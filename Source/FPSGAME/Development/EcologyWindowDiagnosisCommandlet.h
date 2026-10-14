#pragma once
#include "Commandlets/Commandlet.h"
#include "EcologyWindowDiagnosisCommandlet.generated.h"

/** Explicitly requested ecology window collision diagnosis. Never plays or saves a map. */
UCLASS()
class UEcologyWindowDiagnosisCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
