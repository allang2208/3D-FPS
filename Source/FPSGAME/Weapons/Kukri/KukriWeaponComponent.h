#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "../../Skills/WhirlwindTypes.h"
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

/** Which skill rift (KukriSkillRift.cpp) is showing / built in the skill rift mesh. */
enum class EKukriSkillRift : uint8 { None, Dash, Whirlwind };

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
    void RefreshEquipment(UColdSteelStatusModel* Profile);
    UFUNCTION(BlueprintPure, Category="Kukri") bool IsEquipped() const { return !InstanceId.IsEmpty(); }
    UFUNCTION(BlueprintPure, Category="Kukri") bool IsBusy() const { return bAttacking||bEquipping||bDashAttack||bQuickCombat||bUppercut||bHeavyCharging||bHeavyAttack||bWhirlwind; }
    bool IsEquipping() const { return bEquipping; }
    bool IsAttacking() const { return bAttacking; }
    void BeginPrimaryAttack();
    void CancelAction();
    UKukriArmsMeshComponent* ArmsMesh() const { return Viewmodel; }
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
    bool IsHeavyAttackActive() const { return bHeavyAttack; }
    /** Server receipt for heavy hit reports (ColdSteelPlayerState hit validation), as URuneSwordComponent's. */
    bool IsNetworkHeavyReleaseWindowOpen(const FString& Weapon) const;
    bool ConsumeNetworkHeavyChargeForRelease(const FString& Weapon);
    /** 大旋风（主动技能 whirlwind，KukriWhirlwind.cpp）：单手持刀两圈旋转横扫，快捷栏释放；空字符串 = 可释放。 */
    FString WhirlwindStatusText() const;
    bool BeginWhirlwind();
    bool IsWhirlwindActive() const { return bWhirlwind; }
private:
    void TickWhirlwind(float Delta);
    void SweepWhirlwind(float FromDegrees,float ToDegrees);
    void FinishWhirlwind();
    void FinishWhirlwindTraining();
    void GetWhirlwindCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    void BeginWhirlwindFocus();
    void UpdateWhirlwindFocus(float Strength);
    void EndWhirlwindFocus();
    /** Skill rifts (KukriSkillRift.cpp): the combo's space distortion on the sprint attack's chop and the whirlwind's ring. */
    bool PrepareSkillRift();
    void StartDashRift();
    void StartWhirlwindRift();
    void TickSkillRift(float Delta);
    void StopSkillRift();
    bool CanBeginHeavyCharge() const;
    void BeginHeavyCharge();
    void SetHeavyCharging(bool bCharging,bool bRelease);
    void CancelHeavyCharge(bool bNotifyServer);
    void ReleaseHeavyCharge();
    void AdvanceHeavyCharge(float Delta);
    void AdvanceHeavy(float Delta);
    void FinishHeavy(bool bTrain);
    void TickServerHeavyCharge();
    bool PayServerHeavyRelease();
    /** Normal left click (the combo), from a press or from a tap / short charge release. */
    void StartComboClick();
    UFUNCTION(Server,Reliable) void ServerSetKukriHeavyCharge(const FString& Weapon,bool bCharging,bool bRelease);
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
    void ConfirmDashImpact(const FHitResult& Hit);
    void FinishDashAttack();
    void GetDashCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
    FRotator DashViewmodelKick() const;
    /** 视模呈现父节点的命中冲击（不改相机）。 */
    FRotator ViewmodelKick() const;
    AFPSGAMECharacter* Pawn() const;
    bool CanPresent() const;
    bool CanUse() const;
    void InitializePresentation();
    void SetClip(FName Name,bool bLoop,float Blend);
    void SamplePose(float Time);
    void StartAttack(int32 NewStage);
    void AdvanceAttack(float Delta);
    void TraceBlade(const FTransform& From,const FTransform& To);
    void ConfirmImpact(const FHitResult& Hit,bool bWorld);
    /** Impact moment (KukriStrike.cpp, KukriRhythm::Strikes): camera accent + miss stop, deferred hit cues, contact FX. */
    void ArriveStrike();
    void QueueContactFX(const FHitResult& Hit,bool bWorld);
    void SpawnContactFX(const FHitResult& Hit,bool bWorld) const;
    FVector StrikeViewmodelOffset() const;
    void ResetStrike();
    /** Swing rift / sword qi (KukriRift.cpp, KukriRhythm::Rifts): the rune sword's M_RuneRift crescent on every swing. */
    void StartRift();
    void TickRift(float Delta);
    void StopRift();
    FName LocomotionClip() const;
    FTransform BladeFrame() const;

    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> JumpRoot;
    UPROPERTY(Transient) TObjectPtr<UKukriArmsMeshComponent> Viewmodel;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Blade;
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
    FName CurrentClip;
    float Elapsed=0.f;          // author seconds on the current clip
    bool bAttacking=false, bEquipping=false, bQueued=false;
    bool bSwingPlayed=false, bImpactConfirmed=false, bWallHit=false;
    bool bTossPlayed=false, bCatchPlayed=false;
    float PlayRate=1.f;         // frozen per swing
    int32 Stage=0;              // 0 = right->left sweep, 1 = upper-left->lower-right diagonal, 2 = one-handed stab
    int32 NextStage=0;          // stage a click continues with shortly after a swing (KukriRhythm::ComboResetSeconds)
    double LastAttackEnd=-1.;   // world seconds the last swing returned to the stance (-1 = none)
    FRotator CameraCarry=FRotator::ZeroRotator;   // previous stage's camera offset blended out on a chain
    float CameraCarryFov=0.f, CameraCarryAge=-1.f;
    float SwingDamage=0.f, Reach=150.f;
    float HitStop=0.f, ImpactAge=-1.f, ImpactKick=0.f;
    FColdSteelSkillShot Shot;
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
    // Uppercut (stage KukriRhythm::UppercutStage): martial clock, paid at the release, trained once per cast.
    bool bUppercut=false, bUppercutReleased=false, bUppercutTrainingPending=false, bUppercutLungeStarted=false, bUppercutLungeBlocked=false;
    FVector UppercutDirection=FVector::ZeroVector;
    // Heavy strike (stage KukriRhythm::HeavyStage): charge on the left button, the release on the martial clock.
    bool bHeavyCharging=false, bHeavyAttack=false, bHeavyAuto=false, bHeavyFull=false, bHeavyTrainingPending=false;
    int32 HeavyHits=0, HeavyKills=0;      // unique mastery-training victims of the release (TrainHeavyStrike tiers)
    double HeavyChargeStartedAt=0.;
    float HeavyRequiredSeconds=2.f, HeavyMultiplier=1.f;
    // Server side of a remote owner's charge (the stamina bill and the release receipt; the server has no viewmodel).
    bool bServerHeavyCharging=false;
    FString ServerHeavyWeapon;
    double ServerHeavyStartedAt=-1., ServerHeavyRequired=2., NetworkHeavyReleaseUntil=-1.;
    bool bRiftActive=false, bRiftStarted=false;
    // Sprint attack: frozen at release (damage/range/arc/knockback from DashAttackStats), training counted per cast.
    bool bDashAttack=false, bDashTrainingPending=false;
    float DashSprintSeconds=0.f, DashRangeCM=0.f, DashArcDegrees=60.f, DashKnockbackCM=0.f;
    int32 DashHits=0, DashKills=0;
    FVector DashDirection=FVector::ZeroVector;
    // Quick melee: skill stats frozen at the cast (QuickCombatStats); one contact query; kill experience at the end.
    bool bQuickCombat=false, bQuickContactDone=false, bQuickKillPending=false;
    FQuickCombatCast QuickCast;
    // Whirlwind: stats and tuning frozen at the cast; one hit per target; the hit-stop pauses turn, sweep, pose and camera.
    bool bWhirlwind=false, bWhirlwindTrainingPending=false, bWhirlwindSwingPlayed=false, bWhirlwindFocusActive=false;
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
    FTransform SkillRiftOrigin;
    FVector SkillRiftDirection=FVector::ZeroVector, SkillRiftPawnLocation=FVector::ZeroVector;
    float SkillRiftAge=0.f, SkillRiftFadeAge=-1.f;
};
