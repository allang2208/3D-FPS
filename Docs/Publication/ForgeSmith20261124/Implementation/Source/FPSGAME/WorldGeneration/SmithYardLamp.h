#pragma once

#include "../Building/BronzeTorch.h"
#include "SmithYardLamp.generated.h"

class UMaterialInstanceDynamic;

/** Village shop lantern. Local origin is the wall plate, local +X points into the lit bay. */
UCLASS()
class FPSGAME_API AVillageShopChainLamp : public ABronzeTorch
{
    GENERATED_BODY()

public:
    AVillageShopChainLamp();
    virtual void Tick(float DeltaSeconds) override;
    static const FName AlwaysLit;
    static const FName Unlit;

protected:
    virtual void BeginPlay() override;

private:
    void UpdateWick();
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Wick;
    float LastIgnition = -1.f;
};
