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
#include "AzureDragonReach.h"
#include "MeleeWeaponStats.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "UObject/StrongObjectPtr.h"
#include "RuneSwordComponent.generated.h"

class AFPSGAMECharacter;
class UCameraComponent;
class USkeletalMeshComponent;
class USkeletalMesh;
class UAnimSequence;
class USoundBase;
class UColdSteelStatusModel;
class UStaticMesh;
class UStaticMeshComponent;
class USceneComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UAzureDragonEnergyComponent;
class UFPSCombatHealthComponent;
class UNiagaraSystem;
class UDynamicMeshComponent;
struct FStreamableHandle;

/** One recorded point of an Azure Dragon rake's five talon paths, in the claws' body frame. */
struct FAzureDragonTrailSample
{
    float Time=0.f;
    FVector3f Tips[5];
};

/** One rake's five talon rift scars: the bounded tip path, cut while raking, then held and dissolved. */
struct FAzureDragonRift
{
    TArray<FAzureDragonTrailSample> Path;
    float LastCut=-10.f,Width=0.f;
    uint8 Claw=255;
};

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
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsBusy() const { return bUppercut || bWhirlwind || bAttacking || bEquipping || bCharging || bReturningCharge || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose; }
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginInspect();
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsInspecting() const { return bInspecting; }
    bool IsEquipping() const { return bEquipping; }
    bool CanReleaseSupportHand() const
    { return !(bUppercut || bWhirlwind || bAttacking || bEquipping || bCharging || bReturningCharge || bGuardReacting || bGuardBreakPose); }
    USkeletalMeshComponent* ArmsMesh() const { return Viewmodel; }
    bool IsQuickCombatActive() const { return bQuickCombatStrike; }
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
    bool BeginUppercut();
    bool CanBeginUppercut() const;
    FString UppercutStatusText() const;
    bool BeginWhirlwind();
    bool IsWhirlwindActive() const { return bWhirlwind; }
    bool TryBeginDashAttack();
    bool IsDashAttackActive() const { return bDashAttack; }
    float DashReadyFraction() const;
    /** A physical sprint release ends readiness without cancelling an active attack. */
    void ResetDashReadiness() { DashSprintSeconds=0.f; }
    /** Authored carry progress, used by the shared footstep-driven sprint camera. */
    float TacticalSprintPoseWeight() const;
    /** 快速进战：以独立配重锤动作发动技能打击（伤害/击退/眩晕走技能公式）。 */
    UFUNCTION(BlueprintCallable, Category="Rune Sword") bool BeginQuickCombatStrike();
    void CancelAction();
    bool GetFireMagicBladePoints(FVector& Base,FVector& Tip) const;
    /** Presentation attachment, independent of the combat-only Blade_Base/Tip animation tracks. */
    bool GetEnchantmentBladeAttachment(USceneComponent*& Parent,FName& Socket,FTransform& LocalFrame,float& Length) const;
    /** Online clients resolve hits on the server: its receipt stands in for the local result when charging Azure Dragon. */
    void NotifyAzureDragonNetHit(AActor* Target,float Applied,bool bKilled);
    /** Online: the owner's cosmetic Azure Dragon state for the body presentation (flags: bit0 active,
     *  bit1 claw strike, bit2 right claw, bits3-4 stroke 0 horizontal/1 heavy/2 overhead/3 rising, bit5 heavy windup,
     *  bit6 dissolve, bit7 faster death dissolve). */
    void SampleAzureDragonNet(uint8& Flags,float& SourceLength,float& Entry,float& ChargeStart,float ServerNow) const;
    /** Online: another player's claws on this machine, from their replicated body state (source seconds). */
    void PresentAzureDragonRemote(uint8 Flags,float Source,float StrikeContactStart,float StrikeContactEnd,float Entry,float Held);
private:
    friend class URuneSwordAuditCommandlet;
    friend class UFPSConsumableAuditCommandlet;
    friend class UFPSPlayerBodyComponent;
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<class USceneComponent> JumpPresentationRoot;
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
    UPROPERTY(Transient) TObjectPtr<USoundBase> BlockSoundAlternate;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ParrySound;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> RiftVisual;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RiftMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> RiftMeshes;
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UStaticMesh> SlashWaveMeshAsset;
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UMaterialInterface> SlashWaveMaterialAsset;
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UNiagaraSystem> SlashWaveMotesAsset;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> SlashWaveMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> SlashWaveMaterial;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> SlashWaveMotes;
    TSharedPtr<FStreamableHandle> SlashWaveLoad;
    float SwingWaveRange=0.f,SwingWaveScale=0.f,SwingWaveSpeed=1800.f;
    void ReleaseSlashWave(const FTransform& Aim);
    FString InstanceId;
    FString EquippedMeshPath;
    FMeleeModifiers MeleeModifiers;
    float SwingRuneVulnerability=0, SwingRuneVulnerabilitySeconds=0;
    // SwingRuneVulnerability*=剑刃攻击通道（导魔符文）；QuickCombat*=配重锤快速近战通道（凝碧星核）。
    // 金色符文强化：每次确认命中后本挥缩减技能CD的秒数与已缩减标记（每挥一次）。
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
    bool IsRisingDragonFinisher() const { return bAttacking&&SwingSkills.bRisingDragonFinisher; }
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
    float QuickCombatKnockbackCM=0.f;
    // 命中走手枪版同一份合同（QuickCombatContractHit）：距离用技能 rangeCM，
    // 不再借用普通挥击的 SwingReach；接触帧只判一次。
    float QuickCombatRangeCM=200.f;
    bool bQuickCombatContactDone=false;
    // 下劈动作本身仍可独立调用；冲刺技能在持剑前摇中前进一米，使用原扇区结算。
    bool bOverheadAttack=false;
    bool bDashAttack=false,bDashTrainingPending=false,bDashCenterCaptured=false;
    // 保留字段布局；突进由现有动作时间曲线驱动，旧累计值不参与位移。
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
    // A single parry-earned normal-input replacement, owned by this equipped sword.
    double ClovenReadyUntil=0.,ClovenGrantedAt=-100.;
    float ClovenGlow=0.f;
    void GrantClovenCounter();
    bool TryClovenCounter();
    void TickClovenCounter(float Delta);
    void ClearClovenCounter();
    TSet<TWeakObjectPtr<AActor>> HitActors;
    void TickWalkInspect(float Delta);
    void ScheduleWalkInspect(bool bAfterInspect);
    bool IsWalkInspectStride() const;
    bool ShouldBreakWalkInspect() const;
    float WalkInspectDelay=0.f;
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
    float QuickCombatBleedChance=0.f;
    bool bQuickCombatAOE=false;
    FString EquippedAnimationFolder;
    // Standalone skill motion. Soft references are preloaded once, outside input/HUD paths.
    UPROPERTY(EditDefaultsOnly,Category="Rune Sword|Uppercut") TSoftObjectPtr<UAnimSequence> UppercutStandard;
    UPROPERTY(EditDefaultsOnly,Category="Rune Sword|Uppercut") TSoftObjectPtr<UAnimSequence> UppercutLongGrip;
    TSharedPtr<FStreamableHandle> UppercutLoad;
    bool bUppercut=false;
    float UppercutReachGrowth=1.f,UppercutLowReachCM=120.f;
    void LoadUppercutAnimations();
    void TickUppercut(float Delta);
    UAnimSequence* UppercutAnimation() const;
    // Azure Dragon: equipment-owned charge/active window and two reusable claws.
    UPROPERTY(Transient) TObjectPtr<USkeletalMesh> AzureDragonMesh;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> AzureDragonGrab;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> AzureDragonMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<USkeletalMeshComponent>> AzureDragonClaws;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> AzureDragonMIDs;
    TSharedPtr<FStreamableHandle> AzureDragonLoad;
    FString AzureDragonInstance;
    bool bAzureDragonEquipped=false,bSwingAzureDragon=false;
    void RefreshAzureDragon(const FColdSteelItem* Item,UColdSteelStatusModel* Profile);
    void PrepareAzureDragon();
    void TickAzureDragon(float Delta);
    void UpdateAzureDragonPose();
    void StopAzureDragon();
    void DestroyAzureDragon();
    // Charge is session-only and belongs to the currently held enchanted sword.
    UPROPERTY(Transient) TObjectPtr<UAzureDragonEnergyComponent> AzureDragonEnergyDisplay;
    TWeakObjectPtr<UFPSCombatHealthComponent> AzureDragonHealth;
    int32 AzureDragonCharge=0,AzureDragonHitsToSummon=9;
    void OnAzureDragonHit();
    void ClearAzureDragonEnergy();
    void CaptureAzureDragonAttack(UColdSteelStatusModel* Profile);
    float AzureDragonRange(float BaseRange) const { return BaseRange*SwingAzureDragonReachMultiplier; }
    // V10.11: slash-type swings (slashes, heavy and overhead strokes, uppercut) reach from the player to
    // the claws' farthest talon point while active; thrust, pommel, dash, whirlwind and quick combat keep
    // AzureDragonRange (x1.5).
    bool AzureDragonClawSwing() const
    { return bSwingAzureDragonActive&&!bThrustAttack&&!bPommelAttack&&!bDashAttack&&!bWhirlwind&&!bQuickCombatStrike; }
    float AzureDragonSwingRange(float BaseRange) const
    { return AzureDragonClawSwing()?FMath::Max(BaseRange,AzureDragonReach::ClawReachCM):AzureDragonRange(BaseRange); }
    float AzureDragonActiveUntil=0.f,AzureDragonSeconds=30.f,AzureDragonReachMultiplier=1.5f;
    float AzureDragonPhysicalMultiplier=2.f,AzureDragonMagicScale=1.f,SwingAzureDragonReachMultiplier=1.f;
    bool bSwingAzureDragonActive=false;
    bool bSwingAzureDragonCharged=false;
    // Append cosmetic state so existing sword members keep their layout.
    uint8 AzureDragonNextClaw=0,SwingAzureDragonClaw=0;
    // Five talon rift scars per rake, two scar sets (one reusable ribbon mesh each) so the last rake's
    // scars keep dissolving while the next rake cuts new ones.
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> AzureDragonTrailMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UDynamicMeshComponent>> AzureDragonRiftMeshes;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> AzureDragonRiftMIDs;
    FAzureDragonRift AzureDragonRifts[2];
    int32 AzureDragonRiftCutting=INDEX_NONE;    // scar set the current rake is cutting
    void UpdateAzureDragonTrail(const FVector& Origin,const FQuat& Frame,const FVector& Eye,int32 Claw,float Strength,float Size);
    // Unseen custom-depth followers (front-surface test for the glass) and the arm-end fire cards.
    UPROPERTY(Transient) TArray<TObjectPtr<USkeletalMeshComponent>> AzureDragonClawDepth;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> AzureDragonFlameMaterial;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> AzureDragonFlames;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> AzureDragonFlameMID;
    void UpdateAzureDragonFlames(const FVector& Eye,const FQuat& View,const float* ClawStrength);
    // One camera punch and claw flash per rake, when it crosses the contact point.
    bool bAzureDragonImpactFired=false;
    float AzureDragonImpactTime=-10.f;
    // World-space body anchor (eye position + yaw) followed with inertia; the claws live in this frame.
    FVector AzureDragonAnchor=FVector::ZeroVector;
    float AzureDragonAnchorYaw=0.f;
    bool bAzureDragonAnchored=false;
    // Idle-loop clock per claw (V10.10): restarted when its rake ends; < 0 = unset (desynced on summon).
    float AzureDragonIdleStart[2]={-1.f,-1.f};
    // V10.12: claw side from the blade's lateral motion (clip -> +1 right claw, -1 left, 0 vertical),
    // measured once per clip and weapon; a short transform blend whenever a claw changes what it is
    // doing (strike start, cancel, combo hand-over, charge release); per-frame claw-line target band.
    TMap<FName,int8> AzureDragonClipSide;
    float AzureDragonSwingLateral=0.f;          // this swing's blade travel to the right (aim space, cm)
    void ChooseAzureDragonClaw();
    uint32 AzureDragonSwingSerial=0,AzureDragonClawMode[2]={0u,0u};
    float AzureDragonStrikeEntry=-1.f,AzureDragonBlendStart[2]={-10.f,-10.f};
    FVector AzureDragonShownPalm[2]={FVector::ZeroVector,FVector::ZeroVector},AzureDragonBlendPalm[2]={FVector::ZeroVector,FVector::ZeroVector};
    FQuat AzureDragonShownRotation[2]={FQuat::Identity,FQuat::Identity},AzureDragonBlendRotation[2]={FQuat::Identity,FQuat::Identity};
    bool bAzureDragonShown=false;
    bool AzureDragonClawBand(const FVector& Origin,float& OutNear,float& OutFar);
    uint64 AzureDragonBandFrame=0;
    float AzureDragonBandNear=0.f,AzureDragonBandFar=0.f;
    // V10.13: one presented frame of the claws, from the owner's sword state or from another player's
    // replicated body state on this machine.
    struct FAzureDragonFrame
    {
        bool bActive=false,bStriking=false,bCharging=false,bVertical=false,bRising=false,bHeavy=false;
        uint8 Claw=0;
        float Source=0.f,HitStart=0.f,HitEnd=0.f,Entry=-1.f,Held=0.f,Rate=1.f,SummonAge=0.f;
        bool bDissolving=false;                                      // V10.14 expiry: erode and blow away
        float DissolveStart=-100.f,DissolveAge=0.f,DissolveRate=1.f; // age already scaled by the rate
        int32 MoteBudget=0;                                          // motes per claw for this viewer
        FVector Eye=FVector::ZeroVector,ViewEye=FVector::ZeroVector; // the claws' owner / the viewing camera
        float Yaw=0.f;
        FRotator View=FRotator::ZeroRotator;
        class APlayerController* ShakePC=nullptr;                    // the owner's camera only
    };
    bool LocalAzureDragonFrame(FAzureDragonFrame& Out) const;
    void PresentAzureDragon(const FAzureDragonFrame& Frame);
    bool bAzureDragonRemote=false,bAzureDragonRemoteActive=false,bAzureDragonRemoteStriking=false;
    float AzureDragonRemoteSummonAt=0.f,AzureDragonRemoteLastSource=0.f;
    // V10.14: on expiry the claws erode along a wind front and blow away as motes: CPU-simulated
    // camera-facing quads in one fixed-topology mesh, seeded once per dissolve from a bounded set of
    // skinned vertices, only live motes updated (positions only), hidden when done.
    struct FAzureDragonMote
    {
        FVector Local=FVector::ZeroVector,Position=FVector::ZeroVector,Velocity=FVector::ZeroVector;
        float Birth=0.f,Life=1.f,Size=10.f,Phase=0.f;
        bool bBorn=false,bDead=false;
    };
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> AzureDragonDustMaterial;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> AzureDragonDust;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> AzureDragonDustMID;
    TArray<FAzureDragonMote> AzureDragonMotes;
    float AzureDragonDissolveStart=-100.f,AzureDragonSummonedAt=0.f,AzureDragonMoteSeed=-1000.f;
    float AzureDragonRemoteDissolveAt=-100.f;
    bool bAzureDragonRemoteDissolving=false;
    // V10.15: expiry, death, weapon switch, unequip and enchant removal all start the dissolve (death
    // faster, finishing before the respawn); gameplay state still clears at once.
    float AzureDragonDissolveRate=1.f,AzureDragonRemoteDissolveRate=1.f;
    void BeginAzureDragonDissolve(float Rate);
    void UpdateAzureDragonDust(const FAzureDragonFrame& Frame,const FVector& Wind,const FVector* Center,const FVector* Axis);
    bool bPanChiUppercut=false;
    float PanChiUppercutDamage=0.f;
};
