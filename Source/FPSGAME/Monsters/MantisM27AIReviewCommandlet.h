#pragma once
#include "Commandlets/Commandlet.h"
#include "MantisM27AIReviewCommandlet.generated.h"

/** Focused, opt-in review of the M27 recovery/attack regression. No game map. */
UCLASS()
class UMantisM27AIReviewCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
