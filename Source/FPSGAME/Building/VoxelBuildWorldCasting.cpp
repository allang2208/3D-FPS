#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "EngineUtils.h"

AVoxelBuildPrefabActor* AVoxelBuildWorld::PrefabActorAt(FIntVector Cell) const
{
    if(auto* Found=Cast<AVoxelBuildPrefabActor>(PrefabActors.FindRef(Cell).Get()))return Found;
    if(!HasAuthority())for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
        if(It->GetOwner()==this&&It->AnchorCell()==Cell&&!It->IsFalling())
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
    double Best=350.*350.;bool Found=false;
    for(const auto& Entry:Prefabs)
    {
        if(Entry.Id!=VoxelCastingStationId)continue;
        auto* Station=PrefabActorAt(Entry.Cell);
        if(!Station||Station->IsFalling()||FMath::Abs(Entry.Cell.Z-Furnace.Z)>1)continue;
        FIntVector AssignedFurnace;
        if(FindCastingFurnace(Entry.Cell,AssignedFurnace)&&AssignedFurnace!=Furnace)continue;
        const double Distance=FVector::DistSquared2D(Source->GetActorLocation(),Station->GetActorLocation());
        if(Distance<Best){Best=Distance;OutStation=Entry.Cell;Found=true;}
    }
    return Found;
}
