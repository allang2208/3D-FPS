// 弓的库存侧接线：目录合并、主手弓解析、首发发放。
// 与 `ColdSteelProductionTools.cpp` 同一口径——definition 由 JSON 提供，库存是唯一事实源；
// 手上表现与射击数值由 `UBowWeaponComponent` 读同一份 Data，不在这里重复。
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelWarehouseRules.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
bool IsShippedDarkBowPartMesh(const FString& Path)
{
    static const TCHAR* Official[] = {
        TEXT("/Game/Weapons/DarkBow20260925/SK_DarkBow.SK_DarkBow"),
        TEXT("/Game/Weapons/DarkBow20260925/ArmsV2/SM_DarkBow_Riser.SM_DarkBow_Riser"),
        TEXT("/Game/Weapons/DarkBow20260925/ArmsV2/SM_Bow_WoodArrow.SM_Bow_WoodArrow"),
        TEXT("/Game/Weapons/DarkBow20260925/RiserDetail20260925/SM_DarkBow_RiserDetail.SM_DarkBow_RiserDetail"),
        TEXT("/Game/Weapons/DarkBow20260925/RiserForm20260925/SM_DarkBow_RiserForm.SM_DarkBow_RiserForm"),
        TEXT("/Game/Weapons/DarkBow20260925/WoodLongbow20260925/SM_DarkBow_WoodLongbow.SM_DarkBow_WoodLongbow"),
        TEXT("/Game/Weapons/DarkBow20260925/SightContactV11/SM_Bow_OpenMechanicalSight.SM_Bow_OpenMechanicalSight"),
        TEXT("/Game/Weapons/DarkBow20260925/WoodSightV12/SM_Bow_CarvedWoodSight.SM_Bow_CarvedWoodSight"),
        TEXT("/Game/Weapons/DarkBow20260925/RingSightV17/SM_Bow_FineRingSight.SM_Bow_FineRingSight"),
        TEXT("/Game/Weapons/DarkBow20260925/WoodBracketV19/SM_Bow_WoodBracketSight.SM_Bow_WoodBracketSight"),
        TEXT("/Game/Weapons/DarkBow20260925/ModularV13/SM_Bow_BodyModular.SM_Bow_BodyModular"),
        TEXT("/Game/Weapons/DarkBow20260925/BodyVariantsV14/SM_Bow_Body_Swift.SM_Bow_Body_Swift"),
        TEXT("/Game/Weapons/DarkBow20260925/BodyVariantsV14/SM_Bow_Body_Heavy.SM_Bow_Body_Heavy"),
        TEXT("/Game/Weapons/DarkBow20260925/BodyVariantsV14/SM_Bow_Body_Steady.SM_Bow_Body_Steady"),
        TEXT("/Game/Weapons/DarkBow20260925/ElasticV15/SK_Bow_Flex_Original.SK_Bow_Flex_Original"),
        TEXT("/Game/Weapons/DarkBow20260925/ElasticV15/SK_Bow_Flex_Swift.SK_Bow_Flex_Swift"),
        TEXT("/Game/Weapons/DarkBow20260925/ElasticV15/SK_Bow_Flex_Heavy.SK_Bow_Flex_Heavy"),
        TEXT("/Game/Weapons/DarkBow20260925/ElasticV15/SK_Bow_Flex_Steady.SK_Bow_Flex_Steady"),
        TEXT("/Game/Weapons/DarkBow20260925/ModularV13/SM_Bow_GripWrap.SM_Bow_GripWrap"),
        TEXT("/Game/Weapons/DarkBow20260925/ModularV13/SM_Bow_ArrowRestWood.SM_Bow_ArrowRestWood"),
        TEXT("/Game/Weapons/DarkBow20260925/ModularV13/SM_Bow_ArrowRestLined.SM_Bow_ArrowRestLined"),
    };
    for (const TCHAR* One : Official)
    {
        if (Path == One) return true;
    }
    return false;
}
}

void UColdSteelStatusModel::LoadBowDefinitions()
{
    FString Json; TSharedPtr<FJsonObject> Root;
    if (!FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir()/TEXT("ColdSteelData/bows.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root)) return;
    for (const auto& Pair : Root->Values)
    {
        FString Data;
        FJsonSerializer::Serialize(Pair.Value->AsObject().ToSharedRef(), TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));
        Definitions.Add(FString(*Pair.Key), Data);
    }
}

const FColdSteelItem* UColdSteelStatusModel::ActiveBow() const
{
    if (ActiveProductionTool()) return nullptr;
    const auto* Item=Equipped();
    return Item && ColdSteelInventory::IsBow(*Item) ? Item : nullptr;
}

bool UColdSteelStatusModel::SelectBowAmmo(const FString& WeaponId, const FString& Target)
{
    // Selection has no magazine transaction: the pouch is debited at release.
    SyncRuntime();
    const auto* Bow = ActiveBow();
    if (!Bow || Bow->InstanceId != WeaponId || !CanSwitchAmmo(WeaponId, Target))
    {
        Message = TEXT("该箭种不可用，当前选择保留");
        return false;
    }
    auto State = Snapshot();
    auto* Item = State.Items.FindByPredicate([&](const auto& Entry) { return Entry.InstanceId == WeaponId; });
    if (!Item) return false;
    Item->LoadedAmmoType = Target;
    Item->Magazine = Item->Reserve = Item->VirtualMagazineAmmo = 0;
    if (!CommitState(MoveTemp(State))) return false;
    Message = TEXT("已选择 ") + AmmoLabel(Target);
    return true;
}

bool UColdSteelStatusModel::NormalizeBowState(FColdSteelProfile& State) const
{
    bool Changed = false;
    for (auto& Item : State.Items)
    {
        if (!ColdSteelInventory::IsBow(Item)) continue;
        const FString* Catalog = Definitions.Find(Item.Definition);
        TSharedPtr<FJsonObject> Data, Defaults;
        if (!Catalog || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data), Data) || !Data ||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Catalog), Defaults) || !Defaults) continue;
        bool bUpdated = false;
        const double Version = ColdSteelInventory::Number(Item, TEXT("bow_presentation_revision"), 0);
        double Latest = 0.;
        Defaults->TryGetNumberField(TEXT("bow_presentation_revision"), Latest);
        if (Version < Latest)
        {
            if(Version<25&&Latest>=25)
            {
                TArray<FString> Keys;for(const auto& Field:Data->Values)Keys.Add(FString(*Field.Key));
                for(const auto& Key:Keys)if(Key.StartsWith(TEXT("bow_part_arrow_rest_")))
                {
                    const FString NewKey=Key.Replace(TEXT("bow_part_arrow_rest_"),TEXT("bow_part_arrow_"));
                    if(!Data->HasField(NewKey))Data->SetField(NewKey,Data->Values.FindChecked(*Key));
                    Data->RemoveField(Key);
                }
            }
            // Migrate presentation only: keep instance ID, placement, quality,
            // combat numbers, upgrades and any custom replacement part meshes.
            for (const auto& Field : Defaults->Values)
            {
                const FString Key(*Field.Key);
                const bool Owned = Key.StartsWith(TEXT("bow_")) || Key.StartsWith(TEXT("nock_")) ||
                    Key.StartsWith(TEXT("reference_")) || Key == TEXT("brace_nock_cm") || Key == TEXT("draw_anchor_cm") ||
                    Key == TEXT("arrow_rest_cm") || Key == TEXT("draw_curve") || Key == TEXT("arrow_head_mesh") ||
                    Key == TEXT("equip_seconds") || Key == TEXT("draw_seconds") || Key == TEXT("release_seconds") ||
                    Key == TEXT("recover_seconds") || Key == TEXT("ue_icon");
                if (!Owned || Key == TEXT("bow_traits_revision") || Key == TEXT("bow_damage_revision") ||
                    Key == TEXT("bow_damage_coefficient_scale")) continue;
                FString Previous;
                if (Key.StartsWith(TEXT("bow_part_")) && Key.EndsWith(TEXT("_mesh")) &&
                    Data->TryGetStringField(Key, Previous) && !Previous.IsEmpty() &&
                    !IsShippedDarkBowPartMesh(Previous)) continue;
                Data->SetField(Key, Field.Value);
            }
            bUpdated = true;
        }
        // Apply balance revisions once to every persisted bow, including bows
        // in storage. Preserve enhancement level, quality and custom parts.
        double DamageVersion=0., LatestDamage=0.;
        Data->TryGetNumberField(TEXT("bow_damage_revision"),DamageVersion);
        Defaults->TryGetNumberField(TEXT("bow_damage_revision"),LatestDamage);
        if(DamageVersion<1. && LatestDamage>=1.)
        {
            double PreviousBase=46.;Data->TryGetNumberField(TEXT("full_damage"),PreviousBase);
            Data->SetNumberField(TEXT("full_damage"),PreviousBase*1.5);
            Data->SetNumberField(TEXT("bow_damage_coefficient_scale"),1.5);
            Data->SetNumberField(TEXT("bow_damage_revision"),1.);
            bUpdated=true;
        }
        // Weapon-owned traits have a separate migration from presentation.
        // Bring existing bows onto the sniper's additive critical bonus field
        // without resetting upgrades, custom parts or the other combat stats.
        double TraitVersion = 0., LatestTraits = 0.;
        Data->TryGetNumberField(TEXT("bow_traits_revision"), TraitVersion);
        Defaults->TryGetNumberField(TEXT("bow_traits_revision"), LatestTraits);
        if (TraitVersion < LatestTraits)
        {
            double CriticalBonus = 0.;
            if (Defaults->TryGetNumberField(TEXT("critDamageBonus"), CriticalBonus))
                Data->SetNumberField(TEXT("critDamageBonus"), CriticalBonus);
            Data->SetNumberField(TEXT("bow_traits_revision"), LatestTraits);
            bUpdated = true;
        }
        if (bUpdated)
        {
            Item.Data.Reset();
            FJsonSerializer::Serialize(Data.ToSharedRef(), TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item.Data));
            Changed = true;
        }
        // The first revision inherited the generic default of a 30-round gun
        // magazine; arrows live in the pouch and have no magazine or reserve.
        if (Item.Magazine != 0 || Item.Reserve != 0) { Item.Magazine = Item.Reserve = 0; Changed = true; }
    }
    return Changed;
}

bool UColdSteelStatusModel::GrantBow()
{
    SyncRuntime(); auto P=Snapshot();
    FString BowId, ArrowId, Category;
    TArray<FString> Keys;
    Definitions.GetKeys(Keys); Keys.Sort();
    for (const auto& Key : Keys)
    {
        TSharedPtr<FJsonObject> Root;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Definitions.FindChecked(Key)),Root)||!Root) continue;
        Category.Reset();
        Root->TryGetStringField(TEXT("category"),Category);
        if(Category!=TEXT("weapon_bow")) continue;
        BowId= Key;
        Root->TryGetStringField(TEXT("arrow_ammo"),ArrowId);
        break;                                  // 目录里出现多把弓时取遍历到的第一把
    }
    if(BowId.IsEmpty()) return true;            // 没配弓就不打扰存档
    bool Changed=NormalizeBowState(P);
    bool bCreatedBow=false;
    if(!P.Items.ContainsByPredicate([&](const auto& I){return I.Definition==BowId;}))
    {
        auto Item=CreateItem(BowId);
        if(Item.Data.IsEmpty()){Message=TEXT("弓目录未加载");return false;}
        if(!ColdSteelInventory::Insert(P.Items,Item) &&
           !ColdSteelWarehouse::Insert(P.Items,Item,WarehouseCapacity()))
        {
            Message=TEXT("背包和仓库空间不足，腾出空间后再领取弓");
            return false;
        }
        Changed=true;
        bCreatedBow=true;
    }
    if(bCreatedBow && !ArrowId.IsEmpty() && !AddAmmoToState(P,ArrowId,24))
    {Message=TEXT("箭种未登记或箭袋已满，弓尚未发放");return false;}
    if(Changed && !CommitState(MoveTemp(P))) return false;
    return true;
}
