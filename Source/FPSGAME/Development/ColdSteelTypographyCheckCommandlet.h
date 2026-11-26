#pragma once
#include "Commandlets/Commandlet.h"
#include "ColdSteelTypographyCheckCommandlet.generated.h"

UCLASS()
class UColdSteelTypographyCheckCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
#if WITH_EDITOR
private:
    int32 CheckInventoryPopups();
#endif
};
