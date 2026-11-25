#pragma once
#include "Commandlets/Commandlet.h"
#include "HorseMarketCardsReviewCommandlet.generated.h"

/** Offscreen market review with an in-memory wallet and daily stock. */
UCLASS()
class UHorseMarketCardsReviewCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
