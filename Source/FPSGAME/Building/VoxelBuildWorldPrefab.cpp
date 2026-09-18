#include "VoxelBuildWorld.h"
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
        if(AActor* Piece=PrefabActors.FindRef(Anchor).Get())RemovePrefab(Piece);
        Names+=Names.IsEmpty()?Label:FString::Printf(TEXT("、%s"),*Label);
        UE_LOG(LogTemp,Warning,TEXT("PREFAB_DROP %s 失去支撑 @格(%d,%d,%d)"),
            *Label,Anchor.X,Anchor.Y,Anchor.Z);
    }
    Message=FString::Printf(TEXT("%s 失去支撑已脱落"),*Names);
    if(UGameInstance* Game=GetWorld()?GetWorld()->GetGameInstance():nullptr)
        if(auto* Model=Game->GetSubsystem<UColdSteelStatusModel>())
            Model->PostNotice(TEXT("构件脱落"),Message,FString(),3.2f);
}

bool AVoxelBuildWorld::CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason) const
{
    if(!bReady||!Palette){Reason=Message;return false;}
    const FVoxelBuildPrefab* Definition=Palette->FindComponent(Id);
    if(!Definition){Reason=TEXT("缺少该构件定义");return false;}
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
    // 悬空的构件不能放（2026-09-18 用户口径：构件要挂在结构上，不然拆掉周围就剩它浮着）。
    FVoxelBuildPrefabInstance Probe;
    Probe.Id=Id;Probe.Cell=Cell;Probe.Yaw=Yaw;Probe.Footprint=Footprint;
    if(!IsPrefabSupported(Probe))
    {Reason=TEXT("该位置悬空 · 构件要与体素、别的构件或地面接触");return false;}
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
    if(!CanPlacePrefab(Id,Cell,Yaw,Message))return false;
    const FVoxelBuildPrefab* Definition=Palette->FindComponent(Id);
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
    RefreshPrefabOccupancy();MarkSaveDirty();
    Message=Prefabs.IsEmpty()?TEXT("已拆除构件 · 正在保存"):FString::Printf(TEXT("已拆除构件 · 余 %d 件 · 正在保存"),Prefabs.Num());
    return true;
}
