#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
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
    if(!Definition->Mesh.LoadSynchronous()){Reason=TEXT("构件网格尚未导入");return false;}
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
    UStaticMesh* Mesh=Definition->Mesh.LoadSynchronous();
    if(!Mesh)return nullptr;
    // The saved footprint is normalized from the palette so edits to the asset stay authoritative.
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Definition->Footprint,Instance.Yaw);
    const FTransform Transform=AVoxelBuildPrefabActor::ComputeTransform(*Definition,Mesh,Instance.Cell,Instance.Yaw);
    FActorSpawnParameters Spawn;
    Spawn.Owner=this;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Piece=GetWorld()->SpawnActor<AVoxelBuildPrefabActor>(AVoxelBuildPrefabActor::StaticClass(),Transform,Spawn);
    if(!Piece)return nullptr;
    Piece->Configure(Instance.Id,Instance.Cell,Instance.Yaw,Mesh,Definition->Surface.LoadSynchronous(),StructuralContact);
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
    if(!bReady||GetNetMode()!=NM_Standalone||!Target){Message=TEXT("只能拆除自己放置的构件");return false;}
    const FIntVector Cell=Target->AnchorCell();
    if(Prefabs.RemoveAll([Cell](const FVoxelBuildPrefabInstance& Entry){return Entry.Cell==Cell;})<=0)
    {Message=TEXT("该构件不在建筑记录中");return false;}
    if(auto* Found=PrefabActors.Find(Cell))
    {
        if(auto* Actor=Found->Get())Actor->Destroy();
        PrefabActors.Remove(Cell);
    }
    if(IsValid(Target))Target->Destroy();
    RefreshPrefabOccupancy();MarkSaveDirty();
    Message=Prefabs.IsEmpty()?TEXT("已拆除构件 · 正在保存"):FString::Printf(TEXT("已拆除构件 · 余 %d 件 · 正在保存"),Prefabs.Num());
    return true;
}
