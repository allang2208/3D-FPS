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
#include "TwoHandInspectAudio.h"
#include "AzureDragonReach.h"
#include "MeleeWeaponStats.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "UObject/StrongObjectPtr.h"
#include "HighlandOathRune.h"
#include "GaleWingGuard.h"
#include "RingChainRebound.h"
#include "RuneSwordComponent.generated.h"

class AFPSGAMECharacter;
class UCameraComponent;
class USkeletalMeshComponent;
class USkeletalMesh;
class UAnimSequence;
class USoundBase;
class UColdSteelStatusModel;
class UProductionToolComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMeshComponent;
class USceneComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UAzureDragonEnergyComponent;
class UFPSCombatHealthComponent;
class UNiagaraSystem;
class UDynamicMeshComponent;
struct FStreamableHandle;
enum class ESwordGripMode : uint8;

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
    void SpawnAuthoritySlashWave(const FTransform& Aim,float WaveDamage,float Range,float Speed,const FColdSteelSkillShot& Shot);
    uint32 RiftReleaseSerial=0;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;
    void RefreshEquipment(UColdSteelStatusModel* Profile);
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsEquipped() const { return !InstanceId.IsEmpty(); }
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsBusy() const { return bChainSlashPending || bChainSlash || bUppercut || bWhirlwind || bAttacking || bEquipping || bCharging || bReturningCharge || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose || bKnockdownPose; }
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginInspect();
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsInspecting() const { return bInspecting; }
    bool IsEquipping() const { return bEquipping; }
    bool IsStarMarrowChargeMotionReady() const;
    bool IsStarMarrowChargeMotionPlaying() const;
    bool BeginStarMarrowChargeMotion(float Age=0.f);
    void CancelStarMarrowChargeMotion();
    bool CanReleaseSupportHand() const
    { return !(bChainSlash || bUppercut || bWhirlwind || bAttacking || bEquipping || bCharging || bReturningCharge || bGuardReacting || bGuardBreakPose || bKnockdownPose); }
    USkeletalMeshComponent* ArmsMesh() const { return Viewmodel; }
    bool IsQuickCombatActive() const { return bQuickCombatStrike; }
    UFUNCTION(BlueprintPure, Category="Rune Sword") bool IsGuarding() const { return bGuarding; }
    /** Shared sword/warhammer defence; the hammer keeps its own tool rig. */
    bool IsGuardWeaponEquipped() const { return IsEquipped()||!ToolGuardInstance.IsEmpty(); }
    bool IsToolGuardPoseActive() const { return !ToolGuardInstance.IsEmpty()&&(bGuarding||bReturningGuard||bGuardReacting||bGuardBreakPose); }
    bool IsToolGuardBreakActive() const { return !ToolGuardInstance.IsEmpty()&&bGuardBreakPose; }
    bool IsToolGuardRequested() const { return !ToolGuardInstance.IsEmpty()&&(bGuardHeld||IsToolGuardPoseActive()); }
    bool GetToolGuardPose(FName& Clip,float& Seconds,float& Age) const;
    void AdvanceToolGuard(float Delta);
    void CancelToolGuard();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginGuard();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void ReleaseGuard();
    UFUNCTION(Server,Reliable) void ServerSetSwordGuard(const FString& Weapon,bool Raised,uint32 IntentSerial);
    UFUNCTION(Client,Reliable) void ClientSwordGuardResult(const FString& Weapon,uint8 Outcome,float StaminaSpent,double ServerAt,uint32 IntentSerial);
    UFUNCTION(Server,Reliable) void ServerBeginClovenAttack(const FString& Weapon,uint32 Serial);
    bool ApplyNetworkClovenAttack(FColdSteelSkillShot& Shot);
    void PresentGuardBreak();
    /** Player knockdown (UPlayerKnockdownComponent): the two-handed fall/lie/get-up arms on the knockdown clock. */
    void PresentKnockdown(float Age);
    float ResolveGuardDamage(float IncomingDamage,const class UDamageType* Type,class AController* Instigator,AActor* Causer);
    float EquippedDamage() const { return Damage; }
    float AttackSeconds() const { return RuneSwordRhythm::AttackEnd/AttackRate; }
    /** Camera-local centimetres and degrees, composed with the character's existing feedback. */
    void GetCameraMotion(FVector& Location, FRotator& Rotation) const;
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginAttack(bool bContinuing = false);
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginOverhead();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginPrimaryAttack();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void ReleasePrimaryAttack();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void BeginHeavyCharge();
    bool IsHeavyCharging() const { return bCharging; }
    float TakeRingChainChargeDrain(double BaseRate);
    bool IsBillingRingChainCharge() const { return bCharging && RingChargeBilledAt>=0.; }
    /** Server-only receipt opened by a completed heavy-charge release. */
    uint32 ForgedHeavyReleaseSerial() const { return ForgedHeavySerial; }
    bool IsNetworkHeavyReleaseWindowOpen(const FString& Weapon=FString()) const;
    const FColdSteelItem* ForgedHeavyContactItem(const FString& Weapon,uint32 Serial,AActor* Target) const;
    void RecordForgedHeavyTarget(AActor* Target) { ForgedHeavyTargets.Add(Target); }
    /** Converts a completed server charge into the release receipt when the
     *  reliable release RPC and the hit/rift channel arrive out of order. */
    bool ConsumeNetworkHeavyChargeForRelease(const FString& Weapon,double ReleasedAt=0.,uint32 Serial=0);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    float OathWindowRemaining() const;
    float OathReleaseFlash() const;
    const FHighlandOathPresentation& OathPresentation() const { return OathState; }
    double OathClock() const;
    float GaleSwiftRemaining() const;
    float GaleMoveScale() const { return GaleSwiftRemaining()>0.f ? GaleWing::MoveMultiplier : 1.f; }
    void RecordGalePayment(uint64 Key, const FString& Weapon, float Paid, bool bPartialCharge=false);
    void ConfirmGaleKill(uint64 Key, const FString& Weapon);
    void AccumulateGaleCharge(float Paid);
    bool HasGaleGuard(const FColdSteelItem* Item) const;
    bool HasGalePayment(uint64 Key, const FString& Weapon) const;
    void ApplyOathToShot(struct FColdSteelSkillShot& Shot) const;
    void ConfirmOathHit(const struct FColdSteelSkillShot& Shot,float Applied,const FVector& Point);
    void CommitOathRelease(double ReleasedAt,uint32 Serial);
    double OathImpactTime(const FHighlandOathPresentation& State) const;
    double OathImpactAt=-100.;
    FVector OathImpactPoint=FVector::ZeroVector;
    void ConsumeNetworkHeavyReleaseWindow();
    void CancelHeavyCharge();
    UFUNCTION(BlueprintCallable, Category="Rune Sword") void ReleaseHeavyCharge();
    UFUNCTION(BlueprintPure, Category="Rune Sword") float HeavyChargeFraction() const;
    bool TriggerHeavySkill();
    bool BeginChainSlash();
    FString ChainSlashStatusText(bool bPaid=false) const;
    bool BeginUppercut();
    bool CanBeginUppercut() const;
    FString UppercutStatusText() const;
    bool BeginWhirlwind(bool FromZhufengDash=false);
    bool IsWhirlwindActive() const { return bWhirlwind; }
    UMaterialInterface* EquipmentSurface(UMeshComponent* Mesh,int32 Slot,bool bOverlay) const;
    bool IsChainSlashActive() const { return bChainSlash; }
    bool IsPojunChainOccupied() const { return (bChainSlash||bChainSlashPending)&&ChainTool.IsValid(); }
    bool IsZhufengWhirlwindActive() const { return bWhirlwind&&bZhufengWhirlwind; }
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
    void GetFlameArmorAttachments(struct FFlameArmorAttachmentBuffer& Out) const;
    bool IsBeiweiMartialReleasing() const;
    bool IsChixiaoHeavyReleasing() const;
    bool IsZhufengWhirlwindReleasing() const;
    /** Presentation attachment, independent of the combat-only Blade_Base/Tip animation tracks. */
    const FString& DisplayedSwordInstance() const { return InstanceId; }
    bool GetEnchantmentBladeAttachment(USceneComponent*& Parent,FName& Socket,FTransform& LocalFrame,float& Length) const;
    /** Online clients resolve hits on the server: its receipt stands in for the local result when charging Azure Dragon. */
    void NotifyAzureDragonNetHit(AActor* Target,float Applied,bool bKilled);
    void GrantBroadbladeSweep(const FString& Weapon);
    bool IsBroadbladeSweepReady() const;
    float ActiveRidgeRangeScale() const;
    ESwordGripMode GripMode() const;
    bool UsesRidgeSprintCarry() const;
    bool AcceptBroadbladeContact(const FString& Weapon,uint32 Serial,AActor* Target);
    UFUNCTION(Client,Reliable) void ClientBroadbladeImpact(const FString& Weapon,uint32 Serial);
    void ConfirmRingChainHit(const FString& Weapon,uint32 Swing);
    void ClearRingChainProgress();
    bool HasRingChain(const FString& Weapon) const {return !Weapon.IsEmpty()&&Weapon==RingChainWeapon;}
    bool AcceptRingChainSweepContact(const FString& Weapon,uint32 Serial,AActor* Target,bool bAzureClaw);
    bool RingChainHeldSince(const FString& Weapon,double StartedAt) const
        {return RingChainWeapon==Weapon && StartedAt>=RingChainEquippedAt;}
    /** Online: the owner's cosmetic Azure Dragon state for the body presentation (flags: bit0 active,
     *  bit1 claw strike, bit2 right claw, bits3-4 stroke 0 horizontal/1 heavy/2 overhead/3 rising, bit5 heavy windup,
     *  bit6 dissolve, bit7 faster death dissolve). */
    void SampleAzureDragonNet(uint8& Flags,float& SourceLength,float& Entry,float& ChargeStart,float ServerNow) const;
    /** Online: another player's claws on this machine, from their replicated body state (source seconds). */
    void PresentAzureDragonRemote(uint8 Flags,float Source,float StrikeContactStart,float StrikeContactEnd,float Entry,float Held);
private:
    friend bool RingChainRebound::IsReady(APawn*,const FColdSteelItem&,double);
    friend bool RingChainRebound::Consume(APawn*,const FColdSteelItem&,double);
    void RefreshRingChain(const FColdSteelItem* Item);
    bool RingChainReadyAt(const FColdSteelItem& Item,double StartedAt) const;
    void PlayRingChainReady() const;
    UFUNCTION(Client,Reliable) void ClientRingChainWindow(const FString& Weapon,uint32 Swing,double Until);
    UFUNCTION(Server,Reliable) void ServerAcknowledgeRingChain(const FString& Weapon,uint32 Swing);
    RingChainRebound::FProgress RingChainProgress;
    FString RingChainWeapon;
    double RingChainEquippedAt=0.;
    uint32 RingChainGrant=0,RingChainAcknowledged=0;
    void RefreshOath(const struct FColdSteelItem* Item);
    void BeginOathCharge(double Start,double Duration);
    void ClearOath();
    void TickOath();
    struct FGalePayment
    {
        FString Weapon;
        double RecordedAt = 0.;
        float Unreturned = 0.f;
        bool bHasStrikeCost = false;
        bool bHasPartialCharge = false;
        bool bKillRefunded = false;
    };
    TMap<uint64, FGalePayment> GalePayments;
    float GaleChargePaid = 0.f;
    uint32 LocalGaleSkillSerial = 0;
    uint64 ChainGaleKey = 0;
    UPROPERTY(ReplicatedUsing=OnRep_GaleSwiftUntil) double GaleSwiftUntil = 0.;
    UFUNCTION() void OnRep_GaleSwiftUntil();
    void TickGaleSwift();
    float TakeGaleCharge();
    void CreditGaleStamina(UColdSteelStatusModel* Model,float Amount);
    UPROPERTY(Replicated) FHighlandOathPresentation OathState;
    UPROPERTY(Transient) TObjectPtr<class UOathJudgmentVisualComponent> OathVisual;
    UPROPERTY(Transient) TObjectPtr<USoundBase> OathReadySound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> OathHitSound;
    TSharedPtr<struct FStreamableHandle> OathSoundLoad;
    bool bOathInstalled=false,bOathChimed=false,bOathRefunded=false;
    uint32 OathAttackSerial=0,OathRefundReceipt=0;
    double OathReceiptUntil=0.,OathReleaseStamp=0.;
    float OathPaidRelease=0.f;
    FString OathImpactWeapon;
    double OathImpactRelease=-100.;
    UFUNCTION(NetMulticast,Unreliable) void MulticastOathImpact(const FString& Weapon,double ReleaseAt,double HitAt,FVector_NetQuantize Point);
    UFUNCTION(Client,Reliable) void ClientOathRefund(uint32 Serial,double Total);
    void LoadStarMarrowMotion(const FString& Definition,const FString& Folder);
    TSharedPtr<FStreamableHandle> StarMarrowMotionLoad;
    void InitializePresentation();
    void RefreshBeiwei(const struct FColdSteelItem* Item);
    void TickBeiweiTrail();
    FString BeiweiInstance;
    FString ZhufengTrailInstance;
    FString TimeSandTrailInstance;
    UPROPERTY(Transient) TObjectPtr<class UBeiweiSwordTrailComponent> BeiweiTrail;
    friend class URuneSwordAuditCommandlet;
    friend struct FRingChainWireProbe;
    friend class USkillNetworkAuditCommandlet;
    friend class UWarhammerNetworkAuditCommandlet;
    friend class UFPSConsumableAuditCommandlet;
    friend class UFPSPlayerBodyComponent;
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<class USceneComponent> JumpPresentationRoot;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Viewmodel;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> ModularSword;
    FVector ModularBladeBase=FVector::ZeroVector,ModularBladeTip=FVector::ZeroVector;
    FVector ModularTraceTip=FVector::ZeroVector;
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
    UPROPERTY(Transient) FTwoHandInspectAudio InspectAir;
    UPROPERTY(Transient) TObjectPtr<USoundBase> InspectCatchSound; // inspect: the fist takes the sword (GuanLei catch)
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> RiftVisual;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RiftMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> OathRiftMaterial;
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
    // Crystal sword's independent legendary blade: ordinary combo release only.
    bool bRiftPiercerSwing=false;
    uint32 RiftPiercerSerial=0,RiftPiercerAcceptedSerial=0;
    uint8 RiftPiercerAcceptedStage=0;
    double RiftPiercerAcceptedAt=-100.;
    FString RiftPiercerAcceptedWeapon,RiftPiercerAcceptedData;
    void ReleaseRiftPiercer(const FTransform& Aim);
    void SpawnRiftPiercer(const FTransform& Aim,const struct FColdSteelItem& Item,float ThirdDamage,float ThrustReach,const FColdSteelSkillShot& Snapshot);
    UFUNCTION(Server,Reliable) void ServerRiftPiercerRelease(uint32 Serial,const FString& Weapon,uint8 Stage,FVector_NetQuantize Origin,FVector_NetQuantizeNormal Direction,bool AzureDragon);
    FString InstanceId;
    FString EquippedMeshPath;
    FMeleeModifiers MeleeModifiers;
    FString ToolGuardInstance;
    FMeleeModifiers ToolGuardModifiers;
    FName ToolGuardClip;
    float ToolGuardAge=0.f;
    void RefreshToolGuardEquipment(UColdSteelStatusModel* Profile);
    uint32 GuardIntentSerial=0,ServerGuardIntentSerial=0;
    void ReceiveGuardResult(const FString& Weapon,uint8 Outcome,float StaminaSpent,double ServerAt,uint32 IntentSerial);
    const struct FColdSteelItem* GuardItem(const UColdSteelStatusModel* Profile) const;
    const FString& GuardWeaponInstance() const { return ToolGuardInstance.IsEmpty()?InstanceId:ToolGuardInstance; }
    const FMeleeModifiers& GuardModifiers() const { return ToolGuardInstance.IsEmpty()?MeleeModifiers:ToolGuardModifiers; }
    float GuardRaiseSeconds() const;
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
    bool bRingInputInstalled=false,bRingInputBuffered=false,bRingHoldAttempted=false;
    bool bReboundHeavyCharge=false;
    double RingPrimaryDownAt=-1.,RingChargeBilledAt=-1.,RingChargeFullAt=0.;
    float RingChargeStaminaScale=1.f;
    void AdvanceRingPrimaryHold();
    void StartHeavyCharge(double InputStart);
    bool PrepareHeavyCharge(const FColdSteelItem& Item,UColdSteelStatusModel* Model,double Start,double& Duration);
    void SettleRingChainCharge(UColdSteelStatusModel* Model);
    void SettleNetworkRingHold(UColdSteelStatusModel* Model,double Held);
    double HeavyInputReleaseStamp() const;
    float BillRingChargeUntil(double End,double BaseRate);
    double HeavyReleaseCost(const FColdSteelItem* Item,const UColdSteelStatusModel* Model) const;
    bool bAutoHeavyRelease=false,bHeavyTrainingPending=false;
    int32 HeavyTrainingHits=0,HeavyTrainingKills=0;
    void FinishHeavyTraining();
    bool bChixiaoEquipped=false,bChixiaoHeavy=false;
    int32 ChixiaoStrikeIndex=-1;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ChixiaoStandard;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ChixiaoLongGrip;
    TSharedPtr<FStreamableHandle> ChixiaoLoad;
    void RefreshChixiao(const FColdSteelItem* Item);
    UAnimSequence* ChixiaoAnimation() const;
    void TickChixiaoHeavy(float Delta);
    void ChixiaoCameraMotion(FVector& Location,FRotator& Rotation) const;
    bool bWhirlwind=false,bWhirlwindTrainingPending=false;
    bool bZhufengWhirlwind=false;
    float ZhufengSpeed=0.f;
    FVector ZhufengDirection=FVector::ZeroVector;
    void AdvanceZhufeng(float FromTime,float ToTime);
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
    void ApplyWhirlwindForeground();
    void RestoreWhirlwindForeground();
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
    bool bRiftUppercutReveal=false,bRiftDriftAfterReveal=false,bUppercutRiftStarted=false;
    bool bGuardHeld=false,bGuarding=false,bReturningGuard=false,bGuardReacting=false,bGuardBreakPose=false;
    bool bKnockdownPose=false;
    float GuardPoseTime=0.f,GuardReactionRate=1.f,GuardFeedbackStrength=0.f;
    double GuardStartedAt=0.,GuardFeedbackAt=-100.;
    // Server-side guard action receipts. One parry per raise and a re-raise
    // lockout stop the parry window being restarted indefinitely by toggling.
    double NetworkGuardRaisedAt=-100.,NetworkGuardLoweredAt=-100.,GuardReleasedAt=-100.;
    bool bNetworkGuardParried=false;
    // Heavy release receipt consumed by ServerReportHit/ServerReleaseRiftSlash.
    double NetworkHeavyReleaseUntil=-1.,ServerHeavyChargeStartedAt=-1.,ServerHeavyRequiredSeconds=2.;
    double ServerHeavyChargeReceivedAt=-1.,ServerHeavyChargeLastStartedAt=-1.;
    TSharedPtr<FColdSteelItem> ForgedHeavyItem;
    uint32 ForgedHeavySerial=0;
    TSet<TWeakObjectPtr<AActor>> ForgedHeavyTargets;
    // A single parry-earned normal-input replacement, owned by this equipped sword.
    double ClovenReadyUntil=0.,ClovenGrantedAt=-100.;
    float ClovenGlow=0.f;
    void GrantClovenCounter();
    void SendGuardIntent(bool Raised);
    bool CanMaintainNetworkGuard() const;
    void TickNetworkGuard();
    void SetHeavyCharging(bool Charging,bool bReleasedHeavy=false,uint32 PartialSwingSerial=0);
    bool CanMaintainHeavyCharge() const;
    void TickNetworkHeavyCharge();
    UFUNCTION(Server,Reliable) void ServerSetSwordHeavyCharge(const FString& Weapon,bool Charging,bool bReleasedHeavy,double ClientStartedAt,uint32 AttackSerial=0);
    UFUNCTION(Client,Reliable) void ClientCancelSwordHeavyCharge(const FString& Weapon);
    bool ClaimNetworkClovenAttack(uint32 Serial);
    uint32 NetworkBladeSerial=0,ConsumedClovenSerial=0,ClovenReceivedSerial=0;
    double ClovenAttackUntil=0.;
    FString ClovenAttackWeapon;
    float ClovenAttackPhysical=1.f,ClovenAttackToughness=1.f;
    bool TryClovenCounter();
    void TickClovenCounter(float Delta);
    void ClearClovenCounter();
    UFUNCTION(Server,Reliable) void ServerStartBroadbladeSweep(const FString& Weapon,uint32 Serial);
    void RefreshBroadblade(const FColdSteelItem* Item);
    void RefreshRingChainSweep();
    void RefreshRidgeThrust(const FColdSteelItem* Item);
    void PresentRidgeGather();
    UPROPERTY(Transient) TObjectPtr<class UHighlandRidgeGatherComponent> RidgeGather;
    bool BeginBroadbladeSweep();
    bool CommitBroadbladeSweep(const FString& Weapon,uint32 Serial);
    bool bBroadbladeInstalled=false;
    double SweepReadyUntil=0.,SweepServerHitUntil=0.;
    float SweepHitPause=0.f;
    uint32 SweepServerSerial=0,SweepReceivedSerial=0;
    TSet<TWeakObjectPtr<AActor>> SweepServerTargets;
    TSharedPtr<FStreamableHandle> BroadbladeLoad;
    TSharedPtr<FStreamableHandle> RingSweepLoad;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    void TickWalkInspect(float Delta);
    void ScheduleWalkInspect(bool bAfterInspect);
    bool IsWalkInspectStride() const;
    bool ShouldBreakWalkInspect() const;
    float WalkInspectDelay=0.f;
    bool CanPresent() const;
    bool CanUse(bool bContinuing = false) const;
    bool StartSwing(FName Clip, bool Heavy, float StaminaOverride=-1.f, bool bUseWeaponAttackSpeed=true, bool bDash=false);
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
    bool TickKnockdown(float Delta);
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
    bool bChainSlash=false;
    bool bChainSlashPending=false,bChainSlashTrainingPending=false;
    uint32 ChainSlashSerial=0;
    uint32 ChainSlashReceivedSerial=0;
    int32 ChainSlashCut=0,ChainSlashKills=0;
    TSet<TWeakObjectPtr<AActor>> ChainSlashKilledTargets;
    TWeakObjectPtr<UColdSteelStatusModel> ChainSlashRewardModel;
    float ChainSlashDamage=0.f;
    TArray<float,TInlineAllocator<4>> ChainSlashContacts;
    UAnimSequence* ChainSlashAnimation(bool Pojun=false) const;
    TWeakObjectPtr<UProductionToolComponent> ChainTool;
    float ChainGripRate=1.f;
    float ChainSlashActionRate() const;
    FString ChainWeaponId;
    bool StartChainSlash(bool bPaid=false);
    void FinishChainSlashTraining();
    void TickChainSlash(float Delta);
    void HitChainSlashRange(const FTransform& Aim);
    uint8 ChainImpactMask=0;
    int32 ChainLastImpact=INDEX_NONE, ChainRibbonCut=INDEX_NONE;
    double ChainImpactAt=-1., ChainWaveAt=-1.;
    float ChainWaveScale=1.f;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> ChainImpactWave;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ChainWaveMaterial;
    void ApplyChainImpact(int32 Cut);
    void ChainSlashCamera(FVector& Location,FRotator& Rotation) const;
    void PresentChainRibbon();
    void TickChainWave();
    UFUNCTION(Client,Reliable) void ClientChainImpact(uint32 Serial,int32 Cut);
    UFUNCTION(NetMulticast,Unreliable) void MulticastChainContact(AActor* Target,FVector_NetQuantize10 Point,FVector_NetQuantizeNormal Normal,bool bPulse,bool bFinalCut);
    UFUNCTION(Server,Reliable) void ServerChainSlash(const FString& Weapon,uint32 Serial,bool bStart,bool bPojun);
    UFUNCTION(Client,Reliable) void ClientChainSlashResult(uint32 Serial,bool bAccepted,double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt);
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
    uint32 RingSweepReleaseSerial=0;
    TSet<TWeakObjectPtr<AActor>> RingSweepTargets;
};
