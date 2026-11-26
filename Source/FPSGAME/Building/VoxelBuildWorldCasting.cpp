#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "VillageFurnaceKeys.h"
#include "EngineUtils.h"

bool AVoxelBuildWorld::IsFurnaceAt(FIntVector Cell) const
{
    if (VillageFurnaceKeys::Contains(Cell))
    {
        const auto* Station = SceneStations.FindRef(Cell).Get();
        return Station && Station->PrefabId() == VoxelSmeltingFurnaceId && Station->IsSceneStationAvailable();
    }
    return Prefabs.ContainsByPredicate([Cell](const FVoxelBuildPrefabInstance& E) { return E.Cell == Cell && E.Id == VoxelSmeltingFurnaceId; });
}

void AVoxelBuildWorld::RegisterSceneStation(AVoxelBuildPrefabActor* Station)
{
    if(!IsValid(Station)||Station->GetOwner()!=this||!Station->IsSceneStationAvailable()||Station->PrefabId().IsNone())return;
    UnregisterSceneStation(Station);
    const FIntVector Cell=Station->AnchorCell();
    if(Prefabs.ContainsByPredicate([Cell](const auto& P){return P.Cell==Cell;}))
    {UE_LOG(LogTemp,Warning,TEXT("Village station %s overlaps existing construction at %s"),*Station->GetName(),*Cell.ToString());return;}
    SceneStations.Add(Cell,Station);
}

void AVoxelBuildWorld::UnregisterSceneStation(AVoxelBuildPrefabActor* Station)
{
    for(auto It=SceneStations.CreateIterator();It;++It)
        if(!It.Value().IsValid()||It.Value().Get()==Station)It.RemoveCurrent();
}

AVoxelBuildPrefabActor* AVoxelBuildWorld::PrefabActorAt(FIntVector Cell) const
{
    if(auto* Scene=SceneStations.FindRef(Cell).Get())return Scene;
    if(auto* Found=Cast<AVoxelBuildPrefabActor>(PrefabActors.FindRef(Cell).Get()))return Found;
    if(!HasAuthority())for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
        if(It->GetOwner()==this&&It->AnchorCell()==Cell&&!It->IsSceneStation()&&!It->PrefabId().IsNone()&&!It->IsFalling())
        {const_cast<AVoxelBuildWorld*>(this)->PrefabActors.Add(Cell,*It);return *It;}
    return nullptr;
}

bool AVoxelBuildWorld::FindCastingFurnace(FIntVector Station,FIntVector& OutFurnace) const
{
    for(const auto& Job:SmeltingJobs)
        if(Job.bCasting&&Job.StationCell==Station)
        {OutFurnace=Job.Cell;return true;}
    return false;
}

bool AVoxelBuildWorld::FindAvailableCastingStation(FIntVector Furnace,FIntVector& OutStation) const
{
    const auto* Source=PrefabActorAt(Furnace);
    if(!Source)return false;
    const int32 FurnaceZ = VillageFurnaceKeys::Contains(Furnace) ? FMath::FloorToInt(Source->GetActorLocation().Z / 20.) : Furnace.Z;
    double Best=350.*350.;bool Found=false;
    for(const auto& Entry:Prefabs)
    {
        if(Entry.Id!=VoxelCastingStationId)continue;
        auto* Station=PrefabActorAt(Entry.Cell);
        if(!Station||Station->IsFalling()||FMath::Abs(Entry.Cell.Z-FurnaceZ)>1)continue;
        FIntVector AssignedFurnace;
        if(FindCastingFurnace(Entry.Cell,AssignedFurnace)&&AssignedFurnace!=Furnace)continue;
        const double Distance=FVector::DistSquared2D(Source->GetActorLocation(),Station->GetActorLocation());
        if(Distance<Best){Best=Distance;OutStation=Entry.Cell;Found=true;}
    }
    return Found;
}
