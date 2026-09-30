#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Dom/JsonObject.h"
#include "WeaponHandling.h"
#include "GunsmithSystem.generated.h"

struct FColdSteelItem;
using FGunsmithParts = TMap<FString,FString>;
struct FMeleeModifiers
{
    double Damage=1, AttackSpeed=1, Range=1, Stamina=1, BlockStamina=1, HitReaction=1, BlockReduction=1;
    // Poise damage is separate from the duration of a successful poise break.
    double ToughnessDamage=1, PhysicalArmorPenetration=0;
    double ComboSecond=1, ComboThird=1;
    double MagicCooldown=1, MagicDamage=1, MagicCost=1, RuneIntelligence=0, RuneWisdom=0;
    double InnateErosionMultiplier=1;
    // Flat additions affect the action multiplier, not the panel damage.
    // Knockback distance is independent of hit-reaction duration.
    double HeavyDamage=1, HeavyDamageAdd=0, Knockback=1;
    double QuickCombatDamageAdd=0, QuickCombatKnockback=1;
    // 每次近战出手按武器冷却口径缩减全部魔法技能CD（金色符文强化：0.5s→1.0s）。
    double CooldownReduceSecondsPerHit=0;
    // RuneVulnerability*=剑刃攻击通道（普攻/连段/重击/旋风/冲刺及未来的剑刃攻击）；
    // QuickCombatRuneVulnerability*=配重锤快速近战专属通道，两种改造件触发条件不同。
    double QuickCombatRuneVulnerability=0, QuickCombatRuneVulnerabilitySeconds=0;
    double HeavyMultiplier(double Base) const {return Base*HeavyDamage+HeavyDamageAdd;}
    double RuneVulnerability=0, RuneVulnerabilitySeconds=0;
    double ParryWindow=1, RiposteSpeed=1, RiposteStamina=1, RiposteSeconds=0;
    double ClovenSeconds=0, ClovenPhysical=1, ClovenToughness=1;
    double ComboMultiplier(int32 Stage) const {return Stage==2?ComboSecond:Stage==3?ComboThird:1.;}
    // Applied only to the third-stage thrust snapshot, on top of all-attack poise modifiers.
    double ComboThirdToughness=1;
    double ThirdThrustToughnessMultiplier() const {return ToughnessDamage*ComboThirdToughness;}
    // Pommel-strike modifiers never affect blade attacks or their skill snapshots.
    double QuickCombatToughness=1, QuickCombatBleedChance=0;
    bool bQuickCombatAOE=false;
    double QuickCombatToughnessMultiplier() const {return ToughnessDamage*QuickCombatToughness;}
    // Heavy releases only, including a guard-converted heavy attack.
    double HeavyToughness=1;
    double HeavyToughnessMultiplier() const {return ToughnessDamage*HeavyToughness;}
};
/**
 * 采集工具（伐木斧、矿镐）改造倍率：倍率相乘、绝对值相加，1／0 = 未改造。
 * 口径唯一权威是 `Content/ColdSteelData/tool-gunsmith.json` 与 `GunsmithSystem.cpp::Calculate`；
 * 采集与自卫两条链路都读同一份结果（见 `Production/ProductionToolStats.h`）。
 * HarvestHitsAdd 为负表示更快采尽；应用端把所需命中夹在 ≥1。
 */
struct FToolModifiers
{
    double Damage=1, AttackSpeed=1, Stamina=1, CombatReach=1, ToughnessDamage=1;
    double HarvestYield=1, HarvestReach=1;
    double HarvestRadiusAddCM=0, BonusHarvestChance=0, CriticalChanceAdd=0;
    int32 HarvestHitsAdd=0;
};
struct FGunsmithStats
{
    // Bow factors are independent from firearm handling and magazine rules.
    struct FBowModifiers { double Damage=1,Draw=1,Speed=1,Stamina=1,Nock=1,Hold=1,Sway=1,Spread=1,ADS=1; } Bow;
    FMeleeModifiers Melee;
    FToolModifiers Tool;
    FWeaponHandling Handling;
    double ADS=0.3, ADSPercent=0, ADSSeconds=0, Recoil=100, Shake=100, RecoilMultiplier=1, ShakeMultiplier=1, StabilityMultiplier=1;
    double Interval=0.13, Reload=1.5, EmptyReload=1.5, Speed=90, Range=40, Spread=1, Damage=25;
    int32 Capacity=30, ActiveParts=0;
    int32 BurstCount=1;
    double BurstDelay=0; // Last shot to next permitted trigger, seconds.
    double BurstCycle(double ShotInterval) const {return (BurstCount-1)*ShotInterval+FMath::Max(ShotInterval,BurstDelay);}
};
struct FGunsmithOption
{
    FGunsmithStats::FBowModifiers Bow;
    TSharedPtr<FJsonObject> BowVisual;
    FMeleeModifiers Melee;
    FToolModifiers Tool;
    TArray<FString> CompatibleWeapons;
    FString Id, Name, Description;
    /** 数值改造先行时如实说明当前外观归属；空串表示沿用本槽 factory 外形。 */
    FString Appearance;
    TArray<TPair<FString,int32>> Effects;
    // EmptyReload defaults to Reload, so an option only needs the extra catalog
    // key (empty_reload_mult) when normal and empty reload must differ.
    double ADS=0, ADSSeconds=0, Recoil=1, Shake=1, Stability=1, Speed=1, Interval=1, Spread=1, Range=1, Reload=1, EmptyReload=1;
    int32 Magazine=0;
};
/**
 * 武器特殊性质：工具提示「特殊性质」段的一行。
 * Icon 决定这一行的颜色（见 ColdSteelItemTooltipLayout 的 TraitColor），
 * 所以新增武器只要在目录里写 traits，不必改 UI 代码。
 * 取值：special（特殊攻击）/ magic（魔法）/ mechanic（机制）/ drawback（代价）/ neutral。
 * 数据直接从目录的 FGunsmithWeapon::Source 读，不额外缓存。
 */
struct FGunsmithTrait
{
    FString Icon, Text;
};
struct FGunsmithWeapon
{
    FString Id, Model, Name, Ammo;
    /** 目录显式声明该枪命中会造成硬直；缺省 false = 枪械默认不硬直。 */
    bool bHitStagger = false;
    TArray<FString> Allowed;
    TMap<FString,TArray<FGunsmithOption>> Options;
    FGunsmithStats Base;
    TSharedPtr<FJsonObject> Source;
};
DECLARE_MULTICAST_DELEGATE(FGunsmithChanged);
/** Draft is transient. Persistent parts belong exclusively to an inventory instance. */
UCLASS()
class FPSGAME_API UGunsmithSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase&) override;
    virtual void Deinitialize() override;
    const FGunsmithWeapon* Weapon(const FString& Definition) const;
    FString CategoryLabel(const FString& Definition,const FString& Slot) const;
    // Weapon remains the firearm contract used by ammunition and combat callers.
    const FGunsmithWeapon* ModifiableWeapon(const FString& Definition) const;
    bool IsMelee(const FString& Definition) const {return MeleeWeapons.Contains(Definition);}
    /** 采集工具（伐木斧、矿镐）：走工具四栏目录，不套用剑类连击／格挡口径。 */
    bool IsTool(const FString& Definition) const {return ToolWeapons.Contains(Definition);}
    bool IsStaff(const FString& Definition) const {return StaffWeapons.Contains(Definition);}
    bool IsBow(const FString& Definition) const {return BowWeapons.Contains(Definition);}
    /** Resolve a transient visual recipe; draft parts never mutate the equipped item. */
    FColdSteelItem ResolveBowVisual(const FColdSteelItem& Item,const FGunsmithParts* Parts=nullptr) const;
    const FGunsmithOption* Option(const FString& Definition,const FString& Slot,const FString& Id) const;
    FGunsmithParts Installed(const FColdSteelItem&) const;
    FGunsmithParts Normalize(const FString& Definition,const FGunsmithParts&) const;
    FGunsmithStats Calculate(const FString& Definition,const FGunsmithParts&) const;
    FGunsmithStats CalculateItem(const FColdSteelItem& Item,const FGunsmithParts&) const;
    bool Begin(const FString& Instance);
    bool Select(const FString& Slot,const FString& OptionId);
    bool Apply();
    bool CanApply(FString& Reason) const;
    FString ApplyFeedback() const;
    void Undo();
    void Close();
    /**
     * 工具强化草稿等级（阶段 1-C）：0＝无草稿，非 0＝「应用」时要写进物品 Data 的 `tool_enhance_level`。
     * 这是**瞬时草稿**，与 `Preview` 同寿命：不写进 `gunsmith_parts`，不进 `NormalizeProductionState`
     * 的刷新白名单，`Undo`／`Close` 一律丢弃。规则为逐级 +1：只接受 `Current+1`，其余拒绝。
     */
    bool SetDraftEnhanceLevel(int32 Level);
    int32 DraftEnhanceLevel() const {return DraftEnhanceLevelValue;}
    /** 当前实例的出厂／已安装等级；不在工具工作台时返回 0。 */
    int32 CurrentEnhanceLevel() const;
    /** 逐级 +1 检查：OutNextLevel＝当前+1；已满级或无当前实例时为 false。 */
    bool CanEnhanceNow(int32& OutNextLevel) const;
    int32 Pending() const;
    bool IsOpen() const {return bOpen;}
    const FString& Instance() const {return InstanceId;}
    const FString& Definition() const {return DefinitionId;}
    const FGunsmithParts& Draft() const {return Preview;}
    const FString& Message()const{return Status;}
    const TArray<FString>& Slots() const{return SlotKeys;}
    const TArray<FString>& Categories()const{return CategoryNames;}
    const TArray<FString>& Defaults()const{return DefaultNames;}
    const TArray<FString>& Slots(const FString& Definition) const {return IsStaff(Definition)?StaffSlotKeys:IsBow(Definition)?BowSlotKeys:IsTool(Definition)?ToolSlotKeys:IsMelee(Definition)?MeleeSlotKeys:SlotKeys;}
    const TArray<FString>& Categories(const FString& Definition) const {return IsStaff(Definition)?StaffCategoryNames:IsBow(Definition)?BowCategoryNames:IsTool(Definition)?ToolCategoryNames:IsMelee(Definition)?MeleeCategoryNames:CategoryNames;}
    const TArray<FString>& Defaults(const FString& Definition) const {return IsStaff(Definition)?StaffDefaultNames:IsBow(Definition)?BowDefaultNames:IsTool(Definition)?ToolDefaultNames:IsMelee(Definition)?MeleeDefaultNames:DefaultNames;}
    FGunsmithChanged OnChanged;
    TSharedPtr<FJsonObject> Catalog;
private:
    TMap<FString,FGunsmithWeapon> Weapons;
    TMap<FString,FGunsmithWeapon> MeleeWeapons;
    // 采集工具独立成表：四栏目录、数值口径与剑类不同，避免 IsMelee 的剑类分支误覆盖工具。
    TMap<FString,FGunsmithWeapon> ToolWeapons;
    TMap<FString,FGunsmithWeapon> BowWeapons;
    TArray<FString> BowSlotKeys,BowCategoryNames,BowDefaultNames;
    void LoadBowCatalog();
    void LoadStaffCatalog();
    TMap<FString,FGunsmithWeapon> StaffWeapons;
    TArray<FString> StaffSlotKeys,StaffCategoryNames,StaffDefaultNames;
    TArray<FString> MeleeSlotKeys,MeleeCategoryNames,MeleeDefaultNames;
    void LoadMeleeCatalog();
    TArray<FString> ToolSlotKeys,ToolCategoryNames,ToolDefaultNames;
    void LoadToolCatalog();
    TArray<FString> SlotKeys,CategoryNames,DefaultNames;
    FGunsmithParts Preview, Original;
    int32 DraftEnhanceLevelValue=0;
    FString InstanceId, DefinitionId, Status;
    bool bOpen=false;
};
