#pragma once
#include "Commandlets/Commandlet.h"
#include "StablemasterFaceCommandlet.generated.h"

UCLASS()
class UStablemasterFaceCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
