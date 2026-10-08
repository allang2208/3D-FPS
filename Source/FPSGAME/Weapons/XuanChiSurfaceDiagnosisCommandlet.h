#pragma once
#include "Commandlets/Commandlet.h"
#include "XuanChiSurfaceDiagnosisCommandlet.generated.h"

// Explicit diagnosis of the saved sword surface; creates no game or player state.
UCLASS()
class UXuanChiSurfaceDiagnosisCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
