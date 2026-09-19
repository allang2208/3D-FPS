#pragma once
#include "Commandlets/Commandlet.h"
#include "FrostSwordModuleAuthoringCommandlet.generated.h"
UCLASS()
class UFrostSwordModuleAuthoringCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
