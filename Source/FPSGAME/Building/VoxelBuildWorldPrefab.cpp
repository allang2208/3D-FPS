#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
#include "ColdSteelDoor.h"
#include "Engine/StaticMesh.h"

namespace
{
    void FillPrefabCells(FIntVector AnchorCell,FIntVector Footprint,TArray<FIntVector>& Out)
    {
        Out.Reset();
        const FIntVector Size=FIntVector(FMath::Max(1,Footprint.X),FMath::Max(1,Footprint.Y),FMath::Max(1,Footprint.Z));
        for(int32 Z=0;Z<Size.Z;++Z)for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
            Out.Add(AnchorCell+FIntVector(X,Y,Z));
    }
}

void AVoxelBuildWorld::RefreshPrefabOccupancy()
{
    PrefabCells.Reset();
    TArray<FIntVector> Occupied;
    for(const FVoxelBuildPrefabInstance& Entry:Prefabs)
    {
        FillPrefabCells(Entry.Cell,Entry.Footprint,Occupied);
        for(const FIntVector& Cell:Occupied)PrefabCells.Add(Cell);
    }
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
            // 逻辑构件自己接管外观：门按调色板条目的材质整体替换（门板＋门框同一材质）。
            if(auto* Door=Cast<AColdSteelDoor>(Logic))Door->Configure(Definition->Surface.LoadSynchronous());
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
