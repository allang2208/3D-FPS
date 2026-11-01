#pragma once
#include "Commandlets/Commandlet.h"
#include "M24HoldReviewCommandlet.generated.h"

/** Saved-asset hold/animation review in an isolated scene; no gameplay or profile writes. */
UCLASS()
class UM24HoldReviewCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
