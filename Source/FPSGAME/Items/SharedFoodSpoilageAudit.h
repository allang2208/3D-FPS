#pragma once
#include "CoreMinimal.h"

class UWorld;
class UColdSteelStatusModel;

// Called only by the guarded, isolated FoodSpoilageAudit commandlet. Uses real
// world persistence and guest merge paths; it does not exercise socket transport.
void RunSharedFoodSpoilageAudit(UWorld* World,UColdSteelStatusModel* Model,
    TFunctionRef<void(bool,const FString&,const FString&)> Check);
