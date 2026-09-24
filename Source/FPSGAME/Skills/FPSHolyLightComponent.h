#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HolyLightTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSHolyLightComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UNiagaraSystem;
class USoundBase;
class AFPSHolyLightEffect;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSHolyLightComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSHolyLightComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger(bool bSelf=false);
    void Cancel();
    void InterruptPending();
    bool HasQueuedAction() const{return bQueued;}
    bool HasUnreleasedCast() const{return bCommitted;}
    FString StatusText() const;
    float CooldownFraction() const;
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> MoteSystem;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> CastSounds;
    TArray<TWeakObjectPtr<AFPSHolyLightEffect>> Effects;
    TWeakObjectPtr<AActor> LockedTarget;
    FHolyLightCast CastSnapshot;
    FFPSLeftHandNotice HandNotice;
    bool bQueued=false,bCommitted=false,bQueuedSelf=false;
    FString Message;
    double MessageUntil=0;
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    bool IsTarget(AActor* Target) const;
    bool VisibleFrom(AActor* Origin,AActor* Target,const FVector& Start) const;
    AActor* SelectTarget(const FHolyLightCast& Spell,FString& Failure) const;
    void ServiceQueue();
    void ReleaseAtContact();

    void Feedback(const FString& Text);
    void RejectHeldHand();
};
