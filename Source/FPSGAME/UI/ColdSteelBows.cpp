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
    const auto* Item=Equipped();
    return Item && ColdSteelInventory::IsBow(*Item) ? Item : nullptr;
}

bool UColdSteelStatusModel::GrantBow()
{
    SyncRuntime(); auto P=Snapshot();
    FString BowId, ArrowId, Category;
    for (const auto& Pair : Definitions)
    {
        TSharedPtr<FJsonObject> Root;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Pair.Value),Root)||!Root) continue;
        Root->TryGetStringField(TEXT("category"),Category);
        if(Category!=TEXT("weapon_bow")) continue;
        BowId= FString(*Pair.Key);
        Root->TryGetStringField(TEXT("arrow_ammo"),ArrowId);
        break;                                  // 目录里出现多把弓时取遍历到的第一把
    }
    if(BowId.IsEmpty()) return true;            // 没配弓就不打扰存档
    const bool bNeedArrows=!ArrowId.IsEmpty() && PouchCount(ArrowId)<=0;
    bool Changed=false;
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
    }
    if(Changed) CommitState(MoveTemp(P));
    if(bNeedArrows) GrantAmmo(ArrowId,24);      // 首支箭给 24 支，够拉弓试手感
    return true;
}
