#include "ForestVillageMap.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"

namespace
{
void SelectGateRoad(const TArray<FString>& Args,UWorld* World)
{
    if(!World || !World->IsGameWorld() || !ForestVillageMap::Is(World))return;
    const bool Full=Args.Num()==2 && Args[1].Equals(TEXT("full"),ESearchCase::IgnoreCase);
    float Look=0.f;
    if(Args.Num()==1 && Args[0].Equals(TEXT("original"),ESearchCase::IgnoreCase))Look=-1.f;
    else if((Args.Num()==1 || Full) && Args[0].Equals(TEXT("A"),ESearchCase::IgnoreCase))Look=Full?2.f:0.f;
    else if((Args.Num()==1 || Full) && Args[0].Equals(TEXT("B"),ESearchCase::IgnoreCase))Look=Full?3.f:1.f;
    else
    {
        UE_LOG(LogTemp,Display,TEXT("fps.Hills.RoadSurface A|B [full] or original"));
        return;
    }

    auto* Collection=LoadObject<UMaterialParameterCollection>(nullptr,
        TEXT("/Game/ForestPathStudy/VillageRegion/Reference/GateRoad/MPC_GateRoad.MPC_GateRoad"));
    auto* Instance=Collection?World->GetParameterCollectionInstance(Collection):nullptr;
    if(!Instance || !Instance->SetScalarParameterValue(TEXT("RoadLook"),Look))
    {
        UE_LOG(LogTemp,Warning,TEXT("Forest village road look parameter unavailable"));
        return;
    }
    UE_LOG(LogTemp,Display,TEXT("Forest village road surface %s"),*FString::Join(Args,TEXT(" ")));
}

FAutoConsoleCommandWithWorldAndArgs RoadSurfaceCommand(TEXT("fps.Hills.RoadSurface"),
    TEXT("Choose the Quixel (A) or village (B) palette on the east-gate bend; append full for the quarry route, or use original."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&SelectGateRoad));
}

