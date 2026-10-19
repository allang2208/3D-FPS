#pragma once
#include "Commandlets/Commandlet.h"
#include "Saiga12KSurfaceReviewCommandlet.generated.h"

/** Offline, posed asset rendering for Saiga surface repairs. No player/profile is created. */
UCLASS()
class USaiga12KSurfaceReviewCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
