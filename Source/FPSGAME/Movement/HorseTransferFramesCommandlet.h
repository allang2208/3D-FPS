#pragma once
#include "Commandlets/Commandlet.h"
#include "HorseTransferFramesCommandlet.generated.h"

UCLASS()
class UHorseTransferFramesCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    int32 Main(const FString& Params) override;
};
