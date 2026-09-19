#pragma once
#include "Commandlets/Commandlet.h"
#include "GrantPlayerAKMCommandlet.generated.h"

UCLASS()
class UGrantPlayerAKMCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
