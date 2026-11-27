#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "ColdSteelQuickBarTypes.h"
#include "ColdSteelItemInstance.h"
#include "../Movement/HorseRosterTypes.h"
#include "../Dungeon/DungeonTypes.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "../Survival/FPSSurvivalTypes.h"
#include "../Building/ColdSteelPlantingTypes.h"
#include "ColdSteelInventoryTypes.generated.h"



/** Catalog row for the F6 development panel: definition id, display name and grouped class. */
USTRUCT(BlueprintType)
struct FColdSteelCatalogEntry
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FString Definition;
    UPROPERTY(BlueprintReadOnly) FString Name;
    /** 归纳后的类别名（武器／弹药／消耗品／材料／建材／强化材料／祭品／货币）。 */
    UPROPERTY(BlueprintReadOnly) FString Group;
    /** 类别排序键：同一类别的条目在下拉列表里连续排列。 */
    UPROPERTY(BlueprintReadOnly) int32 GroupOrder = 0;
    /** 开发目录的子标题，不是可生成的物品，也不写入玩家档案。 */
    UPROPERTY(BlueprintReadOnly) FString Subgroup;
    UPROPERTY(BlueprintReadOnly) int32 SubgroupOrder = 0;
};

USTRUCT()
struct FColdSteelTreeGrowth
{
    GENERATED_BODY()
    UPROPERTY() double CutAtDay = 0;
    UPROPERTY() float DormantDays = 1;
    UPROPERTY() float MatureDays = 6;
    // 2026-09-28 用户规则（只追加，不插到前面：字段错位会读坏未重编的翻译单元/旧档）：
    // 桩与幼树分离——桩留在被砍树的位置等玩家来劈，幼树在附近随机偏移处长回。
    /** 这是该候选点第几次再生（1 起）；偏移随机流的种子之一。 */
    UPROPERTY() int32 Generation = 1;
    /** 幼树相对候选点基点的位置偏移（cm，世界 XY）。默认 0＝旧行为（原地再生）。 */
    UPROPERTY() FVector2D SaplingOffset = FVector2D::ZeroVector;
    /** 当前树桩相对候选点基点的偏移（cm）＝被砍那棵树当时站的位置。 */
    UPROPERTY() FVector2D StumpOffset = FVector2D::ZeroVector;
    /** 树桩剩余生命比例（1＝没劈过）；树桩生命上限口径见 ProductionTreeHealth::StumpMaxHealth。 */
    UPROPERTY() float StumpHealthRatio = 1.f;
    /** 树桩已被劈开（奖励已发，桩不再渲染/不可再砍）；幼树照常生长不受影响。 */
    UPROPERTY() bool bStumpCleared = false;
};

/** Specialization ranks invested in one skill: spec node id -> rank (skill-tree.json "specializations"). */
USTRUCT()
struct FColdSteelSkillSpec
{
    GENERATED_BODY()
    UPROPERTY() TMap<FName,int32> Ranks;
};

USTRUCT()
struct FColdSteelFormulaBuff
{
    GENERATED_BODY()
    UPROPERTY() FName Id;
    UPROPERTY() TMap<FName,float> Effects;
    /** 旧 tribute 的 "special" 块（原样毫秒/百分比存），仅供机制消费，不进属性聚合。 */
    UPROPERTY() TMap<FName,float> Specials;
    UPROPERTY() float RemainingSeconds=0;
    UPROPERTY() FString Rarity;
    UPROPERTY() int32 Battles=0;
    UPROPERTY() bool bTribute=false;
    // Persistent per-offering identity. Legacy offerings use the invalid GUID until replaced.
    UPROPERTY() int32 UsageVersion=1;
    UPROPERTY() FGuid OfferingId;
    UPROPERTY() bool bPeachUsed=false;
    UPROPERTY() bool bMoonshadowUsed=false;
};
/** 冶炼点击已写入角色档、建筑档可能还没落盘时的对账条。Kind：1投料 2收取 3添燃料 4升级 5拆炉 6队列投料 7部分收取。 */
USTRUCT()
struct FColdSteelSmeltIntent
{
    GENERATED_BODY()
    UPROPERTY() FString WorldKey;
    UPROPERTY() int32 X=0,Y=0,Z=0;
    UPROPERTY() int32 Kind=0;
    UPROPERTY() FString Item;
    UPROPERTY() int64 Count=0;
    UPROPERTY() FString Recipe;
    UPROPERTY() int64 Batch=1;
    UPROPERTY() int32 Axis=0;
    UPROPERTY() int32 Level=0;
    UPROPERTY() double FuelBefore=0;
    UPROPERTY() double FuelAfter=0;
};
/** Paid workpiece kept outside the inventory until the player claims or discards it. */
USTRUCT()
struct FColdSteelForgeJob
{
    GENERATED_BODY()
    UPROPERTY() FString Id;
    UPROPERTY() FName Recipe;
    UPROPERTY() FColdSteelItem Item;
    UPROPERTY() int32 Hits=0;
    /** A hammer reached the blank. Accuracy still affects quality independently. */
    UPROPERTY() bool bHammeredBlank=false;
    UPROPERTY() bool bFinished=false;
    /** Latched at creation; free jobs must not use legacy recipe-based refunds. */
    UPROPERTY() bool bMaterialsWaived=false;
    /** Version 0 is an already-paid legacy job; new material-based jobs use version 2. */
    UPROPERTY() int32 QualityVersion=0;
    UPROPERTY() FName Metal;
    UPROPERTY() FString MaterialName;
    UPROPERTY() double MaterialBonus=0.;
    /** Actual inputs paid at start; empty for legacy jobs that use the recipe fallback. */
    UPROPERTY() TMap<FString,int64> PaidMaterials;
};

/** Paid woodworking result, kept outside inventory until claimed or recycled. */
USTRUCT()
struct FColdSteelWoodworkingJob
{
    GENERATED_BODY()
    UPROPERTY() int32 Version=1;
    // Missing tagged fields in older jobs retain their original score curve.
    UPROPERTY() int32 QualityVersion=1;
    UPROPERTY() FName Core;
    UPROPERTY() double MaterialBonus=0;
    UPROPERTY() FString Id;
    UPROPERTY() FName Pattern;
    UPROPERTY() FName Recipe;
    UPROPERTY() FString Name;
    UPROPERTY() FColdSteelItem Item;
    UPROPERTY() TMap<FString,int64> PaidMaterials;
    UPROPERTY() bool bMaterialsWaived=false;
    UPROPERTY() bool bFinished=false;
    UPROPERTY() bool bPassed=false;
    UPROPERTY() double Quality=0;
    UPROPERTY() double Elapsed=0;
    UPROPERTY() double Clearance=0;
    UPROPERTY() double Integrity=1;
    UPROPERTY() double EdgeFit=0;
    UPROPERTY() FString Result;
    UPROPERTY() TArray<uint8> Mask;
};

/** One paid firearm workpiece. Tagged fields keep older profiles compatible. */
USTRUCT()
struct FColdSteelGunAssemblyJob
{
    GENERATED_BODY()
    UPROPERTY() FString Id;
    UPROPERTY() FName Recipe;
    UPROPERTY() FColdSteelItem Item;
    UPROPERTY() TMap<FString,int64> PaidMaterials;
    /** Fixed at creation; free workpieces never use legacy recipe-based refunds. */
    UPROPERTY() bool bMaterialsWaived=false;
    UPROPERTY() int32 QualityVersion=0;
    UPROPERTY() FName Metal;
    UPROPERTY() FString MaterialName;
    UPROPERTY() double MaterialBonus=0.;
    UPROPERTY() int32 InstalledMask=0;
    // Defaults preserve jobs saved by the original five-part recipe.
    UPROPERTY() int32 PartCount=5;
    UPROPERTY() float CalibrationDuration=5;
    /** Zero keeps old saves readable; new/resumed workpieces use timed follow rounds. */
    UPROPERTY() int32 CalibrationVersion=0;
    UPROPERTY() TArray<float> Scores;
    UPROPERTY() TArray<int32> Misses;
    UPROPERTY() float CalibrationSeconds=0;
    UPROPERTY() float CalibrationTime=0;
    UPROPERTY() float CalibrationError=0;
    UPROPERTY() float Quality=0;
    UPROPERTY() bool bFinished=false;
};

/** Paid alchemy batch; unfinished mixtures and unopened ingredients survive UI/world changes. */
USTRUCT()
struct FColdSteelAlchemyJob
{
    GENERATED_BODY()
    UPROPERTY() int32 Version=1;
    UPROPERTY() FString Id;
    UPROPERTY() FName Recipe;
    UPROPERTY() FString RecipeSnapshot;
    UPROPERTY() FString Name;
    UPROPERTY() int64 Revision=0;
    UPROPERTY() TArray<FColdSteelItem> Escrow;
    /** Escrow supplies the brewing tools but is not refundable when waived. */
    UPROPERTY() bool bMaterialsWaived=false;
    UPROPERTY() TMap<FString,int64> Opened;
    UPROPERTY() TMap<FString,int64> Poured;
    UPROPERTY() TArray<float> Progress;
    UPROPERTY() FColdSteelItem Product;
    UPROPERTY() int32 OutputCount=0;
    UPROPERTY() float Temperature=20;
    UPROPERTY() double Elapsed=0;
    UPROPERTY() float Penalty=0;
    UPROPERTY() float ScorchSeconds=0;
    UPROPERTY() TArray<FString> Faults;
    UPROPERTY() bool bFinished=false;
    UPROPERTY() bool bPassed=false;
    UPROPERTY() FString Result;
};

USTRUCT()
struct FColdSteelProfile
{
    GENERATED_BODY()
    UPROPERTY() int32 Version = 1;
    UPROPERTY() int64 Generation = 0;
    UPROPERTY() FString Name = TEXT("轮回者");
    UPROPERTY() FString Class = TEXT("初心者");
    UPROPERTY() int32 Level = 1;
    UPROPERTY() int64 Experience = 0;
    /** Currency is separate from item stacks; missing tagged fields migrate from legacy gold. */
    UPROPERTY() int32 SoulCurrencyVersion = 0;
    UPROPERTY() int64 Souls = 0;
    /** Cumulative remote-server grants already included in Souls; prevents duplicate mirror rewards. */
    UPROPERTY() int64 ServerSoulCredits = 0;
    UPROPERTY() int64 ServerSoulDebits = 0;
    UPROPERTY() int32 Points = 0;
    UPROPERTY() int32 Kills = 0;
    UPROPERTY() int32 ActiveWeaponSlot = 6;
    UPROPERTY() FStableMountRoster MountRoster;
    UPROPERTY() TMap<FName, int32> Attributes;
    UPROPERTY() TArray<FColdSteelItem> Items;
    /** 储物容器键->容量页数（一页 18x12=216 格）。首次打开对应箱子时按档位登记，
     *  之后只增不减，避免调低档位后箱内物品越界。 */
    UPROPERTY() TMap<FString,int32> StoragePages;
    UPROPERTY() int32 AmmoPouchVersion = 0;
    UPROPERTY() TMap<FString,int64> AmmoPouch;
    UPROPERTY() TArray<FString> Hotbar;
    UPROPERTY() TArray<FString> HotbarDefinitions;
    UPROPERTY() int32 QuickBarVersion = 0;
    UPROPERTY() TArray<FColdSteelQuickBinding> QuickBindings;
    UPROPERTY() int32 MagicWheelVersion = 0;
    UPROPERTY() TArray<FName> MagicWheelSkills;
    UPROPERTY() int32 SelectedMagicSlot = INDEX_NONE;
    UPROPERTY() float Health = 200;
    UPROPERTY() float Mana = 250;
    /** Cumulative focus-break charges already included in Mana; legacy saves default to zero. */
    UPROPERTY() double SpellbookFocusManaLoss = 0;
    /** Server-confirmed crystal mana recovery already included in Mana. */
    UPROPERTY() double MagicCrystalManaRestored = 0.;
    UPROPERTY() double StarMarrowManaSpent = 0.;
    void MergeStarMarrowSpend(double Total)
    {
        if(!FMath::IsFinite(Total)||Total<=StarMarrowManaSpent)return;
        Mana=float(FMath::Max(0.,double(Mana)-(Total-StarMarrowManaSpent)));
        StarMarrowManaSpent=Total;
    }
    UPROPERTY() int32 StaminaVersion = 0;
    UPROPERTY() float Stamina = 100;
    UPROPERTY() float StaminaRecoveryDelay = 0;
    UPROPERTY() bool bSprintExhausted = false;
    UPROPERTY() int32 WarehousePages = 5;
    // Missing in legacy saves: one item per cell. Version 1 uses spatial pages.
    UPROPERTY() int32 WarehouseLayoutVersion = 0;
    UPROPERTY() TArray<FString> ArmoryReceived;
    UPROPERTY() int32 EnhancementSupplyVersion = 0;
    UPROPERTY() int32 SkillProgressVersion = 0;
    UPROPERTY() TMap<FName,FColdSteelSkillProgress> Skills;
    // Skill tree (2026-11-15, Content/ColdSteelData/skill-tree.json). Version 0 = legacy save:
    // the one-time migration marks every tree skill learned so no existing ability is revoked.
    UPROPERTY() int32 SkillTreeVersion = 0;
    UPROPERTY() TArray<FName> LearnedSkills;
    UPROPERTY() TMap<FName,FColdSteelSkillSpec> SkillSpecs;
    UPROPERTY() TArray<FColdSteelFormulaBuff> FormulaBuffs;
    UPROPERTY() float FireballCooldown = 0;
    // Skill schema v9: total duration captured when this cooldown was committed.
    UPROPERTY() float FireballCooldownDuration = 0;
    UPROPERTY() bool bFireballReserved = false;
    UPROPERTY() float IceSpikeCooldown = 0;
    UPROPERTY() float IceSpikeCooldownDuration = 0;
    UPROPERTY() bool bIceSpikeReserved = false;
    UPROPERTY() float LightningCooldown = 0;
    UPROPERTY() float LightningCooldownDuration = 0;
    UPROPERTY() float HolyLightCooldown = 0;
    UPROPERTY() float HolyLightCooldownDuration = 0;
    // Owner martial commits survive an older profile upload or reconnect mirror.
    UPROPERTY() int64 MartialCooldownRevision = 0;
    UPROPERTY() float WhirlwindCooldown = 0;
    UPROPERTY() float WhirlwindCooldownDuration = 0;
    UPROPERTY() float SwordUppercutCooldown = 0;
    UPROPERTY() float SwordUppercutCooldownDuration = 0;
    UPROPERTY() float ChainSlashCooldown = 0;
    UPROPERTY() float ChainSlashCooldownDuration = 0;
    UPROPERTY() float LeapStrikeCooldown = 0;
    UPROPERTY() float LeapStrikeCooldownDuration = 0;
    UPROPERTY() float ShadowStepCooldown = 0;
    UPROPERTY() float ShadowStepCooldownDuration = 0;
    // Confirmed network uppercut costs travel with stamina snapshots.
    UPROPERTY() double UppercutStaminaSpent = 0.;
    /** Confirmed oath refunds; cumulative so mirror/RPC reordering cannot pay twice. */
    UPROPERTY() double OathStaminaRestored = 0.;
    void MergeOathStamina(double Total,double Maximum)
    {
        if(!FMath::IsFinite(Total)||Total<=OathStaminaRestored)return;
        Stamina=float(FMath::Clamp(double(Stamina)+Total-OathStaminaRestored,0.,Maximum));
        OathStaminaRestored=Total;
    }
    // Legacy serialized names retained; these now mirror only the live action
    // remaining/duration and are cleared when loading an interrupted session.
    UPROPERTY() float QuickCombatCooldown = 0;
    UPROPERTY() float QuickCombatCooldownDuration = 0;
    UPROPERTY() bool bQuickCombatReserved = false;
    // Optional tagged fields: legacy profiles start with no tools or depleted nodes.
    UPROPERTY() int32 ProductionSupplyVersion = 0;
    UPROPERTY() FString ActiveProductionTool;
    UPROPERTY() TMap<FString,int32> HarvestProgress; // world GUID:v1:layer:candidate -> 表土挖层计数；岩块／树木采尽时补写采尽标记（命中数结算已退役）
    /** 树木生命值口径（2026-09-25）：world GUID:v1:0:candidate -> 剩余生命比例 0..1；缺省＝满血。
     *  存比例而不是绝对值，调树种生命不会作废旧档；成熟的重生树按满血读，不重写记录。 */
    UPROPERTY() TMap<FString,float> TreeHealth;
    /** 岩块生命值口径（2026-09-30 与树木统一）：world GUID:v1:1:candidate -> 剩余生命比例 0..1；缺省＝满血。
     *  旧档按 HarvestProgress（1..3 次命中）在读档时换算，不迁移遍历。 */
    UPROPERTY() TMap<FString,float> RockHealth;
    UPROPERTY() int32 TreeGrowthVersion = 0;
    UPROPERTY() double TreeGrowthDay = 0; // online gameplay time; pause/offline do not advance
    UPROPERTY() int32 FoodVersion=0;
    UPROPERTY() FGuid FoodClockId;
    UPROPERTY() double FoodClockDay=0.;
    UPROPERTY() TMap<FString,FColdSteelTreeGrowth> TreeGrowth;
    // Skill schema v16: persistent cooldowns, transient fields/buffs are not restored.
    UPROPERTY() float MeteorCooldown = 0;
    UPROPERTY() float MeteorCooldownDuration = 0;
    UPROPERTY() float FlameArmorCooldown = 0;
    UPROPERTY() float FlameArmorCooldownDuration = 0;
    UPROPERTY() float IceArmorCooldown = 0;
    UPROPERTY() float LightningHasteCooldown = 0;
    UPROPERTY() float IceArmorCooldownDuration = 0;
    UPROPERTY() float LightningHasteCooldownDuration = 0;
    UPROPERTY() float DragonBreathCooldown = 0;
    UPROPERTY() float DragonBreathCooldownDuration = 0;
    UPROPERTY() float DragonBreathReservedMana = 0;
    UPROPERTY() bool bDragonBreathReserved = false;
    // Geometry, encounters and reward receipts travel with the same character transaction.
    UPROPERTY() FDungeonRunState DungeonRun;
    UPROPERTY() FInfectionState Infection;
    UPROPERTY() TArray<FColdSteelSmeltIntent> SmeltIntents;
    // A receipt barrier: old periodic uploads cannot undo a server campfire debit/credit.
    UPROPERTY() int64 CampfireInventoryRevision=0;
    UPROPERTY() TMap<FString,int64> CampfireWorldReceipts;
    // Personal workbench escrow, absent in legacy v2 saves. Never also present in Items.
    UPROPERTY() FColdSteelItem EnhancementItem;
    UPROPERTY() FColdSteelForgeJob ForgeJob;
    // BlacksmithApprenticeship::EStage. Older tagged saves start with the lesson available.
    UPROPERTY() uint8 BlacksmithApprenticeshipStage=0;
    UPROPERTY() FColdSteelGunAssemblyJob GunAssemblyJob;
    UPROPERTY() FColdSteelWoodworkingJob WoodworkingJob;
    UPROPERTY() uint8 CarpenterApprenticeshipStage=0;
    UPROPERTY() FColdSteelAlchemyJob AlchemyJob;
    // Skill schema v17: the preparation reserves cooldown, release starts its clock.
    UPROPERTY() float IceWallCooldown = 0;
    UPROPERTY() float IceWallCooldownDuration = 0;
    UPROPERTY() bool bIceWallReserved = false;
    UPROPERTY() float IceWallReservedMana = 0;
    UPROPERTY() float IlluminationArrowCooldown=0;
    UPROPERTY() float IlluminationArrowCooldownDuration=0;
    UPROPERTY() float MagicArrowRainCooldown=0;
    UPROPERTY() float MagicArrowRainCooldownDuration=0;
    UPROPERTY() bool bMagicArrowRainReserved=false;
    UPROPERTY() float MagicArrowRainReservedMana=0;
    UPROPERTY() float BlizzardCooldown = 0;
    UPROPERTY() float BlizzardCooldownDuration = 0;
    UPROPERTY() bool bBlizzardReserved = false;
    UPROPERTY() float BlizzardReservedMana = 0;
    UPROPERTY() float AbsoluteZeroCooldown = 0;
    UPROPERTY() float AbsoluteZeroCooldownDuration = 0;
    UPROPERTY() bool bAbsoluteZeroReserved = false;
    UPROPERTY() float AbsoluteZeroReservedMana = 0;
    // Schema v19: persist electric cooldowns and refund abandoned windups on load.
    UPROPERTY() TMap<FName,float> ElectricCooldowns;
    UPROPERTY() TMap<FName,float> ElectricCooldownDurations;
    UPROPERTY() TMap<FName,float> ElectricReservedMana;
    UPROPERTY() FFPSSurvivalState Survival;
    // Empty values in older saves select the player-body catalog defaults.
    UPROPERTY() FName PlayerHeadId;
    UPROPERTY() FName PlayerHairId;
    /** Stable save identity; PIE copies receive their own identity once. */
    UPROPERTY() FGuid NetworkProfileId;
    // Inventory and plants commit in the same checked save; old profiles start empty.
    UPROPERTY() TArray<FColdSteelCropPlant> PlantingCrops;
};

UCLASS()
class UColdSteelProfileSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FColdSteelProfile Profile;
};

struct FColdSteelProposal
{
    bool bValid = false;
    int64 Revision = 0;
    int32 ActiveWeaponSlot = -1;
    FString Reason;
    TArray<FColdSteelItem> Items;
};

namespace ColdSteelInventory
{
    inline bool IsAlchemySpellbook(const FColdSteelItem& I) { return I.Definition==TEXT("ue_alchemy_spellbook"); }
    inline bool IsDualPistol(const FColdSteelItem& I) { return (I.Definition==TEXT("ue_m1911")||I.Definition==TEXT("ue_g18")||I.Definition==TEXT("ue_pit_viper2011")) || (I.Definition==TEXT("ue_dan_wesson715")||I.Definition==TEXT("ue_rsh12")); }
    FPSGAME_API int32 Owner(const TArray<FColdSteelItem>& Items, int32 Place, int32 Cell);
    /**
     * 主手空置时顶替主武器的那把手枪：只取当前武器组配对的副手槽（6→8，9→11）。
     * 空武器组不借用另一组的副手；显示与换弹事务必须使用同一组的物品身份。
     * 配对槽没有手枪、主手有武器或双手工具生效时返回空。
     * 单枪状态机（开镜、换弹、准星）以它为准，与双持/法杖副手互斥。
     */
    inline const FColdSteelItem* LoneOffhandPistol(const FColdSteelProfile& P)
    {
        if(Owner(P.Items,1,P.ActiveWeaponSlot)>=0)return nullptr;
        if(!P.ActiveProductionTool.IsEmpty())return nullptr;
        const int32 PairedSlot=P.ActiveWeaponSlot==6?8:11;
        const int32 Index=Owner(P.Items,1,PairedSlot);
        return Index>=0&&IsDualPistol(P.Items[Index])?&P.Items[Index]:nullptr;
    }
    inline bool UsesKukriMoveset(const FColdSteelItem& Item);
    /**
     * 主手空置时独自出手的副手弯刀族近战（弯刀、斧头，2026-11-04）：只取当前武器组配对的副手槽（6→8，9→11），
     * 规则同 LoneOffhandPistol。由左手单持呈现（单持招式镜像到左手），招式、数值与服务端回执都用这把武器。
     */
    inline const FColdSteelItem* LoneOffhandBlade(const FColdSteelProfile& P)
    {
        if(Owner(P.Items,1,P.ActiveWeaponSlot)>=0)return nullptr;
        if(!P.ActiveProductionTool.IsEmpty())return nullptr;
        const int32 Index=Owner(P.Items,1,P.ActiveWeaponSlot==6?8:11);
        return Index>=0&&UsesKukriMoveset(P.Items[Index])?&P.Items[Index]:nullptr;
    }
    FPSGAME_API FString Text(const FColdSteelItem& Item, const TCHAR* Key);
    FPSGAME_API double Number(const FColdSteelItem& Item, const TCHAR* Key, double Default = 0);
    FPSGAME_API bool Flag(const FColdSteelItem& Item, const TCHAR* Key);
    inline bool IsStaff(const FColdSteelItem& Item)
    {
        return Text(Item,TEXT("weaponType"))==TEXT("staff");
    }
    inline bool HasMeleeCategory(const FColdSteelItem& Item)
    {
        return Text(Item,TEXT("category"))==TEXT("weapon_melee") && !IsStaff(Item);
    }
    inline bool IsEquippedProductionTool(const FColdSteelItem& Item)
    {
        // 2026-10-17 起铁铲与斧／镐同权：装备在主手武器槽使用，不再走 F7 背包覆盖。
        return Item.Definition==TEXT("tool_axe") || Item.Definition==TEXT("tool_pickaxe") ||
            Item.Definition==TEXT("tool_shovel");
    }
    inline bool IsTwoHandedBlunt(const FColdSteelItem& Item)
    {
        return Text(Item,TEXT("category"))==TEXT("weapon_melee") &&
            Text(Item,TEXT("weaponType"))==TEXT("blunt") && Flag(Item,TEXT("isTwoHanded"));
    }
    inline bool IsMeleeWeapon(const FColdSteelItem& Item)
    {
        return Item.Definition==TEXT("ue_rune_sword") || IsEquippedProductionTool(Item) ||
            HasMeleeCategory(Item);
    }
    inline bool IsTwoHandedSword(const FColdSteelItem& Item)
    {
        return Item.Definition==TEXT("ue_rune_sword") ||
            (IsMeleeWeapon(Item) && Text(Item,TEXT("weaponType"))==TEXT("sword") && Flag(Item,TEXT("isTwoHanded")));
    }
    // 单手近战武器共享分类，具体外观与动作家族由各物品目录声明。
    inline bool IsOneHandedMelee(const FColdSteelItem& Item)
    {
        return HasMeleeCategory(Item) && !Flag(Item,TEXT("isTwoHanded"));
    }
    // Keep animation/execution identity separate from weapon type and item ID.
    // Legacy kukri saves retain their original ID/type; new weapons opt in explicitly.
    inline bool UsesKukriMoveset(const FColdSteelItem& Item)
    {
        return Item.Definition==TEXT("ue_kukri")||Text(Item,TEXT("weaponType"))==TEXT("kukri")||
            (IsOneHandedMelee(Item)&&Text(Item,TEXT("melee_animation_family"))==TEXT("kukri"));
    }
    // Equipment eligibility for blades; separate from the legacy combat/stat family classifier.
    inline bool IsOneHandedBlade(const FColdSteelItem& Item)
    {
        if(Text(Item,TEXT("category"))!=TEXT("weapon_melee")||Flag(Item,TEXT("isTwoHanded")))return false;
        const FString Type=Text(Item,TEXT("weaponType"));
        return UsesKukriMoveset(Item)||Type==TEXT("sword")||Type==TEXT("knife")||Type==TEXT("dagger")||Type==TEXT("saber");
    }
    // 弓是独立类别：不进近战判定，也不进枪械的 definition 白名单，
    // 由 `UProductionToolComponent` 之外的 `UBowWeaponComponent` 接管手上表现。
    inline bool IsBow(const FColdSteelItem& Item)
    {
        return Text(Item,TEXT("category"))==TEXT("weapon_bow") || Text(Item,TEXT("weaponType"))==TEXT("bow");
    }
    FPSGAME_API FIntPoint Footprint(const FColdSteelItem& Item);
    // Authored footprint before the placement orientation is applied.
    FPSGAME_API FIntPoint BaseFootprint(const FColdSteelItem& Item);
    // Orientation is 0 upright, 1 rotated, and negative keeps the current value.
    // Square items never rotate; stored Width/Height always follow the result.
    FPSGAME_API void ApplyOrientation(FColdSteelItem& Item, int32 Orientation);
    inline bool CanRotate(const FColdSteelItem& Item) { const FIntPoint Base = BaseFootprint(Item); return Base.X != Base.Y; }
    FPSGAME_API bool Compatible(const FColdSteelItem& A, const FColdSteelItem& B);
    FPSGAME_API bool CanEquip(const FColdSteelItem& Item, int32 Slot);
    FPSGAME_API bool Locked(const TArray<FColdSteelItem>& Items, int32 Slot);
    FPSGAME_API int32 Owner(const TArray<FColdSteelItem>& Items, int32 Place, int32 Cell);
    /** 仓库(4)格位占用查询按储物归属分域：主仓库传 ""，储物箱传其 Container 键；
     *  背包/装备等非仓库位的占用判定忽略 Container。夹层(5)占用按 CompGrid 折行
     *  （零值＝按当前装备的背包推导；加载校验传整表预算值保证与装备栏顺序无关）。 */
    FPSGAME_API int32 Owner(const TArray<FColdSteelItem>& Items, int32 Place, int32 Cell, const FString& Container, FIntPoint CompGrid = FIntPoint::ZeroValue);
    FPSGAME_API bool Fits(const TArray<FColdSteelItem>& Items, const FColdSteelItem& Item, int32 Cell);
    FPSGAME_API bool Insert(TArray<FColdSteelItem>& Items, FColdSteelItem Item, int32 Preferred = -1);
    FPSGAME_API FColdSteelProposal Move(const TArray<FColdSteelItem>& Items, const FString& Id, int32 Place, int32 Cell, int32 Orientation = -1);
    FPSGAME_API bool Validate(const FColdSteelProfile& Profile, FString& Reason);
    // Checked load migration only; normal inventory transactions keep strict validation.
    FPSGAME_API bool MigrateLegacyWoodFootprints(FColdSteelProfile& Profile, bool& Changed, FString& Reason);
    // Updates an authored instance snapshot; callers must place it using the new footprint.
    FPSGAME_API bool MigrateAuthoredItemFootprint(FColdSteelItem& Item, bool& Changed, FString& Reason);
    FPSGAME_API bool MigrateAuthoredGridFootprints(FColdSteelProfile& Profile, bool& Changed, FString& Reason);
    FPSGAME_API const TArray<FString>& SlotNames();
    /** 槽14撑出的主背包行数：基础4行，目录 bagExtraCells 每18格加一行；旧实例／网络镜像统一读当前目录。 */
    FPSGAME_API int32 BagRows(const TArray<FColdSteelItem>& Items);
    /** 背包装备槽(14)的占有者；空槽返回 INDEX_NONE。 */
    FPSGAME_API int32 EquippedBag(const TArray<FColdSteelItem>& Items);
    /** 单件背包物品的夹层网格（长×宽＝列×行，bagCompartmentColumns/Rows，缺省 6×6）；
     *  未定义夹层（bagCompartmentCells 缺失或 ≤0）返回 (0,0)。容量＝列×行。 */
    FPSGAME_API FIntPoint CompartmentGridOf(const FColdSteelItem& BagItem);
    /** 背包装备槽(14)撑出的夹层网格；未装备背包或无夹层返回 (0,0)。 */
    FPSGAME_API FIntPoint CompartmentGrid(const TArray<FColdSteelItem>& Items);
    /** 背包装备槽(14)撑出的夹层容量（格）＝列×行；未装备背包或物品未定义夹层时为 0。 */
    FPSGAME_API int32 CompartmentCells(const TArray<FColdSteelItem>& Items);
    /** Reflow retained contents after slot 14 changes. Failure leaves After unchanged. */
    FPSGAME_API bool ReconcileBagCapacity(const TArray<FColdSteelItem>& Before, TArray<FColdSteelItem>& After, FString& Reason);
    /** 夹层(Place 5)：由背包装备撑出的独立格空间，网格尺寸（长×宽）与容量都由装备的背包定义。 */
    namespace ColdSteelCompartment
    {
        constexpr int32 Place = 5;
        constexpr int32 MaxColumns = 18; // 网格列上限＝抽屉宽度口径（18 格）；行上限给足纵向空间。
        constexpr int32 MaxRows = 24;
        FPSGAME_API bool Fits(const TArray<FColdSteelItem>& Items, const FColdSteelItem& Item, int32 Cell, FIntPoint Grid);
        /** 夹层内移动/放入夹层(5)/放回背包(0)/穿装备(1)：夹层自身格间、背包/装备/仓库↔夹层双向；
         *  Grid 为当前夹层网格（列×行）；WarehouseCapacity 只在仓库来源的交换回填时用来校验腾出格。 */
        FPSGAME_API FColdSteelProposal Transfer(const TArray<FColdSteelItem>& Items, const FString& Id, int32 Destination, int32 Cell, FIntPoint Grid, int32 WarehouseCapacity, int32 Orientation = -1);
    }
}
