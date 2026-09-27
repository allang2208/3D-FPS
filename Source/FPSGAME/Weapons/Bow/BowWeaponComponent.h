// 第一人称弓：库存持有实例与存档，本组件只管"手上的弓"——视模、拉距、弓弦、箭与释放。
// 结构与 `UProductionToolComponent`（双手采集工具）同族：相机空间挂点、单一动作时钟、
// 物品 Data 驱动资源路径；不引入 AnimBP／蒙太奇资产，动画序列按角色名单节点播放。
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "BowWeaponComponent.generated.h"

class ABowArrow;
class UBowArmsMeshComponent;
class AFPSGAMECharacter;
class UBowPartComponent;
class UCameraComponent;
class UAnimSequence;
class UAudioComponent;
class UColdSteelPickupPrompt;
class UColdSteelStatusModel;
class USceneComponent;
class USkeletalMeshComponent;
class USoundBase;
class UStaticMesh;
class UStaticMeshComponent;
struct FColdSteelItem;
struct FStreamableHandle;

/** 弓的一条时钟上的环节：到达拉弓首帧 → 拉开 → 保持 → 放弦 → 回收；R 可单独搭箭。 */
UENUM()
enum class EBowStage : uint8
{
    Stowed,
    Equip,
    Ready,
    Nocking,
    Drawing,
    Holding,
    Release,
    Recover,
    DrawEntry,
    LetDown,
};

/**
 * 弓武器组件：数值、节奏和资源由 bows.json 驱动；单一动作时钟采样 Bow 原生骨架的八段动画。
 * Sparrow 的手／肘轨迹经 V7 裸臂比例适配，弓挂 bow_grip、弦挂 bow_nock 接触标记。
 * 当前弓体保留作者握把原点、长轴 Z、弦在 -X 侧、箭沿 +X；独立弓体资产已分离烘焙弦。
 * 先采样手臂再更新弓／弦／箭，释放后弦回弹与右手随动分离。
 * 详见 Docs/Weapons/dark-bow-actions-v2-20260925.md；未进行运行与视觉验收。
 */
UCLASS(ClassGroup=(Weapons), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UBowWeaponComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UBowWeaponComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;

    /** 库存是唯一事实源：换弓、改改造、收起都从这里刷新。 */
    void RefreshEquipment(UColdSteelStatusModel* Profile);
    void ShowFeedback(const FString& Message);

    UFUNCTION(BlueprintPure, Category="Bow") bool IsEquipped() const { return !InstanceId.IsEmpty(); }
    UFUNCTION(BlueprintPure, Category="Bow") bool IsBusy() const { return Stage != EBowStage::Ready; }
    UFUNCTION(BlueprintPure, Category="Bow") bool IsDrawing() const
    { return Stage == EBowStage::Drawing || Stage == EBowStage::Holding; }
    UFUNCTION(BlueprintPure, Category="Bow") bool HasArrowNocked() const { return bArrowNocked; }
    /** 0 = 未拉，1 = 拉满。伤害、速度、镜头后座只看这一个数。 */
    UFUNCTION(BlueprintPure, Category="Bow") float DrawFraction() const;
    UFUNCTION(BlueprintPure, Category="Bow") EBowStage GetStage() const { return Stage; }
    UFUNCTION(BlueprintPure, Category="Bow") int32 ArrowsInPouch() const;
    FString StatusLine() const;

    /** 左键按下：0.2 秒到达拉弓首帧，再开始拉弓；箭支只在成功发射时扣除。 */
    void BeginPrimaryAttack();
    /** 从箭袋取箭上弦（R 键／自动搭箭共用）；弦上已有箭时什么都不做。 */
    void BeginNock();
    /** Save the selected arrow type, then nock it; spending still happens only at launch. */
    bool SwitchArrow(const FString& Target);
    /** 左键松开：拉距不足 50% 缓收弓；达到门槛按当前拉距结算。满拉力竭仍会发射。 */
    void ReleasePrimaryAttack();
    /** 右键：连续 ADS 对位与轻度变焦，不重启当前拉弓动作。 */
    void SetSteadyHeld(bool bHeld) { bSteadyHeld = bHeld; }
    bool IsAimHeld() const { return IsEquipped() && bSteadyHeld; }
    float AimAlpha() const { return AimProgress; }
    float AimVerticalFOV(float BaseFOV) const;
    float ScopeMagnification() const { return IsEquipped() && bHasAimSight ? OpticalMagnification : 1.f; }
    bool HasOpticalSight() const { return ScopeMagnification() > 1.f; }
    /** Camera-right/up slope, shared by the HUD projection and the release ray. */
    float ShotSpread() const;
    bool ShouldShowCrosshair() const;
    bool HasPhysicalSight() const { return bHasAimSight; }
    /** 左键按住状态：决定"搭箭"完成后是否顺势续上拉弓（与剑的蓄力释放同一口径）。 */
    void SetTriggerHeld(bool bHeld) { bTriggerHeld = bHeld; }
    /** 切枪／翻越／施法等更高优先级打断：收弓，不结算发射。 */
    void CancelAction(bool bImmediate = true);
    /** 弓与镜头读同一 age：角色在自己的相机合成之前推进这只时钟。 */
    void AdvanceActionBeforeCamera(float Delta);
    /** 相机局部位移（cm）与旋转（度），由角色叠加到既有镜头反馈上。 */
    void GetCameraMotion(FVector& Location, FRotator& Rotation) const;

    FString Definition() const { return EquippedDefinition; }
    FString ArrowDefinition() const { return ArrowId; }

    /**
     * 部件表查询。弓体（riser）、弓弦（string）、弦上箭（arrow）是三个独立部件，
     * 各自一个挂点组件；改造系统只写数据键（`bow_part_<槽名>_mesh` 等）再调
     * `RefreshEquipment`，不需要动状态机与弹道。槽名清单来自 `bow_part_slots`。
     */
    UFUNCTION(BlueprintPure, Category="Bow")
    TArray<FName> PartSlots() const;
    UFUNCTION(BlueprintPure, Category="Bow")
    UBowPartComponent* FindPart(FName Slot) const;
    /** 该部件当前用的网格路径（数据表原值，空＝程序化占位）。 */
    UFUNCTION(BlueprintPure, Category="Bow")
    FString PartMeshPath(FName Slot) const;

protected:
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> Pivot;
    /** 弓的部件表：键是槽名，值是该部件的挂点组件（实体网格与细杆都是它的子件）。 */
    UPROPERTY(Transient) TMap<FName, TObjectPtr<UBowPartComponent>> Parts;
    /** 每个部件的程序化细杆句柄：string 两条（上／下弓梢到弦结点），arrow 一条。 */
    TMap<FName, TArray<int32>> PartRods;
    /** V7 裸手 Bow 原生骨架，外观装备使用匹配的 Bow 蒙皮派生。 */
    UPROPERTY(Transient) TObjectPtr<UBowArmsMeshComponent> Viewmodel;
    UPROPERTY(Transient) TMap<FName, TObjectPtr<UAnimSequence>> Animations;
    /** 占位细杆／箭头由各自组件负责（`UBowPartComponent` 用引擎圆柱，`ABowArrow` 用圆柱+圆锥），
     *  这里不再留第二份。 */
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> ArrowHeadMesh;
    UPROPERTY(Transient) TObjectPtr<USoundBase> DrawSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ReleaseSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> NockSound;

private:
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    TSharedPtr<FStreamableHandle> LoadHandle;
    UPROPERTY(Transient) TObjectPtr<UColdSteelPickupPrompt> Prompt;

    FString InstanceId, EquippedDefinition, DisplayName, ArrowId, Feedback;
    /** 资源路径集合的指纹：变了才重新异步加载，只改数值不闪帧。 */
    FString EquippedSignature;
    uint32 EquippedDataHash = 0;
    /** 部件槽顺序（来自 `bow_part_slots`，决定装配与枚举顺序）。 */
    TArray<FName> SlotOrder;
    TMap<FName, FSoftObjectPath> PendingPartMeshes, PendingPartMaterials;
    EBowStage Stage = EBowStage::Stowed;
    float Elapsed = -1.f, StageSeconds = 0.f, HoldElapsed = 0.f, VisualTime = 0.f;
    float FeedbackSeconds = 0.f, HintCountdown = 0.f, ReleaseKick = 0.f;

    // 节奏（秒）：作者值由 bows.json 覆盖，参考轨迹按阶段归一化映射到实际片段时长。
    float NockSeconds = .68f, DrawSeconds = 1.4f, HoldSeconds = 2.2f, ReleaseSeconds = .3f,
          RecoverSeconds = .34f;
    // 数值。`critical_chance` / `toughness_multiplier` 缺省即不覆盖射击瞬间的修炼快照。
    float FullDamage = 69.f, FullSpeedCM = 9800.f, MinSpeedRatio = .35f,
          GravityCM = 520.f, RangeCM = 3200.f, StaminaCost = 3.f, CriticalChance = -1.f,
          ToughnessMultiplier = 0.f;
    // 当前暗纹猎弓的几何回落（cm / 度）；新弓体必须提供自己的锚点，不能由包络猜弦侧。
    float LengthCM = 140.f, DepthCM = 38.2f, BowScale = 1.f;
    float StringRadiusCM = .09f, ArrowRadiusCM = .3f, ArrowLengthCM = 76.f;
    float SwayAmplitudeCM = .9f, SteadySwayScale = .35f;
    FVector UpperTipCM = FVector(-21.46f, -.935f, 64.11f);
    FVector LowerTipCM = FVector(-21.46f, -.935f, -64.04f);
    FVector BraceNockCM = FVector(-21.46f, -.935f, 1.5f);
    FVector DrawAnchorCM = FVector(-52.5f, 8.f, 3.f);
    FVector ArrowRestCM = FVector(0.f, -.935f, 1.5f);
    FVector BowLocationCM = FVector(57.f, -15.f, -13.f);
    FRotator BowRotation = FRotator(0.f, 0.f, 12.f);
    FVector GripTrimCM = FVector::ZeroVector;
    /** Bow 动画已按相机 +X 前、+Y 右、+Z 上导出。 */
    FRotator ArmsRotation = FRotator::ZeroRotator;
    bool bUsesArms = false, bArrowNocked = false, bSteadyHeld = false, bTriggerHeld = false,
         bHasRightHandBone = false;

    static const TCHAR* ClipIdle;
    static const TCHAR* ClipDraw;
    static const TCHAR* ClipHold;
    static const TCHAR* ClipRelease;
    static const TCHAR* ClipNock;

    bool CanUse() const;
    void SetStage(EBowStage Next, float Seconds, float StartSeconds = 0.f);
    void ApplyNumbers(const FColdSteelItem* Item);
    /** 按 `bow_part_slots` 建／补部件，并读每件的 `_rods`／`_radius_cm`；资源路径见 `CollectPartAssets`。 */
    void ApplyParts(const FColdSteelItem* Item);
    /** 部件资源键：`bow_part_<槽名>_mesh` / `_material`，回落旧平铺键（`bow_mesh`、`arrow_mesh`…）。 */
    static FString PartKey(FName Slot, const TCHAR* Suffix);
    /** 把各槽要加载的资产路径收进一次异步加载；同时算出"表现签名"用于判断是否需要重载。 */
    FString PresentationSignature(const FColdSteelItem* Item) const;
    void CollectPartAssets(const FColdSteelItem* Item);
    bool ConsumeArrowFromPouch(FString& Reason, bool& bSpentOwnedArrow);
    bool LooseArrow(float Ratio);
    FVector NockPoint() const;
    FVector ArrowTipPoint() const;
    /** 手动采样手臂片段：Position 是片段内秒数，bLoop 时按秒取模（与采集工具同一口径）。 */
    void PlayClip(const TCHAR* Name, float Position, bool bLoop);
    void UpdateBowGeometry();
    void UpdateHint();

    /** 部件查表（内部用；对外是 `FindPart`）。 */
    UBowPartComponent* Part(FName Slot) const;
    /** 该部件的第 Index 条细杆是否还在；不在就补建（换部件表后不必重建组件）。 */
    int32 RodFor(FName Slot, int32 Index);

    static const TCHAR* SlotRiser;
    static const TCHAR* SlotString;
    static const TCHAR* SlotArrow;

    /** 当前正在采样手臂的片段名；换片段时才重新起播。 */
    FName CurrentClip;
    bool bPresentationReady = false, bHasGripMarker = false, bHasNockMarker = false;
    bool bNockSoundPlayed = false;
    /** Authored nock endpoints match Draw[0], including the loaded ready pose. */
    bool bNockKeepsDrawPose = false;
    float EquipSeconds = .45f, NockContactFraction = .82f;
    float ReleaseRatio = 0.f;
    FVector ReleasedNockCM = FVector::ZeroVector;
    TArray<float> DrawCurve;
    void SampleArms();
    float ClipLength(const TCHAR* Name) const;
    /** 与蓄力分开的入场时钟：目标固定为 Draw 首帧，不提前推进拉距。 */
    float DrawEntrySeconds = .2f;
    void BeginDrawEntry();

    /** Short, separately authored handling and draw voices; owned by this bow. */
    UPROPERTY(Transient) TObjectPtr<USoundBase> TakeArrowSound;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> DrawAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> HandlingAudio;
    float TakeArrowContactFraction = .28f;
    bool bTakeArrowSoundPlayed = false;
    void StopDrawAudio();
    void StopHandlingAudio();
    void PlayHandlingSound(USoundBase* Sound, float Volume, float FitSeconds = 0.f);

    // Reusable pose layers share one pivot for hands, bow, string and arrow.
    // They are independent of the action clock and never restart a clip.
    float AimProgress = 0.f, CrouchProgress = 0.f;
    // Shaped ADS weight shared by pose, camera zoom and spread. Reversals
    // preserve the current velocity through a short bounded braking segment.
    float AimVelocity = 0.f, AimSegmentStart = 0.f, AimSegmentVelocity = 0.f;
    float AimSegmentElapsed = 0.f, AimSegmentDuration = 0.f;
    bool bAimBlendTarget = false, bAimBraking = false;
    void AdvanceAimWeight(float Delta, bool bTarget);
    float AimInSeconds = .18f, AimOutSeconds = .16f, AimFOVScale = .9f;
    float CrouchInSeconds = .18f, CrouchOutSeconds = .22f, CrouchCantDegrees = -55.f;
    FVector AimRestLocationCM = FVector(78.f, 10.f, -12.f);
    FRotator AimBowRotation = FRotator::ZeroRotator;
    FVector CrouchOffsetCM = FVector(-1.5f, -2.f, -.5f);
    void UpdatePoseLayers();
    /** Animated riser in the unlayered pivot space, shared by aim and geometry. */
    FTransform AnimatedRiserMount() const;

    FVector HipOffsetCM = FVector(0.f, 12.f, -6.f);
    float HipSpread = .035f, MoveSpreadMax = .04f, AirSpreadMax = .05f;
    float ShotSpreadStep = .012f, SpreadRecovery = .06f, CrouchSpreadScale = .7f;
    float MoveSpread = 0.f, AirSpread = 0.f, ShotBloom = 0.f;
    float HipAimProgress = 0.f;
    bool bOriginalAudioSpeed = false;
    // Local physical sight pin; optional so other bow recipes retain rest ADS.
    FVector AimSightPointCM = FVector::ZeroVector;
    float AimSightDistanceCM = 78.f;
    bool bHasAimSight = false;
    float FlexDistribution = 1.15f, StringReturnSeconds = .032f, RingSeconds = .17f, FeedbackScale = 1.f;
    float LetDownPhase = 0.f, LetDownRatio = 0.f;
    float ReleasePulse() const;
    float ReleaseRing() const;
    // Entry clips carry the new arrow while the string remains unloaded.
    bool bEntryNeedsArrow = false, bChainEntry = false, bNockHasCarryAxis = false;
    float ReleaseFeedbackAge = -1.f;
    const TCHAR* DrawEntryClip() const;
    // A shared, distance-driven two-step phase; no gameplay timing is delayed.
    float GaitPhase = 0.f, GaitWeight = 0.f, GaitWeightVelocity = 0.f;
    float SprintBlend = 0.f, SprintBlendVelocity = 0.f;
    float TravelSpeed = 0.f, TravelSpeedVelocity = 0.f;
    FVector TravelDirection = FVector::ZeroVector, TravelDirectionVelocity = FVector::ZeroVector;
    FVector CarryOffset = FVector::ZeroVector;
    FRotator CarryRotation = FRotator::ZeroRotator;
    float TurnFollow = 0.f, TurnFollowVelocity = 0.f, PreviousViewYaw = 0.f;
    bool bHaveViewYaw = false;
    void AdvanceLocomotion(float Delta, bool bUsable);
    // Resolved once on equipment changes; ordinary sights always reset to 1x.
    float OpticalMagnification = 1.f;
};
