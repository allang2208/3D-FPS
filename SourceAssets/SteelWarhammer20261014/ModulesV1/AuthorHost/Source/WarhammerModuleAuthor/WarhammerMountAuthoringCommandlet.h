#pragma once
#include "Commandlets/Commandlet.h"
#include "WarhammerMountAuthoringCommandlet.generated.h"
UCLASS()
class UWarhammerMountAuthoringCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
