#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSExhaustionComponent.generated.h"

class UAudioComponent;
class UPostProcessComponent;
class USoundBase;

/** Stamina-zero edge and owner-only presentation; combat status owns the five-second debuff. */
UCLASS(ClassGroup=(Movement))
class FPSGAME_API UFPSExhaustionComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSExhaustionComponent();
    void ObserveStamina(float Stamina);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UFUNCTION(Server,Reliable) void ServerEnterExhaustion();
    UPROPERTY(Transient) TObjectPtr<UPostProcessComponent> Darkness;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> Panting;
    UPROPERTY() TObjectPtr<USoundBase> PantingSound;
    bool bWasDepleted=false,bWasActive=false;
    float ViewWeight=0.f;
};
