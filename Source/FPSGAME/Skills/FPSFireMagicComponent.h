#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FireMagicTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSFireMagicComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UNiagaraSystem;
class UNiagaraComponent;
class USoundBase;
class AFPSMeteorStrike;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSFireMagicComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSFireMagicComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger(FName Skill);
    void CancelPending();
    bool HasQueuedAction() const{return !QueuedSkill.IsNone();}
    FName UnreleasedSkill() const{return CommittedSkill;}
    FString StatusText(FName Skill) const;
    float CooldownFraction(FName Skill) const;
    bool IsHandOccupiedNotice(FName Skill) const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    float ArmorRemaining() const{return ArmorTime;}
    void OnWeaponHit(AActor* Target,const FVector& Point);
    void NotifyMeteorImpact(const FVector& Point);
    void GetCameraMotion(FVector& Location,FRotator& Rotation) const;
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> AuraSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> WeaponSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> SparkSystem;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CastSound;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> AuraFX;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> WeaponFX;
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> MeteorAssets;
    TArray<TWeakObjectPtr<AFPSMeteorStrike>> Strikes;
    FName QueuedSkill,CommittedSkill,MessageSkill,NoticeSkill;
    FFireMagicCast CastSnapshot,ArmorSnapshot;
    FFireMagicRewards ArmorRewards;
    FFPSLeftHandNotice HandNotice;
    FVector LockedPoint,LockedNormal;
    float ArmorTime=0,AuraTimer=0;
    double MessageUntil=0;
    double ImpactTime=-1;
    float ImpactStrength=0;
    bool bMeteorAssetsReady=false;
    FString Message;
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    bool SelectGround(const FFireMagicCast& Spell,FVector& Point,FVector& Normal,FString& Failure) const;
    bool Allowed(const FFireMagicCast& Spell,FString& Failure) const;
    void ServiceQueue();
    void ReleaseAtContact();
    void Feedback(FName Skill,const FString& Text);
    void RejectHeldHand(FName Skill);
    void StartArmor();
    void TickArmor(float Delta);
    void EndArmor(bool bTrain);
    void ClearEffects();
    void Sparks(const FVector& Point);
    FVector PreviousWeaponBase=FVector::ZeroVector,PreviousWeaponTip=FVector::ZeroVector;
    bool bWeaponSampleValid=false;
};
