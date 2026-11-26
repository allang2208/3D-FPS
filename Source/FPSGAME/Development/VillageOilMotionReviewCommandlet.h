#pragma once
#include "Commandlets/Commandlet.h"
#include "VillageOilMotionReviewCommandlet.generated.h"

UCLASS()
class UVillageOilMotionReviewCommandlet : public UCommandlet
{
    GENERATED_BODY()
    int32 Main(const FString& Params) override;
};
