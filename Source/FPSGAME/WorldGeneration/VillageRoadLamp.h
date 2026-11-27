#pragma once

#include "../Building/BronzeTorch.h"
#include "VillageRoadLamp.generated.h"

class UMaterialInstanceDynamic;

/** Local X points from the timber post toward the roadway. The origin is at the foot of the post. */
UCLASS()
class FPSGAME_API AVillageRoadLamp : public ABronzeTorch
{
    GENERATED_BODY()

public:
    AVillageRoadLamp(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void Tick(float DeltaSeconds) override;

protected:
    virtual void PreRegisterAllComponents() override;
    virtual void BeginPlay() override;
    virtual bool ManagesOwnShadowBudget() const override { return true; }

private:
    void UpdateWick();
    void UpdateShadowBudget(bool bForce = false);
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Wick;
    float LastIgnition = -1.f;
    bool bShadowBudgetActive = true;
    double NextShadowBudgetAt = -1.;
};
