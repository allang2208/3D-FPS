#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "RuneSwordRhythm.h"
#include "RuneSwordHeavyRhythm.h"
#include "RuneSwordThrustRhythm.h"
#include "RuneSwordPommelRhythm.h"
#include "RuneSwordOverheadRhythm.h"
#include "RuneSwordHitQuery.h"
#include "MeleeWeaponStats.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "UObject/StrongObjectPtr.h"
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
class UMaterialInterface;

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
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsBusy() const { return bWhirlwind || bAttacking || bEquipping || bInspecting || bCharging || bReturningCharge || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose; }
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
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginOverhead();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginPrimaryAttack();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void ReleasePrimaryAttack();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginHeavyCharge();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void ReleaseHeavyCharge();
    UFUNCTION(BlueprintPure, Category="Rune Sword") float HeavyChargeFraction() const { return bCharging ? Elapsed/RuneSwordHeavyRhythm::ChargeSeconds : 0.f; }
    bool TriggerHeavySkill();
    bool BeginWhirlwind();
    bool IsWhirlwindActive() const { return bWhirlwind; }
    bool TryBeginDashAttack();
    bool IsDashAttackActive() const { return bDashAttack; }
    float DashReadyFraction() const;
    /** Authored carry progress, used by the shared footstep-driven sprint camera. */
    float TacticalSprintPoseWeight() const;
    /** 快速进战：以独立配重锤动作发动技能打击（伤害/击退/眩晕走技能公式）。 */
    UFUNCTION(BlueprintCallable, Category="Rune Sword") bool BeginQuickCombatStrike();
    void CancelAction();
    bool GetFireMagicBladePoints(FVector& Base,FVector& Tip) const;
private:
    friend class URuneSwordAuditCommandlet;
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Viewmodel;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> ModularSword;
    FVector ModularBladeBase=FVector::ZeroVector,ModularBladeTip=FVector::ZeroVector;
    void RefreshModularSword(const struct FColdSteelItem* Item);
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UAnimSequence>> Animations;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CurrentAnimation;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> AttackLayerSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    /** Impact cue for the pommel strike; other attacks keep the weapon's hit_sound. */
    UPROPERTY(Transient) TObjectPtr<USoundBase> PommelHitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> BlockSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ParrySound;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> RiftVisual;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RiftMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> RiftMeshes;
    FString InstanceId;
    FString EquippedMeshPath;
    FMeleeModifiers MeleeModifiers;
    float SwingRuneVulnerability=0, SwingRuneVulnerabilitySeconds=0;
    float SwingCooldownReduceSeconds=0;bool bSwingCooldownReduced=false;
    FName CurrentClip;
    float Elapsed=0.f, Damage=55.f, AttackRate=1.f, SwingDamage=55.f, SwingRate=1.f;
    // Contact timing follows the installed animation, with range captured per swing.
    float Reach=180.f, ContactStart=RuneSwordRhythm::ContactStart, ContactEnd=RuneSwordRhythm::ContactEnd;
    float SwingReach=180.f, SwingRangeMultiplier=2.f, SwingHitReactionMultiplier=1.f;
    float SwingKnockbackCM=0.f;
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
    bool bWhirlwind=false,bWhirlwindTrainingPending=false;
    bool bWhirlwindSavedBlurOverride=false,bWhirlwindSavedBlurMaxOverride=false;
    FWhirlwindCast WhirlwindCast;
    FWhirlwindTuning WhirlwindTuning;
    int32 WhirlwindHits=0,WhirlwindKills=0;
    float WhirlwindPause=0.f,WhirlwindPauseSpent=0.f,WhirlwindYaw=0.f;
    float WhirlwindSavedBlur=0.f,WhirlwindSavedBlurMax=0.f;
    FVector WhirlwindEntryLocation=FVector::ZeroVector;
    FRotator WhirlwindEntryRotation=FRotator::ZeroRotator;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WhirlwindFocusMaterial;
    struct FWhirlwindDepthState
    {
        TWeakObjectPtr<class UPrimitiveComponent> Primitive;
        bool bRenderCustomDepth=false;
        int32 Stencil=0;
        uint8 WriteMask=0;
        TArray<TStrongObjectPtr<UMaterialInterface>> Materials;
        TArray<TStrongObjectPtr<UMaterialInterface>> OverlayMaterials;
    };
    TArray<FWhirlwindDepthState> WhirlwindDepthStates;
    void BeginWhirlwindFocus();
    void SetWhirlwindFocus(float Strength);
    void EndWhirlwindFocus();
    void TickWhirlwind(float Delta);
    void SweepWhirlwind(float FromDegrees,float ToDegrees);
    void FinishWhirlwindTraining();
    void FinishWhirlwind();
    int32 NextSlash=0, SwingPoison=0, SwingTrainingHits=0;
    FColdSteelSkillShot SwingSkills;
    double LastAttackEnd=-100.;
    double ChargeStartedAt=0.;
    float CancelChargeFrom=0.f, CancelChargeAge=0.f, CancelChargeDuration=.4f;
    bool bAttacking=false, bEquipping=false, bInspecting=false, bQueuedAttack=false;
    bool bCharging=false, bReturningCharge=false, bHeavyAttack=false, bSwingCuePlayed=false;
    bool bThrustAttack=false, bLungeStarted=false, bLungeBlocked=false;
    // Independent quick-combat strike: the counterweight leads instead of the blade.
    bool bPommelAttack=false;
    // 快速进战技能打击：使用配重锤动作，伤害/击退/眩晕与范围来自技能公式。
    bool bQuickCombatStrike=false,bQueuedQuickCombat=false,QuickCombatKillPending=false;
    float QuickCombatStunSeconds=0.f,QuickCombatKnockbackCM=0.f;
    // 命中走手枪版同一份合同（QuickCombatContractHit）：距离用技能 rangeCM，
    // 不再借用普通挥击的 SwingReach；接触帧只判一次。
    float QuickCombatRangeCM=200.f;
    bool bQuickCombatContactDone=false;
    // 下劈动作本身仍可独立调用；冲刺技能衔接独立持剑前摇并使用扇区结算，不附加位移。
    bool bOverheadAttack=false;
    bool bDashAttack=false,bDashTrainingPending=false,bDashCenterCaptured=false;
    // 保留已打开编辑器对象的字段布局；旧突进累计值不再驱动位移。
    float DashSprintSeconds=0.f,DashTravelCM=0.f,DashBounceLeftCM=0.f;
    int32 DashHits=0,DashKills=0;
    FDashAttackCast DashCast;
    FVector DashCenter=FVector::ZeroVector;
    void TickDashReadiness(float Delta);
    void DashAttackContractHit();
    void FinishDashAttack();
    bool HasTacticalSprintAnimations() const;
    bool IsTacticalSprintClip(FName Clip) const;
    bool TickTacticalSprintPose(float Delta);
    float PommelDepthCM=RuneSwordPommelRhythm::CounterweightCM;
    FVector LungeDirection=FVector::ZeroVector;
    bool bRiftActive=false;
    bool bGuardHeld=false,bGuarding=false,bReturningGuard=false,bGuardReacting=false,bGuardBreakPose=false;
    float GuardPoseTime=0.f,GuardReactionRate=1.f,GuardFeedbackStrength=0.f;
    double GuardStartedAt=0.,GuardFeedbackAt=-100.;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    bool CanUse() const;
    bool StartSwing(FName Clip, bool Heavy, float StaminaOverride=-1.f);
    bool StartQuickCombatStrike();
    void QuickCombatContractHit();
    FVector AdvanceThrustLunge(float FromTime,float ToTime);
    void ReturnFromCharge();
    void SetClip(FName Name, bool bLoop);
    void SamplePose(float Time);
    FRuneSwordBladeSample ReadBlade(const FTransform& AimFrame) const;
    void SweepBlade(const FRuneSwordBladeSample& From,const FRuneSwordBladeSample& To);
    void ApplySwingHits(const TArray<FHitResult>& Hits,const FVector& Direction);
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
