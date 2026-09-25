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
class UColdSteelPickupPrompt;
class UColdSteelStatusModel;
class USceneComponent;
class USkeletalMeshComponent;
class USoundBase;
class UStaticMesh;
class UStaticMeshComponent;
struct FColdSteelItem;
struct FStreamableHandle;

/** 弓的一条时钟上的环节：搭箭 → 拉开 → 保持 → 放弦 → 回收。 */
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

    /** 左键按下：弦上无箭先搭箭，已搭箭开始拉弓；箭支只在成功发射时扣除。 */
    void BeginPrimaryAttack();
    /** 从箭袋取箭上弦（R 键／自动搭箭共用）；弦上已有箭时什么都不做。 */
    void BeginNock();
    /** 左键松开或满拉力竭：按当前拉距结算并发射；中断另走 CancelAction。 */
    void ReleasePrimaryAttack();
    /** 右键按住：稳持（呼吸幅度下降），与枪械机瞄共用"稳定"语义。 */
    void SetSteadyHeld(bool bHeld) { bSteadyHeld = bHeld; }
    /** 左键按住状态：决定"搭箭"完成后是否顺势续上拉弓（与剑的蓄力释放同一口径）。 */
    void SetTriggerHeld(bool bHeld) { bTriggerHeld = bHeld; }
    /** 切枪／翻越／施法等更高优先级打断：收弓，不结算发射。 */
    void CancelAction();
    /** 弓与镜头读同一 age：角色在自己的相机合成之前推进这只时钟。 */
    void AdvanceActionBeforeCamera(float Delta);
    /** 相机局部位移（cm）与旋转（度），由角色叠加到既有镜头反馈上。 */
    void GetCameraMotion(FVector& Location, FRotator& Rotation) const;

    FString Definition() const { return EquippedDefinition; }
    FString ArrowDefinition() const { return ArrowId; }

    /**
     * 部件表查询。弓体（riser）、弓弦（string）、弦上箭（arrow_rest）是三个独立部件，
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
    /** 每个部件的程序化细杆句柄：string 两条（上／下弓梢到弦结点），arrow_rest 一条。 */
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
    float FullDamage = 46.f, MinDamageRatio = .25f, FullSpeedCM = 9800.f, MinSpeedRatio = .35f,
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
         bDrawSoundPlayed = false, bHasRightHandBone = false;

    static const TCHAR* ClipIdle;
    static const TCHAR* ClipDraw;
    static const TCHAR* ClipHold;
    static const TCHAR* ClipRelease;
    static const TCHAR* ClipNock;

    bool CanUse() const;
    void SetStage(EBowStage Next, float Seconds);
    void ApplyNumbers(const FColdSteelItem* Item);
    /** 按 `bow_part_slots` 建／补部件，并读每件的 `_rods`／`_radius_cm`；资源路径见 `CollectPartAssets`。 */
    void ApplyParts(const FColdSteelItem* Item);
    /** 部件资源键：`bow_part_<槽名>_mesh` / `_material`，回落旧平铺键（`bow_mesh`、`arrow_mesh`…）。 */
    static FString PartKey(FName Slot, const TCHAR* Suffix);
    /** 把各槽要加载的资产路径收进一次异步加载；同时算出"表现签名"用于判断是否需要重载。 */
    FString PresentationSignature(const FColdSteelItem* Item) const;
    void CollectPartAssets(const FColdSteelItem* Item);
    bool ConsumeArrowFromPouch(FString& Reason);
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
    static const TCHAR* SlotArrowRest;

    /** 当前正在采样手臂的片段名；换片段时才重新起播。 */
    FName CurrentClip;
    bool bPresentationReady = false, bHasGripMarker = false, bHasNockMarker = false;
    bool bNockSoundPlayed = false;
    float EquipSeconds = .45f, NockContactFraction = .82f;
    float ReleaseRatio = 0.f;
    FVector ReleasedNockCM = FVector::ZeroVector;
    TArray<float> DrawCurve;
    void SampleArms();
    float ClipLength(const TCHAR* Name) const;
};
