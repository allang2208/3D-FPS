#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "ColdSteelQuickBarTypes.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "ColdSteelInventoryTypes.generated.h"

USTRUCT(BlueprintType)
struct FColdSteelItem
{
    GENERATED_BODY()
    UPROPERTY() FString InstanceId;
    UPROPERTY() FString Definition;
    // Full source data (including processing/attachment fields); never stripped on transfer.
    UPROPERTY() FString Data;
    UPROPERTY() int64 Count = 1;
    UPROPERTY() int64 StackMax = 1;
    UPROPERTY() int32 Width = 1;
    UPROPERTY() int32 Height = 1;
    // Bag/warehouse placement orientation: a rotated instance swaps its grid footprint.
    UPROPERTY() bool bRotated = false;
    UPROPERTY() int32 Place = 0; // 0 backpack, 1 equipment, 2 world, 4 warehouse (3 is UI hotbar)
    /** 扩展储物容器归属：""=背包/装备/主仓库（既有语义不变）；非空=某储物箱的独立格空间
     *  （如 "crate.tier.3"）。物品仍存于同一 Items 数组、沿用 Place 4 与格坐标， occupancy
     *  按 Container 分域，容量记于 Profile.StoragePages。 */
    UPROPERTY() FString Container;
    UPROPERTY() int32 Cell = 0;
    UPROPERTY() int32 BackpackCell = -1;
    UPROPERTY() FString Map;
    UPROPERTY() FVector Position = FVector::ZeroVector;
    UPROPERTY() FRotator WorldRotation = FRotator::ZeroRotator;
    UPROPERTY() FGuid HarvestWorldId; // Ground resources belong to one generated world.
    UPROPERTY() float Cooldown = 0;
    UPROPERTY() int32 Magazine = 30;
    UPROPERTY() int32 Reserve = 90;
    UPROPERTY() FString LoadedAmmoType;
    // Virtual range rounds are never refunded into the owned ammunition pouch.
    UPROPERTY() int32 VirtualMagazineAmmo = 0;
};

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
};

USTRUCT()
struct FColdSteelTreeGrowth
{
    GENERATED_BODY()
    UPROPERTY() double CutAtDay = 0;
    UPROPERTY() float DormantDays = 1;
    UPROPERTY() float MatureDays = 6;
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
    // 运行时一次性标记（与旧 _worldPeachReviveUsed 同寿命：重新献祭才刷新）：
    bool bPeachUsed=false,bMoonshadowUsed=false;
};
/** 冶炼点击已写入角色档、建筑档可能还没落盘时的对账条。Kind：1投料 2收取 3添燃料 4升级 5拆炉。 */
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
    UPROPERTY() int32 Points = 0;
    UPROPERTY() int32 Kills = 0;
    UPROPERTY() int32 ActiveWeaponSlot = 6;
    UPROPERTY() TMap<FName, int32> Attributes;
    UPROPERTY() TArray<FColdSteelItem> Items;
    /** 储物容器键->容量页数（一页 18x12=216 格）。首次打开对应箱子时按档位登记，
     *  之后只增不减，避免调低档位后箱内物品越界。 */
    UPROPERTY() TMap<FString,int32> StoragePages;
    UPROPERTY() TArray<FColdSteelSmeltIntent> SmeltIntents;
    UPROPERTY() int32 AmmoPouchVersion = 0;
    UPROPERTY() TMap<FString,int64> AmmoPouch;
    UPROPERTY() TArray<FString> Hotbar;
    UPROPERTY() TArray<FString> HotbarDefinitions;
    UPROPERTY() int32 QuickBarVersion = 0;
    UPROPERTY() TArray<FColdSteelQuickBinding> QuickBindings;
    UPROPERTY() float Health = 200;
    UPROPERTY() float Mana = 250;
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
    UPROPERTY() float WhirlwindCooldown = 0;
    UPROPERTY() float WhirlwindCooldownDuration = 0;
    UPROPERTY() float QuickCombatCooldown = 0;
    UPROPERTY() float QuickCombatCooldownDuration = 0;
    UPROPERTY() bool bQuickCombatReserved = false;
    // Optional tagged fields: legacy profiles start with no tools or depleted nodes.
    UPROPERTY() int32 ProductionSupplyVersion = 0;
    UPROPERTY() FString ActiveProductionTool;
    UPROPERTY() TMap<FString,int32> HarvestProgress; // world GUID:v1:layer:candidate -> 1..3 hits
    UPROPERTY() int32 TreeGrowthVersion = 0;
    UPROPERTY() double TreeGrowthDay = 0; // online gameplay time; pause/offline do not advance
    UPROPERTY() TMap<FString,FColdSteelTreeGrowth> TreeGrowth;
    // Skill schema v16: persistent cooldowns, transient fields/buffs are not restored.
    UPROPERTY() float MeteorCooldown = 0;
    UPROPERTY() float MeteorCooldownDuration = 0;
    UPROPERTY() float FlameArmorCooldown = 0;
    UPROPERTY() float FlameArmorCooldownDuration = 0;
    UPROPERTY() FInfectionState Infection;
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
    inline bool IsDualPistol(const FColdSteelItem& I) { return I.Definition==TEXT("ue_m1911") || I.Definition==TEXT("ue_dan_wesson715"); }
    FPSGAME_API FString Text(const FColdSteelItem& Item, const TCHAR* Key);
    FPSGAME_API double Number(const FColdSteelItem& Item, const TCHAR* Key, double Default = 0);
    FPSGAME_API bool Flag(const FColdSteelItem& Item, const TCHAR* Key);
    inline bool IsEquippedProductionTool(const FColdSteelItem& Item)
    {
        return Item.Definition==TEXT("tool_axe") || Item.Definition==TEXT("tool_pickaxe");
    }
    inline bool IsMeleeWeapon(const FColdSteelItem& Item)
    {
        return Item.Definition==TEXT("ue_rune_sword") || IsEquippedProductionTool(Item) ||
            Text(Item,TEXT("category"))==TEXT("weapon_melee");
    }
    inline bool IsTwoHandedSword(const FColdSteelItem& Item)
    {
        return Item.Definition==TEXT("ue_rune_sword") ||
            (IsMeleeWeapon(Item) && Text(Item,TEXT("weaponType"))==TEXT("sword") && Flag(Item,TEXT("isTwoHanded")));
    // 弓是独立类别：不进近战判定，也不进枪械的 definition 白名单，
    // 由 `UProductionToolComponent` 之外的 `UBowWeaponComponent` 接管手上表现。
    inline bool IsBow(const FColdSteelItem& Item)
    {
        return Text(Item,TEXT("category"))==TEXT("weapon_bow") || Text(Item,TEXT("weaponType"))==TEXT("bow");
    }
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
     *  背包/装备等非仓库位的占用判定忽略 Container。 */
    FPSGAME_API int32 Owner(const TArray<FColdSteelItem>& Items, int32 Place, int32 Cell, const FString& Container);
    FPSGAME_API bool Fits(const TArray<FColdSteelItem>& Items, const FColdSteelItem& Item, int32 Cell);
    FPSGAME_API bool Insert(TArray<FColdSteelItem>& Items, FColdSteelItem Item, int32 Preferred = -1);
    FPSGAME_API FColdSteelProposal Move(const TArray<FColdSteelItem>& Items, const FString& Id, int32 Place, int32 Cell, int32 Orientation = -1);
    FPSGAME_API bool Validate(const FColdSteelProfile& Profile, FString& Reason);
    // Checked load migration only; normal inventory transactions keep strict validation.
    FPSGAME_API bool MigrateLegacyWoodFootprints(FColdSteelProfile& Profile, bool& Changed, FString& Reason);
    FPSGAME_API const TArray<FString>& SlotNames();
}
