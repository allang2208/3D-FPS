#pragma once
#include "Commandlets/Commandlet.h"
#include "HorseGroundContactReviewCommandlet.generated.h"

UCLASS()
class UHorseGroundContactReviewCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    int32 Main(const FString& Params) override;
};
