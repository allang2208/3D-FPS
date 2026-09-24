#include "VoxelBuildWorld.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildGrounding.h"
#include "SmeltingSystem.h"
#include "ColdSteelDoor.h"
#include "ColdSteelWindow.h"
#include "ColdSteelFountain.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"

namespace
{
    void FillPrefabCells(FIntVector AnchorCell,FIntVector Footprint,TArray<FIntVector>& Out)
    {
        Out.Reset();
        const FIntVector Size=FIntVector(FMath::Max(1,Footprint.X),FMath::Max(1,Footprint.Y),FMath::Max(1,Footprint.Z));
        for(int32 Z=0;Z<Size.Z;++Z)for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
            Out.Add(AnchorCell+FIntVector(X,Y,Z));
    }

    // 支撑判定只看六个正对面（与体素的连接键同一套邻接口径）。
    const FIntVector SupportFaces[]={FIntVector(1,0,0),FIntVector(-1,0,0),FIntVector(0,1,0),
        FIntVector(0,-1,0),FIntVector(0,0,1),FIntVector(0,0,-1)};
    // 超大构件（凉亭 48×48×38 ≈ 8.7 万格）不逐格扫：抽样上限内找一个接触就够。
    constexpr int32 MaxSupportSamples=4096;
}

void AVoxelBuildWorld::RefreshPrefabOccupancy()
{
    PrefabCells.Reset();
    PrefabCellOwner.Reset();
    TArray<FIntVector> Occupied;
    for(const FVoxelBuildPrefabInstance& Entry:Prefabs)
    {
        FillPrefabCells(Entry.Cell,Entry.Footprint,Occupied);
        for(const FIntVector& Cell:Occupied){PrefabCells.Add(Cell);PrefabCellOwner.Add(Cell,Entry.Cell);}
    }
}

bool AVoxelBuildWorld::ResolvePrefabSurfaceCell(const FHitResult& Hit,FVoxelBuildKey& Key) const
{
    // 命中面必须属于一件已放置构件：占位 Actor 自己，或挂在它下面的逻辑构件（门／窗的组件沿
    // 挂载链一路上溯到 AVoxelBuildPrefabActor）。
    const AVoxelBuildPrefabActor* Piece=nullptr;
    for(AActor* Node=Hit.GetComponent()?Hit.GetComponent()->GetOwner():nullptr;
        Node;Node=Node->GetAttachParentActor())
        if((Piece=Cast<AVoxelBuildPrefabActor>(Node)))break;
    if(!Piece)return false;
    // 与体素 ResolveHit 同一口径：取面内半厘米处的格子，命中面贴边才不会落到邻格。
    const FIntVector Cell=ToCell(Hit.ImpactPoint-Hit.ImpactNormal*.5);
    // 占格表是唯一的权威：摆动出来的门／窗扇打在占格体积之外，这里自然拒绝（落回贴地分支）。
    if(!IsPrefabCell(FGuid(),Cell))return false;
    Key=FVoxelBuildKey{{},Cell};return true;
}

bool AVoxelBuildWorld::HitBelongsToPlacedPrefab(const FHitResult& Hit) const
{
    // 与 ResolvePrefabSurfaceCell 同一条上溯链，但不验占格：占格外的摆开扇面也算"构件自己的网格"。
    for(AActor* Node=Hit.GetComponent()?Hit.GetComponent()->GetOwner():nullptr;
        Node;Node=Node->GetAttachParentActor())
        if(Cast<AVoxelBuildPrefabActor>(Node))return true;
    return false;
}

bool AVoxelBuildWorld::IsPrefabCell(FGuid Volume,FIntVector Cell) const
{
    if(Volume.IsValid())
    {
        // 自由体积的格是本地坐标、原点可以在任意连续位置（自由放置不取整）：
        // 换算成真实世界格再查（历史缺陷：直接拿本地格查世界占格表）。
        const auto* Data=FreeVolumes.Find(Volume);if(!Data)return false;
        Cell=ToCell(Data->Origin+CellMin(Cell));
    }
    return PrefabCells.Contains(Cell);
}

bool AVoxelBuildWorld::PrefabSupportAt(FVector WorldMin) const
{
    const FIntVector C=ToCell(WorldMin);
    for(const FIntVector& Face:SupportFaces)if(IsPrefabCell(FGuid(),C+Face))return true;
    return false;
}

bool AVoxelBuildWorld::PrefabColumnTop(FIntVector Cell,FIntVector& OutTopCell) const
{
    // 只认**已放置**构件：命中格得在世界占格表里，再反查锚格与 Footprint 推该列顶。
    const FIntVector* Anchor=PrefabCellOwner.Find(Cell);
    if(!Anchor)return false;
    const FVoxelBuildPrefabInstance* Entry=Prefabs.FindByPredicate(
        [Anchor](const FVoxelBuildPrefabInstance& E){return E.Cell==*Anchor;});
    if(!Entry)return false;
    OutTopCell=FIntVector(Cell.X,Cell.Y,Entry->Cell.Z+FMath::Max(1,Entry->Footprint.Z));
    return true;
}

void AVoxelBuildWorld::ReanchorVoxelsAround(const TArray<FIntVector>& VacatedCells)
{
    if(!SupportGraph||!Runtime||VacatedCells.IsEmpty())return;
    // 只重判"腾出格外壳一圈"的体素，且只处理**原本有锚、如今既不贴地面也不贴别的构件**的节点——
    // 重锚发生在拆除／脱落之后，锚只可能变没、不会新增，所以绝大多数节点一次查表就跳过。
    TSet<FIntVector> VacatedSet;for(const FIntVector& Cell:VacatedCells)VacatedSet.Add(Cell);
    TSet<FIntVector> Boundary;
    for(const FIntVector& Cell:VacatedCells)for(const FIntVector& Face:SupportFaces)
    {
        const FIntVector Neighbor=Cell+Face;
        if(VacatedSet.Contains(Neighbor))continue;
        Boundary.Add(Neighbor);
    }
    TSet<FVoxelBuildKey> Done;bool bChanged=false;
    for(const FIntVector& Cell:Boundary)
    {
        for(const FVoxelBuildKey& Key:SupportGraph->Near(CellMin(Cell)))
        {
            if(Done.Contains(Key))continue;Done.Add(Key);
            FVoxelSupportNode* Node=SupportGraph->Nodes.Find(Key);
            if(!Node||!Node->bAnchor)continue;           // 原本就没锚：不动它（倒塌由既有流程负责）
            if(PrefabSupportAt(Node->Min))continue;      // 还贴着别的构件：锚不变
            if(IsGroundAnchor(Node->Min))continue;       // 脚下有地面：锚不变
            Node->bAnchor=false;
            Runtime->DirtySupport.Add(Key);Runtime->NodeEpoch.Add(Key,Revision+1);
            bChanged=true;
        }
    }
    if(!bChanged)return;
    ++Revision;SupportGraph->SolveConnectivity();
    Runtime->StructureAt=GetWorld()->GetTimeSeconds()+.08;MarkSaveDirty();
}


bool AVoxelBuildWorld::IsPrefabOnGround(FIntVector AnchorCell,FIntVector Footprint) const
{
    // 地面探测点：中心 + 四角（起伏地形上只测中心会误判"没着地"）。
    const int32 LastX=FMath::Max(0,Footprint.X-1),LastY=FMath::Max(0,Footprint.Y-1);
    const FIntVector Points[]={FIntVector(LastX/2,LastY/2,0),FIntVector(0,0,0),FIntVector(LastX,0,0),
        FIntVector(0,LastY,0),FIntVector(LastX,LastY,0)};
    // 2026-09-18 根因（用户报"拆掉支撑后窗仍然悬空"）：探针带是"底面 +40.5 cm"，而构件自己的
    // 网格正好在这条带里。不排除它时，任何构件都会把自己的碰撞当成"底下有地面"，于是拆光周围
    // 也不会掉。这里只排除这一件自己的占位 Actor 与逻辑构件：其他构件、场景实体照旧算表面，
    // 体素放置用的 IsGroundAnchor 口径不变。
    FCollisionQueryParams Params=VoxelGrounding::Query(GetWorld(),this);
    if(const TWeakObjectPtr<AActor>* Placed=PrefabActors.Find(AnchorCell))
        if(AActor* Piece=Placed->Get())
        {
            Params.AddIgnoredActor(Piece);
            if(auto* Prefab=Cast<AVoxelBuildPrefabActor>(Piece))
                if(AActor* Logic=Prefab->Logic())Params.AddIgnoredActor(Logic);
        }
    for(const FIntVector& Offset:Points)
    {
        VoxelGrounding::FFootprint Ground;
        const FVector Min=CellMin(AnchorCell+Offset);
        if(VoxelGrounding::Sample(GetWorld(),Min,Min.Z+VoxelGrounding::AnchorProbeRiseCm,
            Min.Z-VoxelGrounding::ContactToleranceCm,Params,Ground))return true;
    }
    return false;
}

bool AVoxelBuildWorld::IsPrefabSupported(const FVoxelBuildPrefabInstance& Instance,FIntVector* OutContact) const
{
    const FVoxelBuildPrefab* Definition=Palette?Palette->FindComponent(Instance.Id):nullptr;
    if(!Definition)return true;   // 定义缺失时不在这里判死，交给生成路径报错
    // 壁挂构件（火把等）钉在墙面/柱面上，靠的是表面而不是地面：不参与"失去支撑脱落"，
    // 否则挂在非体素表面（关卡网格、导入模型）上的那几件会在附近一动土就掉下来。
    if(Definition->Mount==EVoxelPrefabMount::Wall)return true;
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Instance.Yaw);
    // ① 地形：先试这一条，站在地上的大件（凉亭、喷泉）在这里就短路了。
    if(IsPrefabOnGround(Instance.Cell,Footprint))return true;
    // ②／③ 与体素或另一件构件面对面相邻。
    TArray<FIntVector> Occupied;FillPrefabCells(Instance.Cell,Footprint,Occupied);
    const int32 Stride=FMath::Max(1,FMath::DivideAndRoundUp(Occupied.Num(),MaxSupportSamples));
    for(int32 Index=0;Index<Occupied.Num();Index+=Stride)
    {
        const FIntVector& Cell=Occupied[Index];
        for(const FIntVector& Face:SupportFaces)
        {
            const FIntVector Neighbor=Cell+Face;
            if(!VolumeMaterialAt({},Neighbor).IsNone()){if(OutContact)*OutContact=Neighbor;return true;}
            // 变量名避开 AActor::Owner（项目 C4458 按错误处理）。
            if(const FIntVector* CellOwner=PrefabCellOwner.Find(Neighbor))
                if(*CellOwner!=Instance.Cell){if(OutContact)*OutContact=Neighbor;return true;}
        }
    }
    return false;
}

void AVoxelBuildWorld::VerifyPrefabSupport(const TArray<FVoxelEditCell>& Edit)
{
    if(Prefabs.IsEmpty()||Edit.IsEmpty())return;
    // 只看"改动点及一圈邻居"命中的占格：不这样筛，每批编辑都要扫全场构件（凉亭一件 8.7 万格）。
    TSet<FIntVector> Candidates;
    for(const FVoxelEditCell& E:Edit)
    {
        if(const FIntVector* CellOwner=PrefabCellOwner.Find(E.Position))Candidates.Add(*CellOwner);
        for(const FIntVector& Face:SupportFaces)
            if(const FIntVector* CellOwner=PrefabCellOwner.Find(E.Position+Face))Candidates.Add(*CellOwner);
    }
    if(Candidates.IsEmpty())return;
    TArray<FIntVector> Drop;
    for(const FVoxelBuildPrefabInstance& Instance:Prefabs)
        if(Candidates.Contains(Instance.Cell)&&!IsPrefabSupported(Instance))
            Drop.Add(Instance.Cell);
    if(Drop.IsEmpty())return;
    FString Names;
    for(const FIntVector& Anchor:Drop)
    {
        const FVoxelBuildPrefabInstance* Instance=Prefabs.FindByPredicate(
            [Anchor](const FVoxelBuildPrefabInstance& Entry){return Entry.Cell==Anchor;});
        const FVoxelBuildPrefab* Definition=Instance&&Palette?Palette->FindComponent(Instance->Id):nullptr;
        const FString Label=Definition?Definition->DisplayName.ToString():
            (Instance?Instance->Id.ToString():FString(TEXT("构件")));
        // 脱落 = 真的掉下来（2026-09-18）：占位网格补上调色板代表网格后切成刚体自由落体，
        // 逻辑构件挂上去跟随、停止交互，8 秒后一起销毁。没有可用网格／物理体时退回直接移除。
        // 炉内冶炼/存料的高炉脱落：尽力退料（落体无法像手动拆除那样拒绝）；背包放不下则随炉
        // 清任务与存料并在提示栏点名，不留孤儿条目（读档侧同样会丢弃孤儿，双保险）。
        if(FindSmelting(Anchor)||FuelAt(Anchor)>0)
        {
            FString RefundReason;
            if(!RefundSmeltingAt(Anchor,RefundReason))
            {
                UE_LOG(LogTemp,Warning,TEXT("PREFAB_DROP %s 炉内冶炼无法退料（%s），任务随炉清理"),*Label,*RefundReason);
                ClearSmelting(Anchor);SetFuel(Anchor,0);
                if(UGameInstance* Game=GetWorld()?GetWorld()->GetGameInstance():nullptr)
                    if(auto* Model=Game->GetSubsystem<UColdSteelStatusModel>())
                        Model->PostNotice(TEXT("构件脱落"),FString::Printf(TEXT("%s 炉内冶炼随炉丢失（背包已满）"),*Label),FString(),3.2f);
            }
        }
        AActor* Piece=PrefabActors.FindRef(Anchor).Get();
        // 审计 W3（2026-09-23）：记录里还有这件构件、占位 Actor 却已经没了（外部销毁/GC 边界），
        // 原来会**无声**走完"删记录+清占格"——玩家只看到构件凭空消失。现在点名记日志。
        if(!Piece)UE_LOG(LogTemp,Error,TEXT("PREFAB_DROP %s @格(%d,%d,%d) 占位 Actor 已缺失 · 仅清理记录"),
            *Label,Anchor.X,Anchor.Y,Anchor.Z);
        auto* Placed=Piece?Cast<AVoxelBuildPrefabActor>(Piece):nullptr;
        const bool bFalling=Placed&&Placed->BeginFall(Definition?Definition->Mesh.LoadSynchronous():nullptr,8.f);
        if(Piece&&!bFalling)Piece->Destroy();
        PrefabActors.Remove(Anchor);
        Names+=Names.IsEmpty()?Label:FString::Printf(TEXT("、%s"),*Label);
        UE_LOG(LogTemp,Warning,TEXT("PREFAB_DROP %s 失去支撑 @格(%d,%d,%d) %s"),
            *Label,Anchor.X,Anchor.Y,Anchor.Z,bFalling?TEXT("落体"):TEXT("直接移除"));
    }
    // 先记下将被腾空的全部占格（RemoveAll 之后 Footprint 就没处查了）。
    TArray<FIntVector> Vacated;TArray<FIntVector> Scratch;
    for(const FVoxelBuildPrefabInstance& Entry:Prefabs)
        if(Drop.Contains(Entry.Cell)){FillPrefabCells(Entry.Cell,Entry.Footprint,Scratch);Vacated.Append(Scratch);}
    Prefabs.RemoveAll([&Drop](const FVoxelBuildPrefabInstance& Entry){return Drop.Contains(Entry.Cell);});
    // 脱落的高炉连燃料记录一起清（2026-09-24 回头审查）：SetFuel(0) 遇已升级记录会保留等级（为"烧空不丢升级"，
    // 炉子还在才对），但炉子本体脱落掉出后那条等级记录就成了无主残留——同格重建新炉会白捡旧等级。
    // 上面退料段已按格退过，这里无差别清掉脱落格的燃料记录；下一行 MarkSaveDirty 顺带落盘。
    Fuels.RemoveAll([&Drop](const FVoxelFurnaceFuel& E){return Drop.Contains(E.Cell);});
    RefreshPrefabOccupancy();
    // 腾出的格：原本只锚在这件构件上的体素要重判锚定，否则它会继续被当"有地基"撑着（2026-09-19）。
    ReanchorVoxelsAround(Vacated);
    MarkSaveDirty();
    Message=FString::Printf(TEXT("%s 失去支撑已脱落"),*Names);
    if(UGameInstance* Game=GetWorld()?GetWorld()->GetGameInstance():nullptr)
        if(auto* Model=Game->GetSubsystem<UColdSteelStatusModel>())
            Model->PostNotice(TEXT("构件脱落"),Message,FString(),3.2f);
}

bool AVoxelBuildWorld::CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason,bool bSurfaceBacked) const
{
    if(!bReady||!Palette){Reason=Message;return false;}
    const FVoxelBuildPrefab* Definition=Palette->FindComponent(Id);
    if(!Definition){Reason=TEXT("缺少该构件定义");return false;}
    const bool bWallMount=Definition->Mount==EVoxelPrefabMount::Wall;
    // 逻辑构件（门）只要求 Actor 类；普通构件仍然要求网格。
    if(Definition->ActorClass.IsNull()&&!Definition->Mesh.LoadSynchronous())
    {Reason=TEXT("构件网格尚未导入");return false;}
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Yaw);
    TArray<FIntVector> Occupied;FillPrefabCells(Cell,Footprint,Occupied);
    for(const FIntVector& Entry:Occupied)
    {
        if(PrefabCells.Contains(Entry)){Reason=TEXT("该位置已有构件");return false;}
        if(!VolumeMaterialAt({},Entry).IsNone()){Reason=TEXT("该位置已有体素方块");return false;}
    }
    if(bWallMount)
    {
        // 壁挂件：必须由瞄准到的竖直表面托住（表面法线已在组件侧校验过）。
        if(!bSurfaceBacked){Reason=TEXT("必须贴在墙面或结构表面才能放置");return false;}
    }
    else
    {
        // 悬空的构件不能放（2026-09-18 用户口径：构件要挂在结构上，不然拆掉周围就剩它浮着）。
        FVoxelBuildPrefabInstance Probe;
        Probe.Id=Id;Probe.Cell=Cell;Probe.Yaw=Yaw;Probe.Footprint=Footprint;
        if(!IsPrefabSupported(Probe))
        {Reason=TEXT("该位置悬空 · 构件要与体素、别的构件或地面接触");return false;}
    }
    Reason=FString::Printf(TEXT("可放置 %s · %d × %d × %d cm · 左键确认"),
        *Definition->DisplayName.ToString(),Footprint.X*CellSizeCm,Footprint.Y*CellSizeCm,Footprint.Z*CellSizeCm);
    return true;
}

AVoxelBuildPrefabActor* AVoxelBuildWorld::SpawnPrefab(const FVoxelBuildPrefabInstance& Instance)
{
    const FVoxelBuildPrefab* Definition=Palette?Palette->FindComponent(Instance.Id):nullptr;
    if(!Definition||!GetWorld())return nullptr;
    UClass* LogicClass=Definition->ActorClass.LoadSynchronous();
    UStaticMesh* Mesh=LogicClass?nullptr:Definition->Mesh.LoadSynchronous();
    if(!LogicClass&&!Mesh)return nullptr;
    // The saved footprint is normalized from the palette so edits to the asset stay authoritative.
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Instance.Yaw);
    // 摆放口径按“是不是逻辑构件”分流，而不是看有没有网格：
    //   普通构件：网格包围盒居中于占格体积（ComputeTransform，历史口径）；
    //   逻辑构件（门等）：锚点 = 占格底面中心，构件自己从锚点往上搭。
    // 逻辑构件也带 Mesh（只用于抽屉缩略图），若照普通构件居中，门会被抬升半个身高、与预览不一致。
    const FTransform Transform=LogicClass
        ?FTransform(FRotator(0.f,Instance.Yaw*90.f,0.f),
            FVector(Instance.Cell)*20.f+FVector(Footprint.X*10.f,Footprint.Y*10.f,0.f))
        :AVoxelBuildPrefabActor::ComputeTransform(*Definition,Mesh,Instance.Cell,Instance.Yaw);
    FActorSpawnParameters Spawn;
    Spawn.Owner=this;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Piece=GetWorld()->SpawnActor<AVoxelBuildPrefabActor>(AVoxelBuildPrefabActor::StaticClass(),Transform,Spawn);
    if(!Piece)return nullptr;
    Piece->Configure(Instance.Id,Instance.Cell,Instance.Yaw,Mesh,Definition->Surface.LoadSynchronous(),StructuralContact);
    if(LogicClass)
    {
        // 门等自带逻辑的构件：挂成占位 Actor 的子件，占格/存档仍由 Instance 记录。
        FActorSpawnParameters LogicSpawn;
        LogicSpawn.Owner=this;
        LogicSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        FTransform LogicTransform=Transform;
        LogicTransform.SetLocation(Transform.GetLocation()+Transform.GetRotation().RotateVector(Definition->ActorOffsetCm));
        if(AActor* Logic=GetWorld()->SpawnActor<AActor>(LogicClass,LogicTransform,LogicSpawn))
        {
            // 逻辑构件自己接管外观：门／窗按调色板条目的材质整体替换（框与扇同一材质）。
            if(auto* Door=Cast<AColdSteelDoor>(Logic))Door->Configure(Definition->Surface.LoadSynchronous());
            else if(auto* Window=Cast<AColdSteelWindow>(Logic))Window->Configure(Definition->Surface.LoadSynchronous());
            else if(auto* Fountain=Cast<AColdSteelFountain>(Logic))Fountain->Configure(Definition->Surface.LoadSynchronous());
            Logic->AttachToActor(Piece,FAttachmentTransformRules::KeepWorldTransform);
            Piece->AttachLogicActor(Logic);
        }
    }
    PrefabActors.Add(Instance.Cell,Piece);
    return Piece;
}

bool AVoxelBuildWorld::PlacePrefab(FName Id,FIntVector Cell,int32 Yaw)
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    const FVoxelBuildPrefab* Looking=Palette?Palette->FindComponent(Id):nullptr;
    // 壁挂件在组件侧已经确认过"瞄准的是竖直表面"，这里复检时要把这一点带进来，
    // 否则同一件会被自己的"必须贴墙"规则挡掉。
    const bool bSurfaceBacked=Looking&&Looking->Mount==EVoxelPrefabMount::Wall;
    if(!CanPlacePrefab(Id,Cell,Yaw,Message,bSurfaceBacked))return false;
    const FVoxelBuildPrefab* Definition=Looking;
    FVoxelBuildPrefabInstance Instance;
    Instance.Id=Id;Instance.Cell=Cell;Instance.Yaw=((Yaw%4)+4)%4;
    Instance.Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Instance.Yaw);
    if(!SpawnPrefab(Instance)){Message=TEXT("构件网格生成失败");return false;}
    Prefabs.Add(Instance);RefreshPrefabOccupancy();MarkSaveDirty();
    Message=FString::Printf(TEXT("已放置构件 · 共 %d 件 · 正在保存"),Prefabs.Num());
    return true;
}

bool AVoxelBuildWorld::RemovePrefab(AActor* Piece)
{
    AVoxelBuildPrefabActor* Target=Cast<AVoxelBuildPrefabActor>(Piece);
    // 传进来的可能是逻辑构件（门）本身：向上找承载它的占位记录。
    if(!Target)for(AActor* Parent=Piece?Piece->GetAttachParentActor():nullptr;Parent;Parent=Parent->GetAttachParentActor())
        if(auto* Found=Cast<AVoxelBuildPrefabActor>(Parent)){Target=Found;break;}
    if(!bReady||GetNetMode()!=NM_Standalone||!Target){Message=TEXT("只能拆除自己放置的构件");return false;}
    // 正在下落的构件（失去支撑后脱落）已经不在 Prefabs 记录里，但 Actor 还要飞一段时间。
    // 不特判的话会走到下面的 RemoveAll，提示"不在建筑记录中"——玩家清不掉它；
    // 更糟的是若同一格已经放了**新**构件，用 AnchorCell 查记录会命中新构件并把它销毁。
    // 落体件只销毁自己：不碰记录、不重判锚定（脱落时已经 Reanchor 过了）、不退还材料
    // （与手动拆除一致，构件本就免料）。
    if(Target->IsFalling())
    {
        if(AActor* Logic=Target->Logic())Logic->Destroy();
        Target->Destroy();
        Message=TEXT("已清除正在坠落的构件");
        return true;
    }
    const FIntVector Cell=Target->AnchorCell();
    // 高炉拆除特判（2026-09-23 冶炼）：炉内有矿料或存料先退料（完成退产物、未完退原料、燃料折木材）；
    // 背包放不下就拒绝拆除——与放置"先扣料再提交"同一口径，不静默吞料也不凭空产锭。
    if(FindSmelting(Cell)||FuelAt(Cell)>0)
    {
        FString RefundReason;
        if(!RefundSmeltingAt(Cell,RefundReason)){Message=RefundReason;return false;}
    }
    // 先记下这件构件的占格（RemoveAll 之后 Footprint 就没处查了）：拆除后贴着它的体素要重判锚定。
    TArray<FIntVector> Vacated;
    if(const FVoxelBuildPrefabInstance* Entry=Prefabs.FindByPredicate(
            [Cell](const FVoxelBuildPrefabInstance& E){return E.Cell==Cell;}))
        FillPrefabCells(Entry->Cell,Entry->Footprint,Vacated);
    if(Prefabs.RemoveAll([Cell](const FVoxelBuildPrefabInstance& Entry){return Entry.Cell==Cell;})<=0)
    {Message=TEXT("该构件不在建筑记录中");return false;}
    if(auto* Found=PrefabActors.Find(Cell))
    {
        // 占位记录是 AActor：逻辑构件（门）挂在上面，拆除时先销毁它再销毁占位。
        if(auto* Placed=Cast<AVoxelBuildPrefabActor>(Found->Get()))
        {
            if(AActor* Logic=Placed->Logic())Logic->Destroy();
            Placed->Destroy();
        }
        else if(AActor* Actor=Found->Get())Actor->Destroy();
        PrefabActors.Remove(Cell);
    }
    if(IsValid(Target))Target->Destroy();
    // 拆除高炉＝这座炉连同它的升级与存料一起作废：清掉燃料记录（含只升过级、存料已烧空/为零的残留记录）。
    // 退料在上面已按格退过；非炉格的拆除这里 RemoveAll 命中 0，无副作用。
    Fuels.RemoveAll([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    RefreshPrefabOccupancy();
    ReanchorVoxelsAround(Vacated);
    MarkSaveDirty();
    Message=Prefabs.IsEmpty()?TEXT("已拆除构件 · 正在保存"):FString::Printf(TEXT("已拆除构件 · 余 %d 件 · 正在保存"),Prefabs.Num());
    return true;
}

// —— 炉内冶炼（VBX v6）：任务与存料都按高炉锚格存，与构件记录同一份存档、同一生命周期。
// 进度＝已积累秒数＋当前燃烧段（UTC ticks，关闭游戏也计入，但受燃料封顶）；
// 结算/续燃/添燃料在 UColdSteelSmeltingSystem，这里只存状态。

const FVoxelSmeltingJob* AVoxelBuildWorld::FindSmelting(FIntVector Cell) const
{
    const FVoxelSmeltingJob* Job=SmeltingJobs.FindByPredicate([Cell](const FVoxelSmeltingJob& E){return E.Cell==Cell;});
    return Job&&!Job->Recipe.IsNone()?Job:nullptr;
}

FVoxelSmeltingJob* AVoxelBuildWorld::FindSmeltingMutable(FIntVector Cell)
{
    FVoxelSmeltingJob* Job=SmeltingJobs.FindByPredicate([Cell](const FVoxelSmeltingJob& E){return E.Cell==Cell;});
    return Job&&!Job->Recipe.IsNone()?Job:nullptr;
}

bool AVoxelBuildWorld::BeginSmelting(FIntVector Cell,FName Recipe,FString& Reason,int64 Batch)
{
    if(!bReady||GetNetMode()!=NM_Standalone){Reason=TEXT("建筑世界未就绪");return false;}
    const FVoxelBuildPrefabInstance* Piece=Prefabs.FindByPredicate(
        [Cell](const FVoxelBuildPrefabInstance& E){return E.Cell==Cell;});
    if(!Piece||Piece->Id!=VoxelSmeltingFurnaceId){Reason=TEXT("目标不是已放置的冶炼高炉");return false;}
    if(FindSmelting(Cell)){Reason=TEXT("这座高炉正在冶炼");return false;}
    if(Recipe.IsNone()){Reason=TEXT("冶炼任务无效");return false;}
    // 以"待燃"落账：是否立刻起燃由系统层 EnsureBurning 按存料决定。
    FVoxelSmeltingJob& Job=SmeltingJobs.AddDefaulted_GetRef();
    Job.Cell=Cell;Job.Recipe=Recipe;Job.ProgressSeconds=0;Job.BurnStartTicks=0;
    Job.BatchCount=FMath::Max<int64>(1,Batch);
    MarkSaveDirty();
    return true;
}

int32 AVoxelBuildWorld::FurnaceLevel(FIntVector Cell) const
{   return FurnaceUpgradeLevel(Cell,VoxelFurnaceAxisSpeed);   }

namespace { int32 FVoxelFurnaceFuel::* FurnaceLevelField(int32 Axis)
{   switch(Axis){case VoxelFurnaceAxisFuelCapacity:return &FVoxelFurnaceFuel::FuelLevel;
    case VoxelFurnaceAxisBatch:return &FVoxelFurnaceFuel::BatchLevel;default:return &FVoxelFurnaceFuel::Level;}   }   }

int32 AVoxelBuildWorld::FurnaceUpgradeLevel(FIntVector Cell,int32 Axis) const
{
    const FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    return Fuel?FMath::Clamp(Fuel->*FurnaceLevelField(Axis),1,VoxelFurnaceAxisMax(Axis)):1;
}

void AVoxelBuildWorld::SetFurnaceUpgradeLevel(FIntVector Cell,int32 Axis,int32 Level)
{
    Level=FMath::Clamp(Level,1,VoxelFurnaceAxisMax(Axis));   // 燃料仓 6 档、其余 5 档（2026-09-24 数值调参）
    FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    if(!Fuel)
    {   // 升级可以发生在零存料时：建一条 0 秒记录承载等级（读档过滤认任一轴>1 的记录，不会丢）。
        FVoxelFurnaceFuel& Created=Fuels.AddDefaulted_GetRef();Created.Cell=Cell;Fuel=&Created;
    }
    int32 FVoxelFurnaceFuel::* Field=FurnaceLevelField(Axis);
    if(Fuel->*Field==Level)return;
    Fuel->*Field=Level;MarkSaveDirty();
}

void AVoxelBuildWorld::SetFurnaceLevel(FIntVector Cell,int32 Level)
{   SetFurnaceUpgradeLevel(Cell,VoxelFurnaceAxisSpeed,Level);   }

bool AVoxelBuildWorld::ClearSmelting(FIntVector Cell)
{
    const int32 Removed=SmeltingJobs.RemoveAll([Cell](const FVoxelSmeltingJob& E){return E.Cell==Cell;});
    if(Removed>0)MarkSaveDirty();
    return Removed>0;
}

double AVoxelBuildWorld::FuelAt(FIntVector Cell) const
{
    const FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    return Fuel?Fuel->FuelSeconds:0.;
}

void AVoxelBuildWorld::SetFuel(FIntVector Cell,double Seconds)
{
    const int32 Index=Fuels.IndexOfByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    if(Seconds<=0)
    {
        // 零存料但已升级的炉子：记录要留着承载等级（否则升级随烧空丢失，2026-09-24 排查发现）。
        // v9 三轴：任一轴升过级都要保记录，不然烧空一次就把那条轴的等级洗掉。
        if(Index!=INDEX_NONE)
        {
            const FVoxelFurnaceFuel& E=Fuels[Index];
            if(E.Level>1||E.FuelLevel>1||E.BatchLevel>1)
            {   if(!FMath::IsNearlyEqual(E.FuelSeconds,0.0)){Fuels[Index].FuelSeconds=0;MarkSaveDirty();} return; }
            Fuels.RemoveAt(Index);MarkSaveDirty();
        }
        return;
    }
    if(Index!=INDEX_NONE)
    {
        if(FMath::IsNearlyEqual(Fuels[Index].FuelSeconds,Seconds))return;   // 值没变就不标脏
        Fuels[Index].FuelSeconds=Seconds;
    }
    else
    {
        FVoxelFurnaceFuel& Fuel=Fuels.AddDefaulted_GetRef();
        Fuel.Cell=Cell;Fuel.FuelSeconds=Seconds;
    }
    MarkSaveDirty();
}

void AVoxelBuildWorld::SetFurnaceFireTicks(FIntVector Cell,int64 Ticks)
{
    if(FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;}))
        if(Fuel->FireStartTicks!=Ticks){Fuel->FireStartTicks=Ticks;MarkSaveDirty();}
}

int64 AVoxelBuildWorld::FurnaceFireTicks(FIntVector Cell) const
{
    const FVoxelFurnaceFuel* Fuel=Fuels.FindByPredicate([Cell](const FVoxelFurnaceFuel& E){return E.Cell==Cell;});
    return Fuel?Fuel->FireStartTicks:0;
}

bool AVoxelBuildWorld::RefundSmeltingAt(FIntVector Cell,FString& Reason)
{
    if(!FindSmelting(Cell)&&FuelAt(Cell)<=0)return true;   // 炉内本就没有矿料和存料。
    UGameInstance* Game=GetWorld()?GetWorld()->GetGameInstance():nullptr;
    auto* System=Game?Game->GetSubsystem<UColdSteelSmeltingSystem>():nullptr;
    if(!System){Reason=TEXT("冶炼系统未就绪");return false;}
    return System->RefundForTeardown(this,Cell,Reason);
}
