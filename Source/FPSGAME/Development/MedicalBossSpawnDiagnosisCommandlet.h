#pragma once
#include "Commandlets/Commandlet.h"
#include "MedicalBossSpawnDiagnosisCommandlet.generated.h"

/** Query saved theatre collision for the reported missing boss, without BeginPlay or saving assets. */
UCLASS()
class UMedicalBossSpawnDiagnosisCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
