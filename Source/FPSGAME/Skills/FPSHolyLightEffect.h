#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HolyLightTypes.h"
#include "FPSHolyLightEffect.generated.h"
class USplineComponent;
class UDynamicMeshComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UMaterialInstanceDynamic;
class UPointLightComponent;

UCLASS()
class FPSGAME_API AFPSHolyLightEffect : public AActor
{
    GENERATED_BODY()
public:
    AFPSHolyLightEffect();
    void InitializeLight(AActor* Target,UNiagaraSystem* System,const FHolyLightCast& Spell);
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<USplineComponent> Path;
    UPROPERTY() TObjectPtr<UDynamicMeshComponent> Beam;
    UPROPERTY() TObjectPtr<UDynamicMeshComponent> Core;
    UPROPERTY() TObjectPtr<UDynamicMeshComponent> Pool;
    UPROPERTY() TObjectPtr<UNiagaraComponent> Motes;
    UPROPERTY() TObjectPtr<UPointLightComponent> Light;
    UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
    TWeakObjectPtr<AActor> FollowTarget;
    FHolyLightCast Settings;
    float Age=0,FootOffset=0;
};
