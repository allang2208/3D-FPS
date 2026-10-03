#pragma once
#include "CoreMinimal.h"
#include "SlagBlackMist.h"
#include "M10PoisonGas.generated.h"

/** Locally rising green smoke; shared dense-core blindness and target poison. */
UCLASS()
class FPSGAME_API AM10PoisonGas : public ASlagBlackMist
{
    GENERATED_BODY()
public:
    AM10PoisonGas();
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere,Category="M10|RearGas",meta=(ClampMin="0")) float MagicDamagePerSecond=6.f;
protected:
    virtual void GetEmissionSources(FVector (&Origins)[3],FVector& Drift) const override;
    virtual bool ShouldEmit() const override;
    virtual float GetDiffusionSpeed() const override { return 1.5f; }
private:
    TMap<TWeakObjectPtr<APawn>,float> ExposureSeconds;
};
