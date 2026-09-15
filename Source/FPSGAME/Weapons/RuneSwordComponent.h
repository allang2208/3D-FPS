#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "RuneSwordRhythm.h"
#include "RuneSwordHeavyRhythm.h"
#include "RuneSwordThrustRhythm.h"
#include "RuneSwordHitQuery.h"
#include "RuneSwordComponent.generated.h"

class AFPSGAMECharacter;
class UCameraComponent;
class USkeletalMeshComponent;
class UAnimSequence;
class USoundBase;
class UColdSteelStatusModel;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;

/** Standalone first-person sword. The inventory owns the equipped instance and saves. */
UCLASS(ClassGroup=(Weapons), meta=(BlueprintSpawnableComponent))
class FPSGAME_API URuneSwordComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    URuneSwordComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;
    void RefreshEquipment(UColdSteelStatusModel* Profile);
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsEquipped() const { return !InstanceId.IsEmpty(); }
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsBusy() const { return bAttacking || bEquipping || bInspecting || bCharging || bReturningCharge || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose; }
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginInspect();
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsInspecting() const { return bInspecting; }
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsGuarding() const { return bGuarding; }
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginGuard();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void ReleaseGuard();
    float ResolveGuardDamage(float IncomingDamage,const class UDamageType* Type,class AController* Instigator,AActor* Causer);
    float EquippedDamage() const { return Damage; }
    float AttackSeconds() const { return RuneSwordRhythm::AttackEnd/AttackRate; }
    /** Camera-local centimetres and degrees, composed with the character's existing feedback. */
    void GetCameraMotion(FVector& Location, FRotator& Rotation) const;
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginAttack();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginPrimaryAttack();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void ReleasePrimaryAttack();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginHeavyCharge();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void ReleaseHeavyCharge();
    UFUNCTION(BlueprintPure, Category="Rune Sword") float HeavyChargeFraction() const { return bCharging ? Elapsed/RuneSwordHeavyRhythm::ChargeSeconds : 0.f; }
    bool TriggerHeavySkill();
    void CancelAction();
private:
    friend class URuneSwordAuditCommandlet;
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Viewmodel;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UAnimSequence>> Animations;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CurrentAnimation;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> AttackLayerSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> BlockSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ParrySound;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> RiftVisual;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RiftMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> RiftMeshes;
    FString InstanceId;
    FName CurrentClip;
    float Elapsed=0.f, Damage=55.f, AttackRate=1.f, SwingDamage=55.f, SwingRate=1.f;
    // Contact timing follows the installed animation, with range captured per swing.
    float Reach=180.f, ContactStart=RuneSwordRhythm::ContactStart, ContactEnd=RuneSwordRhythm::ContactEnd;
    float SwingReach=180.f;
    FTransform PreviousAimFrame;
    float ImpactAge=1.f, ImpactDirection=1.f, ImpactStrength=1.f;
    bool bImpactFeedbackPlayed=false;
    bool bThrustImpact=false;
    float RiftAge=0.f, RiftFastSeconds=.115f, RiftDissolveSeconds=.20f, RiftDriftSpeed=85.f;
    FTransform RiftOrigin;
    FVector RiftDirection=FVector::ForwardVector;
    float RequiredChargeSeconds=2.f,ChargedMultiplier=2.5f;
    bool bAutoHeavyRelease=false,bHeavyTrainingPending=false;
    int32 HeavyTrainingHits=0,HeavyTrainingKills=0;
    void FinishHeavyTraining();
    int32 NextSlash=0, SwingPoison=0, SwingTrainingHits=0;
    FColdSteelSkillShot SwingSkills;
    double LastAttackEnd=-100.;
    double ChargeStartedAt=0.;
    float CancelChargeFrom=0.f, CancelChargeAge=0.f, CancelChargeDuration=.4f;
    bool bAttacking=false, bEquipping=false, bInspecting=false, bQueuedAttack=false;
    bool bCharging=false, bReturningCharge=false, bHeavyAttack=false, bSwingCuePlayed=false;
    bool bThrustAttack=false, bLungeStarted=false, bLungeBlocked=false;
    FVector LungeDirection=FVector::ZeroVector;
    bool bRiftActive=false;
    bool bGuardHeld=false,bGuarding=false,bReturningGuard=false,bGuardReacting=false,bGuardBreakPose=false;
    float GuardPoseTime=0.f,GuardReactionRate=1.f,GuardFeedbackStrength=0.f;
    double GuardStartedAt=0.,GuardFeedbackAt=-100.;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    bool CanUse() const;
    bool StartSwing(FName Clip, bool Heavy);
    FVector AdvanceThrustLunge(float FromTime,float ToTime);
    void ReturnFromCharge();
    void SetClip(FName Name, bool bLoop);
    void SamplePose(float Time);
    FRuneSwordBladeSample ReadBlade(const FTransform& AimFrame) const;
    void SweepBlade(const FRuneSwordBladeSample& From,const FRuneSwordBladeSample& To);
    void StartRift(float SourceAge);
    void TickRift(float Delta);
    void StopRift();
    void TryBeginGuard();
    bool TickGuard(float Delta);
    bool TickGuardBreak(float Delta);
    void GuardFeedback(bool Parried);
    bool GetGuardCameraMotion(FVector& Location,FRotator& Rotation) const;
    void ClearGuard();
};
