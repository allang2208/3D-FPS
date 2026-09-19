#pragma once
#include "Commandlets/Commandlet.h"
#include "FrostSwordSurfaceCaptureCommandlet.generated.h"

// Explicit visual diagnosis only. No profile, save, gameplay or map startup.
UCLASS()
class UFrostSwordSurfaceCaptureCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
