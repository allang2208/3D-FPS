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
        const double Version = ColdSteelInventory::Number(Item, TEXT("bow_presentation_revision"), 0);
        double Latest = 0.;
        Defaults->TryGetNumberField(TEXT("bow_presentation_revision"), Latest);
        if (Version < Latest)
        {
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
                if (!Owned) continue;
                FString Previous;
                if (Key.StartsWith(TEXT("bow_part_")) && Key.EndsWith(TEXT("_mesh")) &&
                    Data->TryGetStringField(Key, Previous) && !Previous.IsEmpty() &&
                    Previous != TEXT("/Game/Weapons/DarkBow20260925/SK_DarkBow.SK_DarkBow")) continue;
                Data->SetField(Key, Field.Value);
            }
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
