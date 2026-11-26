#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../../Skills/FPSCastingMeshComponent.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "../../Skills/ShadowStepTypes.h"
#include "KukriArmsMeshComponent.h"
#include "KukriModuleVisual.h"
#include "OffhandKukriComponent.generated.h"

class UCameraComponent;
class UAnimSequence;
class UDynamicMeshComponent;
class UMaterialInstanceDynamic;
class UPrimitiveComponent;
class USoundBase;
class UStaticMeshComponent;
class UColdSteelStatusModel;
struct FStreamableHandle;

/** Native V9 left arm holding the reversed kukri beside the main-hand pistol (first person only). */
UCLASS()
class FPSGAME_API UOffhandKukriArmsMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    FVector RightHandInCamera=FVector::ZeroVector;
    // Whole native arm translation for the staff's below-frame grip handoff; zero for the pistol pair.
    FVector PresentationOffset=FVector::ZeroVector;
    float AimWeight=0.f;
    /** 0 = on the stance, 1 = dropped out of view below (equip entry, reload, consumables): the fist follows a
     *  pulled-back arc and the blade tips down, the shoulder stays and the elbow re-solves. */
    float LowerWeight=0.f;
    float DrawTime=-1.f;
    /** >= 0: the quick-melee flourish samples its key table instead of the stance lerp. */
    float StrikeTime=-1.f;
    /** >= 0: the mirrored uppercut samples its key table instead of the stance lerp. */
    float UppercutTime=-1.f;
    /** >= 0: ShadowStepSlash (Stage 1 / Stage 2) samples OffhandShadowStepMotion. */
    float ShadowStepTime=-1.f;
    bool bShadowStepStage2=false;
    virtual void FinalizeBoneTransform() override;
private:
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TArray<FTransform> Reference,Source,SourceUpper,SourceShadowStep,Target;
    TArray<int32> LeftBones,RightBones;
    int32 Clavicle=INDEX_NONE,Upper=INDEX_NONE,Lower=INDEX_NONE,Hand=INDEX_NONE,Twist01=INDEX_NONE,Twist02=INDEX_NONE;
    void CacheRig();
};

/** Pistol cross-arm carry and below-frame raise on the native axe arm used by the chop. */
UCLASS()
class FPSGAME_API UPistolHatchetArmsMeshComponent : public UKukriArmsMeshComponent
{
    GENERATED_BODY()
public:
    void ConfigureCarry();
    bool bCrossedCarry=false;
    float CarryWeight=1.f;
    FVector CarryAnchorInCamera=FVector::ZeroVector;
    float AimWeight=0.f;
    virtual void FinalizeBoneTransform() override;
private:
    FQuat CarryHandInCamera=FQuat::Identity;
    TArray<int32> CarryBones;
    TArray<FTransform> CarryPose;
    int32 Clavicle=INDEX_NONE,Upper=INDEX_NONE,Lower=INDEX_NONE,Hand=INDEX_NONE,Twist01=INDEX_NONE,Twist02=INDEX_NONE;
};

/**
 * Off-hand kukri paired with a main-hand pistol: the BV1hQnh6hEio knife-and-gun hold.
 * Hip: the pistol is centred and canted, the left forearm crosses under the right one.
 * ADS: native sight line, the left wrist stays crossed under the right wrist.
 * Author data: SourceAssets/DualPistolKukri20261025 (OffhandKukriAuthoredPose.h).
 */
UCLASS(ClassGroup=(Weapons))
class FPSGAME_API UOffhandKukriComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UOffhandKukriComponent();
    static bool IsOffhandKukri(const struct FColdSteelItem& Item);
    /** Equipped beside a main-hand pistol on this pawn (local first-person presentation). */
    static bool IsEquippedOn(const AActor* Owner);
    /** The kukri arm currently owns the visible left hand. */
    static bool PresentsLeftHand(const AActor* Owner);
    bool IsEquipped() const {return bEquipped;}
    bool OwnsLeftHand() const;
    void OnPistolEquipStarted();
    USkeletalMeshComponent* ArmsMesh() const;
    UStaticMeshComponent* WeaponMesh() const {return Blade;}
    /** Hip framing / right-arm recomposition weight; ADS unwinding is applied by the viewmodel. */
    float PistolFramingWeight() const {return RightWeight*RightWeight*(3.f-2.f*RightWeight);}
    void PrepareQuickRift();
    void ApplyPistolRightArm(USkeletalMeshComponent& Gun,TArray<FTransform>& Pose);
    void AdvanceActionBeforeCamera(float Delta);
    /** F while paired: off-hand blade thrust or hatchet overhead chop, including entry from ADS. */
    bool IsQuickCombatActive() const {return bQuickCombat;}
    bool IsPendantAttackActive(const FString& Weapon) const
    {return (bQuickCombat&&QuickShot.ItemInstance==Weapon)||(bUppercut&&UpperShot.ItemInstance==Weapon)||(bShadowStep&&ShadowStepShot.ItemInstance==Weapon);}
    float GetQuickCombatAge() const {return QuickElapsed;}
    float GetQuickCombatRate() const {return QuickActionRate;}
    bool IsHatchetQuickCombat() const {return bQuickCombat&&bHatchetQuickCombat;}
    float GetQuickCombatLength() const;
    float GetQuickCombatContact() const;
    float GetQuickCombatRelease() const;
    bool IsQuickCombatPaused() const {return QuickHitStop>0.f;}
    bool CanQuickCombat() const;
    bool BeginQuickCombat();
    void CancelQuickCombat();
    /** Uppercut (swordUppercut skill): the main-hand clip mirrored onto the left hand; the gun evades. */
    bool IsUppercutActive() const {return bUppercut;}
    float GetUppercutAge() const {return UppercutElapsed;}
    bool IsUppercutPaused() const {return UppercutHitStop>0.f;}
    bool IsUppercutLungeBlocked() const {return bUppercutLungeBlocked;}
    FString UppercutStatusText() const;
    bool BeginUppercut();
    void CancelUppercut();
    /** ShadowStepSlash (瞬步掠影斩) for Pistol+Offhand and Staff+Offhand blades/hatchets. */
    bool IsShadowStepActive() const {return bShadowStep;}
    bool IsShadowStepFollowupActive() const {return bShadowStep&&bShadowStepStage2;}
    bool IsShadowStepDashLocked() const {return bShadowStep&&!bShadowStepStage2&&ShadowStepElapsed<ShadowStep::Stage1DashEnd+.04f;}
    float GetShadowStepAge() const {return ShadowStepElapsed;}
    bool IsShadowStepPaused() const {return ShadowStepHitStop>0.f;}
    FString ShadowStepStatusText() const;
    bool BeginShadowStep();
    bool TryTriggerShadowStepFollowup();
    void GrantShadowStepFollowupWindow(uint32 Sequence,float WindowSeconds);
    float ShadowStepFollowupRemaining() const {return (bShadowStep&&!bShadowStepStage2&&bShadowStepFollowupUnlocked)?FMath::Max(0.f,ShadowStepFollowupTimer):0.f;}
    bool CanCancelShadowStepRecovery() const;
    void CancelShadowStep();
    FVector ShadowStepPressOffset() const;
    void GetCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    /** Authored gun framing replacing OffhandKukriPose::HipFraming while striking. */
    bool GetStrikeFraming(FTransform& Out) const;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    UPROPERTY(Transient) TObjectPtr<UOffhandKukriArmsMeshComponent> Arms;
    UPROPERTY(Transient) TObjectPtr<UPistolHatchetArmsMeshComponent> AxeArms;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> AxeChop;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> AxeIdle;
    bool UsesNativeAxe() const;
    void InstallAxeArms();
    FTransform SampleAxeBlade(float Time, bool Striking, float EntryLower=0.f);
    float AxeIdleAge=0.f;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Blade;
    TWeakObjectPtr<UCameraComponent> Camera;
    TWeakObjectPtr<UColdSteelStatusModel> Model;
    TSharedPtr<FStreamableHandle> Load;
    FKukriModuleVisual Modules;
    void CaptureContactEdge(const FColdSteelItem& Item);
    FVector ContactBase=KukriRhythm::BladeRoot,ContactTip=KukriRhythm::BladeTip;
    FDelegateHandle EquipmentChanged;
    bool bEquipped=false,bEquipmentResolved=false,bPair=false,bHold=false;
    float RightWeight=0.f,AimWeight=0.f;
    // Draw entry: runs whenever the knife hand takes the left hand over (pistol equip, after inspection, newly
    // equipped); the reload and consumables drive their own lower/raise.
    float EntryAge=-1.f;
    FString BladeInstance;
    enum class EDrawEntry : uint8 { None, Raise, KukriToss };
    EDrawEntry PendingDraw=EDrawEntry::None;
    bool bAssetsReady=false,bDrawHatchet=false;
    float DrawTime=-1.f;
    UPROPERTY(Transient) TObjectPtr<USoundBase> DrawTossSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> DrawCatchSound;
    bool bWasPresenting=false;
    float EntryLowerWeight() const;
    // The native support arm's first frames of the reload clip, lifted in from below.
    double NativeReloadEnteredAt=-1.;
    TArray<int32> GunLeftBones;
    void ApplyNativeReloadEntry(USkeletalMeshComponent& Gun,TArray<FTransform>& Pose);
    // Right arm recomposition cache for the current pistol rig.
    TWeakObjectPtr<USkeletalMesh> GunMesh;
    TArray<FTransform> RightReference,RightSource,RightTarget;
    TArray<int32> RightBones;
    int32 RightClavicle=INDEX_NONE,RightUpper=INDEX_NONE,RightLower=INDEX_NONE,RightHand=INDEX_NONE,RightTwist01=INDEX_NONE,RightTwist02=INDEX_NONE;
    void CacheGun(const USkeletalMeshComponent& Gun);
    void RefreshEquipment();
    void ApplyAssets();
    void UpdateVisibility();
    // Quick melee flourish (OffhandKukriStrike.cpp): author clock, contacts, camera, focus blur.
    void AdvanceQuickCombat(float Delta);
    void QuickContact();
    void ConfirmQuickImpact(const FHitResult& Hit,bool bWorld);
    void SpawnContactFX(const FHitResult& Hit,bool bWorld) const;
    void FinishQuickCombat();
    bool PrepareRiftVisual();
    void StartQuickRift();
    void BeginStrikeFocus();
    void UpdateStrikeFocus(float Strength);
    void EndStrikeFocus();
    bool bQuickCombat=false,bImpactConfirmed=false,bWallHit=false,bQuickKillPending=false;
    bool bStaffQuickCombat=false;
    bool bHatchetQuickCombat=false;
    float QuickEndTime=0.f,QuickTotalDuration=0.f;
    float QuickActionRate=1.f;
    friend class USkillNetworkAuditCommandlet;
    float QuickElapsed=0.f,QuickHitStop=0.f,QuickImpactAge=-1.f,QuickStrikeAge=-1.f,QuickImpactKick=0.f;
    // Unframed native gun palm: blade sampling is independent of gun clearance.
    FVector QuickNativePistolHand=FVector::ZeroVector;
    int32 QuickSwingsPlayed=0,QuickContactsDone=0,QuickMasteryHits=0;
    float StrikeDamage=0.f;
    FQuickCombatCast QuickCast;
    FColdSteelSkillShot QuickShot;
    TSet<TWeakObjectPtr<AActor>> QuickHitActors;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> WhooshSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> WallSound;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> ThudSounds;
    // Mirrored uppercut (OffhandKukriUppercut.cpp): paid at the release, trained once per cast,
    // martial clock = Lightning Haste x KukriRhythm::UpperTempo on the stage-3 tables.
    void AdvanceUppercut(float Delta);
    void AdvanceUppercutLunge(float From,float To);
    void UppercutTrace(const FTransform& From,const FTransform& To);
    void ConfirmUpperImpact(const FHitResult& Hit,bool bWorld);
    void ArriveUpperStrike();
    void QueueUpperFX(const FHitResult& Hit,bool bWorld);
    void ResetUpperStrike();
    void FinishUppercut(bool bTrain);
    void StartUpperRift();
    void StartShadowStepRift(bool bStage2);
    void TickUpperRift(float Delta);
    void StopUpperRift();
    void AdvanceShadowStep(float Delta);
    void AdvanceShadowStepDash(float From,float To);
    void ShadowStepTrace(const FTransform& From,const FTransform& To);
    void ConfirmShadowStepImpact(const FHitResult& Hit,bool bWorld,bool bHeavy=false);
    void ArriveShadowStepStrike();
    void QueueShadowStepFX(const FHitResult& Hit,bool bWorld);
    void FinishShadowStep(bool bTrain);
    void GetShadowStepCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    FTransform ShadowStepBladeFrame(float T) const;
    FTransform UpperBladeFrame(float T) const;
    bool bUppercut=false,bUppercutReleased=false,bUppercutTrainingPending=false;
    bool bStaffUppercut=false;
    float UppercutEndTime=0.f;
    bool bUppercutLungeStarted=false,bUppercutLungeBlocked=false;
    FVector UppercutDirection=FVector::ZeroVector;
    float UppercutElapsed=0.f,UppercutHitStop=0.f,UppercutImpactAge=-1.f,UppercutStrikeAge=-1.f,UppercutImpactKick=0.f;
    bool bUpperSwingPlayed=false,bUpperImpactConfirmed=false,bUpperWallHit=false;
    bool bUpperStrikeDone=false,bUpperPendingFlesh=false,bUpperPendingWall=false;
    FHitResult UpperPendingFleshHit,UpperPendingWallHit;
    float UpperDamage=0.f,UpperReach=150.f;
    struct FUpperPendingFX{FHitResult Hit;bool bWorld=false;};
    TArray<FUpperPendingFX> UpperPendingFX;
    TSet<TWeakObjectPtr<AActor>> UpperHitActors;
    FTransform UpperPreviousBlade;
    bool bHaveUpperPreviousBlade=false;
    FColdSteelSkillShot UpperShot;
    // Mirrored rift crescent (OffhandKukriUpper::Rift, camera space), frozen in world space at its start.
    bool bUpperRiftStarted=false,bUpperRiftActive=false;
    FTransform UpperRiftOrigin;
    FVector UpperRiftDirection=FVector::ForwardVector;
    float UpperRiftAge=0.f,UpperRiftFadeAge=-1.f;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> UpperRiftVisual;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> UpperRiftMID;
    // Background-only blur (M_WhirlwindFocus): the viewmodel writes stencil 231 and stays sharp.
    bool bFocusActive=false,bFocusSavedBlurOverride=false;
    float FocusSavedBlur=0.f;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FocusMaterial;
    struct FFocusDepth { TWeakObjectPtr<UPrimitiveComponent> Part; bool bEnabled; int32 Stencil; uint8 WriteMask; };
    TArray<FFocusDepth> FocusDepth;
    // ShadowStepSlash (OffhandKukriShadowStep.cpp): Pistol+Offhand and Staff+Offhand mirrored Stage 1 & Stage 2.
    bool bShadowStep=false,bShadowStepStage2=false,bStaffShadowStep=false;
    bool bShadowStepTrainingPending=false,bShadowStepDashStarted=false,bShadowStepDashBlocked=false,bShadowStepDashDepenetrated=false;
    bool bShadowStepFollowupUnlocked=false,bShadowStepFollowupUsed=false;
    bool bShadowStepDashWhooshPlayed=false,bShadowStepSwingPlayed=false,bShadowStepImpactConfirmed=false,bShadowStepWallHit=false;
    bool bShadowStepRiftStarted=false;
    bool bShadowStepStrikeDone=false,bShadowStepPendingFlesh=false,bShadowStepPendingWall=false,bShadowStepHeavyImpact=false;
    FHitResult ShadowStepPendingFleshHit,ShadowStepPendingWallHit;
    TArray<FUpperPendingFX> ShadowStepPendingFX;
    float ShadowStepStrikeAge=-1.f,ShadowStepPressStop=0.f;
    uint8 OffhandRiftMode=0; // 0 = Uppercut, 1 = HatchetQuick, 2 = ShadowStep1, 3 = ShadowStep2
    uint32 ShadowStepSerial=0;
    int32 ShadowStepKills=0;
    float ShadowStepElapsed=0.f,ShadowStepEndTime=0.f,ShadowStepHitStop=0.f,ShadowStepImpactAge=-1.f,ShadowStepImpactKick=0.f;
    float ShadowStepFollowupTimer=0.f;
    float ShadowStepStage1Damage=0.f,ShadowStepStage2Damage=0.f,ShadowStepReach=150.f;
    FShadowStepCast ShadowStepCast;
    FVector ShadowStepDirection=FVector::ZeroVector;
    FVector ShadowStepDashStartLocation=FVector::ZeroVector;
    TSet<TWeakObjectPtr<AActor>> ShadowStepHitActors;
    FTransform ShadowStepPreviousBlade;
    bool bHaveShadowStepPreviousBlade=false;
    FColdSteelSkillShot ShadowStepShot;
};
