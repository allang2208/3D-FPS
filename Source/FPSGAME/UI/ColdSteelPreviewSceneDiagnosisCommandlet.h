#pragma once
#include "Commandlets/Commandlet.h"
#include "ColdSteelPreviewSceneDiagnosisCommandlet.generated.h"

/** Explicit, isolated reproduction of a mismatched world-subsystem CDO during icon studio creation. */
UCLASS()
class UColdSteelPreviewSceneDiagnosisCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
