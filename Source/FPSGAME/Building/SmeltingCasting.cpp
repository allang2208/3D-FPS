#include "SmeltingSystem.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"

int64 UColdSteelSmeltingSystem::CastingStored(const FVoxelSmeltingJob& Job)
{
    int64 Count=0;for(const auto& P:Job.Products)Count+=FMath::Max<int64>(0,P.Count);
    return Count;
}

bool UColdSteelSmeltingSystem::HasCastingStation(const AVoxelBuildWorld* World,FIntVector Cell) const
{
    if(!World)return false;
    if(const auto* Job=World->FindSmelting(Cell);Job&&Job->bCasting)return true;
    FIntVector Station;return World->FindAvailableCastingStation(Cell,Station);
}

bool UColdSteelSmeltingSystem::CastingBlocked(const AVoxelBuildWorld* World,const FVoxelSmeltingJob& Job) const
{
    if(!Job.bCasting)return false;
    auto* Station=World?World->PrefabActorAt(Job.StationCell):nullptr;
    if(!Station||Station->IsFalling()||Station->PrefabId()!=VoxelCastingStationId)return true;
    const auto* Recipe=Find(Job.Recipe);
    return Recipe&&CastingStored(Job)+Recipe->OutputCount>CastingCapacity;
}

bool UColdSteelSmeltingSystem::SettleCasting(AVoxelBuildWorld* World,FIntVector Cell)
{
    auto* Job=World?World->FindSmeltingMutable(Cell):nullptr;
    if(!Job||!Job->bCasting)return false;
    auto* Station=World->PrefabActorAt(Job->StationCell);
    if(!Station||Station->IsFalling()||Station->PrefabId()!=VoxelCastingStationId)
    {
        FIntVector Replacement;
        if(World->FindAvailableCastingStation(Cell,Replacement))
        {Job->StationCell=Replacement;World->MarkSmeltingDirty();}
    }
    const int64 Now=FDateTime::UtcNow().GetTicks();
    const double TickSeconds=1./double(ETimespan::TicksPerSecond);
    const int64 Fire=World->FurnaceFireTicks(Cell);
    const double FuelSeconds=FMath::Max(0.,World->FuelAt(Cell));
    const double Elapsed=Fire>0&&Fire<=Now?double(Now-Fire)*TickSeconds:0.;
    const double Burn=FMath::Min(Elapsed,FuelSeconds);
    double Work=Burn;
    bool Changed=false;
    // Fuel still burns while the rack is full, matching the existing user-approved furnace rule.
    // Only actual work before the fuel runs out advances the queue; offline catch-up uses this same loop.
    for(int32 Iter=0;Iter<CastingCapacity+CastingQueueCapacity+2;++Iter)
    {
        if(Job->Recipe.IsNone())
        {
            if(Job->Queue.IsEmpty())break;
            const auto Next=Job->Queue[0];Job->Queue.RemoveAt(0);
            Job->Recipe=Next.Recipe;Job->BatchCount=Next.Batch;
            Job->ProducedBatches=0;Job->ProgressSeconds=0;Changed=true;
        }
        const auto* Recipe=Find(Job->Recipe);
        if(!Recipe||CastingBlocked(World,*Job))break;
        const double Unit=FMath::Max(.001,Recipe->Seconds/SpeedMultiplier(World->FurnaceLevel(Cell)));
        const double Need=FMath::Max(0.,Unit*double(Job->ProducedBatches+1)-Job->ProgressSeconds);
        const double Advance=FMath::Min(Need,Work);
        if(Advance>0){Job->ProgressSeconds+=Advance;Work-=Advance;Changed=true;}
        if(Advance+1e-6<Need)break;
        auto* Product=Job->Products.FindByPredicate([&](const auto& P){return P.Item==Recipe->Output;});
        if(!Product){auto& New=Job->Products.AddDefaulted_GetRef();New.Item=Recipe->Output;Product=&New;}
        Product->Count+=Recipe->OutputCount;
        ++Job->ProducedBatches;++Job->CastSerial;
        Job->LastCastRecipe=Job->Recipe;
        Job->LastCastTicks=Fire>0?FMath::Min(Now,Fire+int64((Burn-Work)*ETimespan::TicksPerSecond)):Now;
        Changed=true;
        if(Job->ProducedBatches>=Job->BatchCount)
        {
            Job->Recipe=NAME_None;Job->BatchCount=0;
            Job->ProducedBatches=0;Job->ProgressSeconds=0;
        }
        if(Work<=1e-6&&Job->ProgressSeconds<=0)break;
    }
    const int64 Start=FuelSeconds>Burn&&!Job->Recipe.IsNone()&&!CastingBlocked(World,*Job)?Now:0;
    if(Job->BurnStartTicks!=Start){Job->BurnStartTicks=Start;Changed=true;}
    World->SetFuel(Cell,FuelSeconds-Burn);
    World->SetFurnaceFireTicks(Cell,FuelSeconds>Burn?Now:0);
    if(Changed)World->MarkSmeltingDirty();
    return Changed||Burn>0;
}
