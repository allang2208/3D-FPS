#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "ColdSteelQuickBarTypes.h"
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
    UPROPERTY() int32 Cell = 0;
    UPROPERTY() int32 BackpackCell = -1;
    UPROPERTY() FString Map;
    UPROPERTY() FVector Position = FVector::ZeroVector;
    UPROPERTY() FRotator WorldRotation = FRotator::ZeroRotator;
    UPROPERTY() FGuid HarvestWorldId; // Ground resources belong to one generated world.
    UPROPERTY() float Cooldown = 0;
    UPROPERTY() int32 Magazine = 30;
    UPROPERTY() int32 Reserve = 90;
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
    UPROPERTY() float RemainingSeconds=0;
    UPROPERTY() FString Rarity;
    UPROPERTY() int32 Battles=0;
    UPROPERTY() bool bTribute=false;
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
    FPSGAME_API bool Fits(const TArray<FColdSteelItem>& Items, const FColdSteelItem& Item, int32 Cell);
    FPSGAME_API bool Insert(TArray<FColdSteelItem>& Items, FColdSteelItem Item, int32 Preferred = -1);
    FPSGAME_API FColdSteelProposal Move(const TArray<FColdSteelItem>& Items, const FString& Id, int32 Place, int32 Cell, int32 Orientation = -1);
    FPSGAME_API bool Validate(const FColdSteelProfile& Profile, FString& Reason);
    FPSGAME_API const TArray<FString>& SlotNames();
}
