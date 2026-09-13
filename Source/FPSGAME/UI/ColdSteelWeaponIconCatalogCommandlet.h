#pragma once
#include "Commandlets/Commandlet.h"
#include "ColdSteelWeaponIconCatalogCommandlet.generated.h"

/** Offline production of transparent base-weapon inventory images. */
UCLASS()
class UColdSteelWeaponIconCatalogCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
