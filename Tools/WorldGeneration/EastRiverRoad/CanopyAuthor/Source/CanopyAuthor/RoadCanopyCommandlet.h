#pragma once
#include "Commandlets/Commandlet.h"
#include "RoadCanopyCommandlet.generated.h"

UCLASS()
class URoadCanopyCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
