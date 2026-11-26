#include "ProductionResource.h"
#include "../Development/DevelopmentEnvironmentObject.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "EngineUtils.h"

bool FProductionResource::ResolveHit(UWorld* Scene, const FHitResult& Hit, FProductionResource& Out, FString& Reason)
{
    if (const auto* Object = Cast<ADevelopmentEnvironmentObject>(Hit.GetActor())) return Object->Describe(Out);
    for (TActorIterator<ATemperateHillsWorld> It(Scene); It; ++It)
        if (It->ResolveProductionResource(Hit, Out, Reason)) return true;
    return false;
}

void FProductionResource::ApplySuccessfulStrike(const FHitResult& Hit, bool bDepleted) const
{
    if (auto* Object = DevelopmentObject.Get()) Object->ApplyStrike(*this, Hit, bDepleted);
    else if (bDepleted && World.IsValid()) World->CompleteProductionHarvest(*this, Hit, Direction);
}
