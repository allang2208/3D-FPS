#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ProductionBreakEffect.generated.h"

UCLASS(NotBlueprintable)
class AProductionBreakEffect : public AActor
{
    GENERATED_BODY()
public:
    AProductionBreakEffect();
    void Start(bool Wood,uint32 Seed,bool Landing);
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<class UParticleSystemComponent> Dust;
    UPROPERTY() TObjectPtr<class UNiagaraComponent> Leaves;
    UPROPERTY() TArray<TObjectPtr<class UBoxComponent>> Bodies;
    float Age=0;
    bool Stopped=false;
};
