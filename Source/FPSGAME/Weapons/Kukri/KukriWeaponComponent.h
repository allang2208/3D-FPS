#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "../../Skills/ShadowStepTypes.h"
#include "../../Skills/WhirlwindTypes.h"
#include "KukriModuleVisual.h"
#include "KukriPairedHeavyHit.h"
#include "KukriWeaponComponent.generated.h"

class AFPSGAMECharacter;
class UCameraComponent;
class UKukriArmsMeshComponent;
class UStaticMeshComponent;
class USceneComponent;
class UAnimSequence;
class USoundBase;
class UColdSteelStatusModel;
class UDynamicMeshComponent;
class UMaterialInstanceDynamic;
class UPrimitiveComponent;
namespace KukriRhythm{struct FStrike;}

/** Which skill rift (KukriSkillRift.cpp) is showing / built in the skill rift mesh. */
enum class EKukriSkillRift : uint8 { None, Dash, Whirlwind, ShadowStep1, ShadowStep2 };

/**
 * 尼泊尔弯刀：单手近战（主手，副手可空或持枪／魔法书）。
 * 库存拥有装备实例；本组件只负责第一人称视模、拔刀／待机／走／跑与三段连击（右→左横劈、左上→右下斜劈、
 * 单手低位戳刺；每段回到架势后才接下一段），以及挥砍命中（出手冻结伤害与攻速，命中窗内逐子步扫掠，每挥目标去重）、
 * 挥刀镜头曲线与命中顿帧。
 */
UCLASS(ClassGroup=(Weapons), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UKukriWeaponComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UKukriWeaponComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;

    static bool IsKukri(const struct FColdSteelItem& Item);
    /** 双持弯刀：主手弯刀的同组副手槽也是弯刀（第二把挂在本视模 hand_l，待机／走／跑换双持动作）。 */
    static bool IsDualOn(const AActor* Owner);
    void RefreshEquipment(UColdSteelStatusModel* Profile);
    UFUNCTION(BlueprintPure, Category="Kukri") bool IsEquipped() const { return !InstanceId.IsEmpty(); }
    bool IsDual() const { return IsEquipped()&&bDual; }
    /** Main hand empty: the off-hand kukri / hatchet acts alone in the left hand, the single moveset mirrored
     *  (UColdSteelStatusModel::ActiveKukriWeapon, the right arm hidden). */
    bool IsLoneOffhand() const { return IsEquipped()&&bLoneOffhand; }
    UFUNCTION(BlueprintPure, Category="Kukri") bool IsBusy() const { return bAttacking||bEquipping||bDashAttack||bQuickCombat||bUppercut||bHeavyCharging||bHeavyAttack||bWhirlwind||bShadowStep; }
    bool IsEquipping() const { return bEquipping; }
    bool IsAttacking() const { return bAttacking; }
    bool IsPendantAttackActive(const FString& Weapon) const
    {
        if(bStaffOffhandWhirlwind&&bWhirlwind&&Weapon==Shot.ItemInstance)return true;
        if(Weapon==InstanceId)return bAttacking||bDashAttack||bQuickCombat||bUppercut||bHeavyAttack||bWhirlwind||bShadowStep;
        return Weapon==OffhandInstanceId&&((bAttacking&&(bDualSweep||bDualThrust))||bDashAttack||(bHeavyAttack&&bDualHeavy)||(bShadowStep&&bDualShadowStep));
    }
    void BeginPrimaryAttack();
    void CancelAction();
    uint32 NetworkAttackSerial() const { return (bAttacking||bDashAttack)?Shot.KukriAttackSerial:0; }
    void RejectNetworkAttack(uint32 Serial);
    UKukriArmsMeshComponent* ArmsMesh() const { return Viewmodel; }
    /** Root of this hand's visible modular knife, for temporary cosmetic layers. */
    UStaticMeshComponent* WeaponMesh(bool Offhand=false) const { return Offhand?OffhandBlade.Get():Blade.Get(); }
    /** 挥刀镜头曲线 + 命中抖动（相对相机）；FovDelta 为垂直视场增量（度）。供角色相机更新读取。 */
    void GetCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    /** 冲刺攻击（被动技能 dashAttack，KukriDashAttack.cpp）：地面连续奔跑就绪后左键双手跳劈。 */
    float DashReadyFraction() const;
    bool TryBeginDashAttack();
    bool IsDashAttackActive() const { return bDashAttack; }
    void ResetDashReadiness() { DashSprintSeconds=0.f; }
    /** 快速近战（F，KukriQuickCombat.cpp）：刀把砸击，由 UColdSteelStatusModel::TriggerQuickCombat 分派。 */
    bool BeginQuickCombat();
    bool IsQuickCombatActive() const { return bQuickCombat; }
    /** 上挑（主动技能 swordUppercut，KukriUppercut.cpp）：参考滑铲上撩，快捷栏释放；空字符串 = 可释放。 */
    FString UppercutStatusText() const;
    bool BeginUppercut();
    bool IsUppercutActive() const { return bUppercut; }
    /** 重击（技能 heavyStrike，KukriHeavy.cpp）：左键按住蓄力、松开出手（≤0.2 s 或未蓄满 = 普通连击）；快捷栏蓄满自动出手。 */
    void ReleasePrimaryAttack();
    bool TriggerHeavySkill();
    float HeavyChargeFraction() const;
    /** Owner: the local charge; authority of a remote owner: the charge the server is billing (stamina model). */
    bool IsHeavyCharging() const;
    bool IsDualHeavyCharging() const;
    bool IsHeavyAttackActive() const { return bHeavyAttack; }
    /** Server receipt for heavy hit reports (ColdSteelPlayerState hit validation), as URuneSwordComponent's. */
    bool IsNetworkHeavyReleaseWindowOpen(const FString& Weapon) const;
    bool IsNetworkFalconHeavyRelease(const FString& Weapon) const { return bServerFalconRelease && IsNetworkHeavyReleaseWindowOpen(Weapon); }
    uint32 GetNetworkHeavyReleaseSerial() const {return NetworkHeavyReleaseSerial;}
    bool ConsumeNetworkHeavyChargeForRelease(const FString& Weapon,uint8 Phase=0,double HitStamp=0.);
    bool IsNetworkHeavyTargetNew(const FString& Weapon,AActor* Target,uint8 Phase=0) const;
    void RecordNetworkHeavyTarget(const FString& Weapon,AActor* Target,uint8 Phase=0);
    void ConfirmFalconHook(const FColdSteelSkillShot& BladeShot,const FHitResult& Contact);
    UFUNCTION(NetMulticast,Unreliable) void MulticastBladeTargetFX(const FHitResult& Hit);
    static bool PublishBladeHit(AActor* Attacker,const FHitResult& Hit,const FColdSteelSkillShot& Outcome);
    void PresentOwnerBladeHit(const FHitResult& Hit,uint32 Swing,uint8 Phase);
    void PresentBladeScenery(const FHitResult& Hit);
    /** 大旋风（主动技能 whirlwind，KukriWhirlwind.cpp）：单手持刀两圈旋转横扫，快捷栏释放；空字符串 = 可释放。 */
    FString WhirlwindStatusText() const;
    bool BeginWhirlwind();
    bool IsWhirlwindActive() const { return bWhirlwind; }
    /** 瞬步掠影斩（单手终极武技 shadowStepSlash，KukriShadowStep.cpp）：单持／左手单持／双持穿身疾斩 + 命中解锁二段反手追斩。 */
    FString ShadowStepStatusText() const;
    bool BeginShadowStep();
    bool IsShadowStepActive() const { return bShadowStep; }
    bool IsShadowStepFollowupActive() const { return bShadowStep&&bShadowStepStage2; }
    bool IsShadowStepDashLocked() const { return bShadowStep&&!bShadowStepStage2&&Elapsed<ShadowStep::Stage1DashEnd+.04f; }
    bool TryTriggerShadowStepFollowup();
    void GrantShadowStepFollowupWindow(uint32 Sequence,float WindowSeconds);
    float ShadowStepFollowupRemaining() const { return (bShadowStep&&!bShadowStepStage2&&bShadowStepFollowupUnlocked)?FMath::Max(0.f,ShadowStepFollowupTimer):0.f; }
    void PublishStaffWhirlwindBlade(const FTransform& DisplayedBlade);
    /** Owner-view yaw correction; independent of controller/world-body rotation and camera shake strength. */
    float GetWhirlwindFirstPersonYawOffset() const;
private:
    friend class UFPSPlayerBodyComponent;
    friend class UKukriNetworkAuditCommandlet;
    friend class UFPSConsumableAuditCommandlet;
    friend class USwiftFalconMotionAuditCommandlet;
    void ResetFalconHooks();
    void DrawFalconHooks();
    UFUNCTION(Server,Reliable) void ServerDrawFalconHooks(double ChargeStarted);
    UFUNCTION(NetMulticast,Reliable) void MulticastFalconMark(uint8 Hand,AActor* Target,FVector_NetQuantize10 Point,FName Bone,const FString& Weapon,float HoldSeconds,bool bLeftHand);
    UFUNCTION(NetMulticast,Reliable) void MulticastFalconDraw(uint8 ValidHands,uint8 TugHands,bool bShared,float SecondsToSnap);
    UFUNCTION(NetMulticast,Reliable) void MulticastClearFalconHooks();
    TWeakObjectPtr<AActor> FalconHookTargets[2];
    TWeakObjectPtr<class USwiftFalconHookVisual> FalconHookVisuals[2];
    bool bFalconHooksDrawn=false;
    double FalconChargeKey=0.;
    FTimerHandle FalconDrawTimer;
    void TickWhirlwind(float Delta);
    void SweepWhirlwind(float FromDegrees,float ToDegrees);
    void FinishWhirlwind(bool Interrupted=true);
    void FinishWhirlwindTraining();
    void GetWhirlwindCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    void BeginWhirlwindFocus();
    void UpdateWhirlwindFocus(float Strength);
    void EndWhirlwindFocus();
    /** Skill rifts (KukriSkillRift.cpp): the combo's space distortion on the sprint attack's chop and the whirlwind's ring. */
    bool PrepareSkillRift();
    void StartDashRift();
    void StartWhirlwindRift();
    void StartShadowStepRift(bool bStage2,bool bDualCast);
    void UpdateWhirlwindRiftPose(const FTransform& Knife);
    void TickSkillRift(float Delta);
    void StopSkillRift();
    void AdvanceShadowStep(float Delta);
    void AdvanceShadowStepDash(float From,float To);
    void TraceShadowStepBlade(const FTransform& From,const FTransform& To,bool bOffhand);
    void ConfirmShadowStepImpact(const FHitResult& Hit,bool bWorld,bool bHeavy=false);
    void ArriveShadowStepStrike();
    void QueueShadowStepFX(const FHitResult& Hit,bool bWorld);
    void FinishShadowStep(bool bTrain);
    bool CanCancelShadowStepRecovery() const;
    void GetShadowStepCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    FRotator ShadowStepViewmodelKick() const;
    FVector ShadowStepViewmodelOffset() const;
    bool CanBeginHeavyCharge() const;
    void BeginHeavyCharge();
    void SetHeavyCharging(bool bCharging,bool bRelease);
    void CancelHeavyCharge(bool bNotifyServer);
    void ReleaseHeavyCharge();
    void AdvanceHeavyCharge(float Delta);
    void AdvanceHeavy(float Delta);
    void FinishHeavy(bool bTrain);
    void CountHeavyVictim(AActor* Target,bool Killed);
    void FlushPairedHeavyContacts(bool EndWindow);
    TMap<TWeakObjectPtr<AActor>,FKukriHeavyContacts> PairedHeavyContacts;
    void TickServerHeavyCharge();
    bool PayServerHeavyRelease();
    /** Normal left click (the combo), from a press or from a tap / short charge release. */
    void StartComboClick();
    void FinishNetworkAttack(bool Cancelled=false);
    UFUNCTION(Server,Reliable) void ServerSetKukriHeavyCharge(const FString& Weapon,bool bCharging,bool bRelease,bool BothBlades,double ClientStartedAt);
    UFUNCTION(Client,Reliable) void ClientCancelKukriHeavyCharge(const FString& Weapon);
    void AdvanceUppercut(float Delta);
    void AdvanceUppercutLunge(float From,float To);
    void FinishUppercut(bool bTrain);
    void AdvanceQuickCombat(float Delta);
    void QuickContact();
    void ConfirmQuickImpact(const FHitResult& Hit,bool bWorld);
    void FinishQuickCombat();
    void GetQuickCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    FRotator QuickViewmodelKick() const;
    void TickDashReadiness(float Delta);
    void AdvanceDashAttack(float Delta);
    void DashContact();
    void SampleSkillBladeWall(const FTransform& From,const FTransform& To,const FVector& Base,const FVector& Tip,int32 Beat);
    void TrackWhirlwindWall(const FTransform& BladePose);
    int32 LastSkillWallBeat=INDEX_NONE;
    FVector WhirlwindWallBase=FVector::ZeroVector,WhirlwindWallTip=FVector::ZeroVector;
    void ConfirmDashImpact(const FHitResult& Hit);
    void FinishDashAttack();
    void GetDashCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    FRotator DashViewmodelKick() const;
    /** 视模呈现父节点的命中冲击（不改相机）。 */
    FRotator ViewmodelKick() const;
    AFPSGAMECharacter* Pawn() const;
    bool CanPresent() const;
    bool CanUse(bool bContinuing = false) const;
    void InitializePresentation();
    void SetClip(FName Name,bool bLoop,float Blend);
    void SamplePose(float Time);
    void StartAttack(int32 NewStage);
    void AdvanceAttack(float Delta);
    void TraceBlade(const FTransform& From,const FTransform& To,bool UseOffhand=false);
    void ConfirmImpact(const FHitResult& Hit,bool bWorld);
    /** Impact moment (KukriStrike.cpp, KukriRhythm::Strikes): camera accent + miss stop, deferred hit cues, contact FX. */
    void ArriveStrike();
    void QueueContactFX(const FHitResult& Hit,bool bWorld);
    void SpawnContactFX(const FHitResult& Hit,bool bWorld);
    UFUNCTION(Server,Unreliable) void ServerBladeScenery(FVector_NetQuantize10 Point,FVector_NetQuantizeNormal Normal);
    UFUNCTION(NetMulticast,Unreliable) void MulticastBladeScenery(const FHitResult& Hit);
    double LastServerScenery=-1.;
    FVector StrikeViewmodelOffset() const;
    /** Impact-moment profile of the current swing: the stage's Strikes row, the dual thrust's or the dual heavy's. */
    const KukriRhythm::FStrike& StrikeProfile() const;
    /** Presentation rows of the current swing: KukriRhythm::Swings / Rifts[Stage], or the hatchet's own chop on combo stage 3
     *  (HatchetChopRhythm.h, on stage 3's gameplay clock: same windows, impact moment and receipts). */
    const KukriRhythm::FSwing& SwingProfile() const;
    const KukriRhythm::FRift& RiftProfile() const;
    bool IsHatchetChop() const;
    /** Hatchets on the double thrust's clock: two hatchets chop down together (HatchetDualChopRhythm.h), or the hatchet hand of
     *  a hatchet + kukri pair chops while the kukri thrusts (HatchetPairRhythm.h). */
    bool IsHatchetDualChop() const;
    /** Camera of a pair chop: the dual chop's curve, half and half with the double thrust's when only one hand chops. */
    void PairChopCamera(float T,FRotator& Rotation,float& Fov,FVector* Location=nullptr) const;
    /** The pair's draw: DualEquip, or each hand's own weapon's toss when a hatchet is in the pair. */
    FName DualEquipClip() const;
    /** Swing camera of InStage at author time T (the hatchet chop's curve on its stage, KukriRhythm::SwingCamera otherwise). */
    void StageSwingCamera(int32 InStage,float T,FRotator& Rotation,float& Fov,FVector* Location=nullptr) const;
    void ResetStrike();
    /** Swing rift / sword qi (KukriRift.cpp, KukriRhythm::Rifts): the rune sword's M_RuneRift crescent on every swing. */
    void StartRift();
    void TickRift(float Delta);
    void StopRift();
    FName LocomotionClip() const;
    /** Dual hatchets' sprint-ready run (HatchetReadyRhythm.h): enter from the idle hand gesture, loop while ready, exit
     *  back.  Returns true when it owns the clip this frame. */
    bool TickReadyRun(float Delta);
    /** Dual kukri (SourceAssets/DualKukriIdle20261025): off-hand slot of the active set, second blade on hand_l. */
    void RefreshOffhand(UColdSteelStatusModel* Profile,bool DrawNewOffhand=false);
    void UpdateOffhandBlade();
    /** Dual run: the right kukri turns into the reference sprint's reverse grip with the arm's blend into the run, and back
     *  out of it (before the pose is sampled). */
    void UpdateDualFlip(float Delta);
    /** Dual draw (DualEquip): the off-hand kukri's mirrored toss on hand_l while it plays, the constant grip otherwise. */
    void UpdateOffhandDraw();
    FTransform BladeFrame() const;
    /** The off-hand SM_Kukri's grip frame in world space (dual kukri: the left blade's swing in the dual sweep). */
    FTransform OffhandBladeFrame() const;
    /** Dual sweep (combo stages 1-2 with two kukris, KukriRhythm::DualSweepClips): hand the swing over to the left blade. */
    void BeginOffhandSwing();
    /** Dual thrust (combo stage 3 with two kukris): the forward stride between author times From and To. */
    void AdvanceDualThrustLunge(float From,float To);

    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> JumpRoot;
    UPROPERTY(Transient) TObjectPtr<UKukriArmsMeshComponent> Viewmodel;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Blade;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> OffhandBlade;     // dual kukri: second assembly on hand_l
    FKukriModuleVisual MainModules,OffhandModules;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UAnimSequence>> Animations;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CurrentAnimation;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> PommelHitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> WallSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> TossSound;    // draw: knife leaves the hand
    UPROPERTY(Transient) TObjectPtr<USoundBase> CatchSound;   // draw: handle lands in the palm
    UPROPERTY(Transient) TObjectPtr<USoundBase> StabWhooshSound;            // V12c stab drive
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> StabThudSounds;     // V12c flesh thud under the hit sound
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> RiftVisual;      // swing rift ribbon (owner only)
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RiftMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WhirlwindFocus;   // background-only whirlwind blur
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> SkillRiftVisual;     // sprint-attack / whirlwind rift (owner only)
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SkillRiftMID;

    FString InstanceId;
    FString OffhandInstanceId;  // dual kukri: the off-hand kukri of the active weapon set (empty = single)
    bool bDual=false;
    // Lone off-hand blade: InstanceId is the off-hand slot's item; the viewmodel mirrors the right arm onto the left and
    // hides the right, OffhandBlade (hand_l) shows the weapon, BladeFrame() reads it, view cues are mirrored.
    bool bLoneOffhand=false;
    bool bHatchetChop=false;    // main item is the hatchet and its chop clip loaded: combo stage 3 plays HatchetAttack3
    bool bHatchetReadyRun=false;  // main item is the hatchet and the ready-run clips loaded: a ready dual sprint shows them
    bool bDualHatchet=false;      // both hands hold hatchets (the dual sprints' own variants apply)
    // Which hand of the pair holds a hatchet (RefreshOffhand): each hand plays its own weapon's variants (HatchetPairRhythm.h).
    bool bMainHatchet=false, bOffhandHatchet=false;
    // This double thrust's chopping hands (fixed at the swing start): both = HatchetDualAttack3, one = a hatchet + kukri pair.
    bool bChopRight=false, bChopLeft=false;
    uint8 RiftChopSides=0;        // the rift ribbon built for these chopping hands (1 right, 2 left)
    // Sprint-ready run set (HatchetReadyRhythm.h): 0 none, 1 enter, 2 loop, 3 exit.
    int32 ReadyRunPhase=0;
    bool bDualChop=false;       // this double thrust is two hatchets: it plays HatchetDualAttack3 (fixed at the swing start)
    // Right kukri turned in the fist (rad about its grip Y): 0 = forward grip, pi = the dual run's reverse grip.
    float DualTwirlAngle=0.f, DualTwirlFrom=0.f, DualTwirlProgress=1.f;
    bool bDualTwirlIn=false;
    // Dual sweep: stages 1-2 play the two-blade clips; from KukriRhythm::DualSweepOffset(Stage) the left blade swings
    // (mirrored cues).
    bool bDualSweep=false, bOffhandSwing=false;
    // Dual thrust (stage 3 with two kukris, KukriRhythm::DualThrust*): both blades drive together; the left one keeps its
    // own contact set and traced frame; the stride rides the shared melee-lunge movement (Thrust).
    bool bDualThrust=false, bDualThrustLungeStarted=false, bDualThrustLungeBlocked=false;
    FVector DualThrustDirection=FVector::ZeroVector;
    TSet<TWeakObjectPtr<AActor>> OffhandHitActors;
    FTransform PreviousOffhandBlade;
    FName CurrentClip;
    float Elapsed=0.f;          // author seconds on the current clip
    bool bAttacking=false, bEquipping=false, bQueued=false;
    bool bPendingOffhandDraw=false;
    bool bSwingPlayed=false, bImpactConfirmed=false, bWallHit=false;
    bool bTossPlayed=false, bCatchPlayed=false;
    bool bOffhandTossPlayed=false, bOffhandCatchPlayed=false;   // dual draw: the left hand's toss / catch cues
    bool bOffhandDrawPose=false;                                // OffhandBlade carries the dual draw's flight table
    float PlayRate=1.f;         // frozen per swing
    int32 Stage=0;              // 0 = right->left sweep, 1 = upper-left->lower-right diagonal, 2 = one-handed stab
    int32 NextStage=0;          // stage a click continues with shortly after a swing (KukriRhythm::ComboResetSeconds)
    double LastAttackEnd=-1.;   // world seconds the last swing returned to the stance (-1 = none)
    FRotator CameraCarry=FRotator::ZeroRotator;   // previous stage's camera offset blended out on a chain
    float CameraCarryFov=0.f, CameraCarryAge=-1.f;
    float SwingDamage=0.f, Reach=150.f;
    float OffhandSwingDamage=0.f,OffhandReach=150.f,OffhandPlayRate=1.f;
    float HitStop=0.f, ImpactAge=-1.f, ImpactKick=0.f;
    FColdSteelSkillShot Shot;
    FColdSteelSkillShot OffhandShot;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    FTransform PreviousBlade;
    bool bHavePreviousBlade=false;
    // Impact moment: cues of contacts found before it wait for the blade (damage is not deferred).
    struct FKukriPendingFX{FHitResult Hit;bool bWorld=false;};
    bool bStrikeDone=false, bPendingFlesh=false, bPendingWall=false, bPressIn=false;
    FHitResult PendingFleshHit, PendingWallHit;
    TArray<FKukriPendingFX> PendingFX;
    float StrikeAge=-1.f, PressStop=0.f;
    // Swing rift: frozen in world space where the viewmodel was at the window start.
    FTransform RiftOrigin;
    FVector RiftDirection=FVector::ForwardVector;
    float RiftAge=0.f, RiftFadeAge=-1.f;
    int32 RiftStage=INDEX_NONE;          // stage whose ribbon is in RiftVisual
    int8 RiftFalconPhase=-1;
    bool bRiftMirrored=false;            // RiftVisual holds the ribbon mirrored left-right (the dual sweep's left blade)
    bool bRiftDual=false;                // RiftVisual holds the dual heavy's two crossing crescents (KukriRhythm::DualHeavyRift)
    bool bRiftChop=false;                // RiftVisual holds the hatchet chop's crescent (HatchetChopRhythm::Ribbon)
    float RiftTimeOffset=0.f;            // author seconds the revealing ribbon's window is shifted by (left blade: DualSweepOffset(Stage))
    // Uppercut (stage KukriRhythm::UppercutStage): martial clock, paid at the release, trained once per cast.
    bool bUppercut=false, bUppercutReleased=false, bUppercutTrainingPending=false, bUppercutLungeStarted=false, bUppercutLungeBlocked=false;
    FVector UppercutDirection=FVector::ZeroVector;
    // Heavy strike (stage KukriRhythm::HeavyStage): charge on the left button, the release on the martial clock.
    bool bHeavyCharging=false, bHeavyAttack=false, bHeavyAuto=false, bHeavyFull=false, bHeavyTrainingPending=false;
    // Dual heavy (both kukris, KukriHeavyRhythm::DualCharge* / KukriRhythm::DualHeavy*): fixed at the charge start; the release
    // traces both blades in one window (the left with OffhandHitActors / PreviousOffhandBlade, as the dual thrust).
    bool bDualHeavy=false;
    bool bFalconHeavy=false;
    float FalconReleaseRate=1.f;
    TSet<TWeakObjectPtr<AActor>> HeavyTrainedTargets;
    FString HeavyOffhandWeapon;
    bool DualHeavyReady() const;
    int32 HeavyHits=0, HeavyKills=0;      // unique mastery-training victims of the release (TrainHeavyStrike tiers)
    double HeavyChargeStartedAt=0.;
    float HeavyRequiredSeconds=2.f, HeavyMultiplier=1.f;
    // Server side of a remote owner's charge (the stamina bill and the release receipt; the server has no viewmodel).
    bool bServerHeavyCharging=false;
    uint32 NetworkHeavyReleaseSerial=0;
    TSet<TWeakObjectPtr<AActor>> NetworkHeavyTargets[2][2]; // [phase][hand]
    bool bServerFalconRelease=false;
    double ServerFalconReleasedAt=-1.;
    float ServerFalconRate=1.f;
    FString ServerHeavyWeapon,ServerHeavyOffhandWeapon;
    double ServerHeavyStartedAt=-1., ServerHeavyRequired=2., NetworkHeavyReleaseUntil=-1.;
    double ServerHeavyReceivedAt=-1., ServerHeavyLastStartedAt=-1.;
    bool bRiftActive=false, bRiftStarted=false;
    // Sprint attack: frozen at release (damage/range/arc/knockback from DashAttackStats), training counted per cast.
    bool bDashAttack=false, bDashTrainingPending=false;
    bool bDualDash=false;   // this sprint attack is the pair's two-handed chop down (KukriDualDashRhythm.h, fixed at its start)
    float DashSprintSeconds=0.f, DashRangeCM=0.f, DashArcDegrees=60.f, DashKnockbackCM=0.f;
    int32 DashHits=0, DashKills=0;
    FVector DashDirection=FVector::ZeroVector;
    // Quick melee: skill stats frozen at the cast (QuickCombatStats); one contact query; kill experience at the end.
    bool bQuickCombat=false, bQuickContactDone=false, bQuickKillPending=false;
    FQuickCombatCast QuickCast;
    // Whirlwind: stats and tuning frozen at the cast; one hit per target; the hit-stop pauses turn, sweep, pose and camera.
    bool bWhirlwind=false, bWhirlwindTrainingPending=false, bWhirlwindSwingPlayed=false, bWhirlwindFocusActive=false;
    bool bStaffOffhandWhirlwind=false;
    FWhirlwindCast WhirlwindCast;
    FWhirlwindTuning WhirlwindTuning;
    float WhirlwindYaw=0.f, WhirlwindPause=0.f, WhirlwindPauseSpent=0.f, WhirlwindReaction=1.f;
    float WhirlwindImpactAge=1.f, WhirlwindImpactStrength=1.f;
    int32 WhirlwindHits=0, WhirlwindKills=0;
    float WhirlwindSavedBlur=0.f;
    bool bWhirlwindSavedBlurOverride=false;
    struct FKukriWhirlwindDepth{TWeakObjectPtr<UPrimitiveComponent> Part;bool bEnabled=false;int32 Stencil=0;uint8 WriteMask=0;};
    TArray<FKukriWhirlwindDepth> WhirlwindDepth;
    // Skill rift: frozen in world space at its start (the dash crescent rides with the dash while it unfolds).
    EKukriSkillRift SkillRift=EKukriSkillRift::None, SkillRiftMesh=EKukriSkillRift::None;
    bool bSkillRiftMirrored=false;    // the built dash crescent is the lone off-hand blade's mirror image
    bool bSkillRiftDual=false;        // ...or the pair's two crescents (KukriDualDashRhythm)
    FTransform SkillRiftOrigin;
    FVector SkillRiftDirection=FVector::ZeroVector, SkillRiftPawnLocation=FVector::ZeroVector;
    float SkillRiftAge=0.f, SkillRiftFadeAge=-1.f;
    // ShadowStepSlash (瞬步掠影斩): Stage 1 pass-through dash + 30° slash, Stage 2 zero-displacement backhand follow-up.
    bool bShadowStep=false, bShadowStepStage2=false, bDualShadowStep=false;
    bool bShadowStepTrainingPending=false, bShadowStepDashStarted=false, bShadowStepDashBlocked=false, bShadowStepDashDepenetrated=false;
    bool bShadowStepFollowupUnlocked=false, bShadowStepFollowupUsed=false;
    bool bShadowStepDashWhooshPlayed=false, bShadowStepRightSwingPlayed=false, bShadowStepLeftSwingPlayed=false;
    bool bShadowStepRiftStarted=false;
    bool bShadowStepStrikeDone=false, bShadowStepPendingFlesh=false, bShadowStepPendingWall=false, bShadowStepHeavyImpact=false;
    FHitResult ShadowStepPendingFleshHit, ShadowStepPendingWallHit;
    TArray<FKukriPendingFX> ShadowStepPendingFX;
    float ShadowStepPressStop=0.f;
    uint32 ShadowStepSerial=0;
    int32 ShadowStepKills=0;
    float ShadowStepFollowupTimer=0.f;
    float ShadowStepStage1Damage=0.f, ShadowStepStage2Damage=0.f;
    float OffhandShadowStepStage1Damage=0.f, OffhandShadowStepStage2Damage=0.f;
    FShadowStepCast ShadowStepCast;
    FVector ShadowStepDirection=FVector::ZeroVector;
    FVector ShadowStepDashStartLocation=FVector::ZeroVector;
};
