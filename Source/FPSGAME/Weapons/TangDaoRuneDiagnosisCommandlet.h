#pragma once
#include "Commandlets/Commandlet.h"
#include "TangDaoRuneDiagnosisCommandlet.generated.h"

/** Read the reported TangDao assembly and derived mesh data without gameplay. */
UCLASS()
class UTangDaoRuneDiagnosisCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
