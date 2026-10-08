#pragma once
#include "Commandlets/Commandlet.h"
#include "BoundCongregateRigReviewCommandlet.generated.h"

/** Opt-in review of the real ten-limb animation instance on an isolated floor. */
UCLASS()
class UBoundCongregateRigReviewCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
