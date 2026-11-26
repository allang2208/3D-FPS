#pragma once
#include "Commandlets/Commandlet.h"
#include "SharedGripSurfaceDiagnosisCommandlet.generated.h"

// Explicit diagnosis only; no game state is created and no asset is saved.
UCLASS()
class USharedGripSurfaceDiagnosisCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
