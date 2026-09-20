#include "VoxelBuildWorld.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
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
            Node->bAnchor=false;AnchorCache.Add(Key,false);
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
    for(const FIntVector& Offset:Points)
        if(IsGroundAnchor(CellMin(AnchorCell+Offset)))return true;
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
    // 先记下将被腾空的全部占格（逐件 RemovePrefab 会把条目清掉，Footprint 之后就没处查了）。
    TArray<FIntVector> Vacated;TArray<FIntVector> Scratch;
    for(const FVoxelBuildPrefabInstance& Entry:Prefabs)
        if(Drop.Contains(Entry.Cell)){FillPrefabCells(Entry.Cell,Entry.Footprint,Scratch);Vacated.Append(Scratch);}
    FString Names;
    for(const FIntVector& Anchor:Drop)
    {
        const FVoxelBuildPrefabInstance* Instance=Prefabs.FindByPredicate(
            [Anchor](const FVoxelBuildPrefabInstance& Entry){return Entry.Cell==Anchor;});
        const FVoxelBuildPrefab* Definition=Instance&&Palette?Palette->FindComponent(Instance->Id):nullptr;
        const FString Label=Definition?Definition->DisplayName.ToString():
            (Instance?Instance->Id.ToString():FString(TEXT("构件")));
        if(AActor* Piece=PrefabActors.FindRef(Anchor).Get())RemovePrefab(Piece);
        Names+=Names.IsEmpty()?Label:FString::Printf(TEXT("、%s"),*Label);
        UE_LOG(LogTemp,Warning,TEXT("PREFAB_DROP %s 失去支撑 @格(%d,%d,%d)"),
            *Label,Anchor.X,Anchor.Y,Anchor.Z);
    }
    // 腾出的格：原本只锚在这些构件上的体素要重判锚定，否则会继续被当"有地基"撑着（2026-09-19）。
    ReanchorVoxelsAround(Vacated);
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
    const FIntVector Cell=Target->AnchorCell();
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
    RefreshPrefabOccupancy();
    ReanchorVoxelsAround(Vacated);
    MarkSaveDirty();
    Message=Prefabs.IsEmpty()?TEXT("已拆除构件 · 正在保存"):FString::Printf(TEXT("已拆除构件 · 余 %d 件 · 正在保存"),Prefabs.Num());
    return true;
}
