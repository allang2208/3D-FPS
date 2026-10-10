#include "ColdSteelItemRarity.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelItemReadCache.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool ColdSteelItemRarity::IsEquipment(const FJsonObject& Data)
{
    FString Category;Data.TryGetStringField(TEXT("category"),Category);
    if(Category==TEXT("weapon")||Category.StartsWith(TEXT("weapon_"))||Category==TEXT("equipment")||
        Category==TEXT("armor")||Category==TEXT("accessory")||Category==TEXT("shield")||
        Category==TEXT("magic_book")||Category==TEXT("tool"))return true;
    // An item's kind, never its current bag/ground location, decides whether it is equipment.
    for(const TCHAR* Key:{TEXT("equipSlot"),TEXT("weaponType"),TEXT("rangedType"),TEXT("offhandType")})
    {FString Value;if(Data.TryGetStringField(Key,Value)&&!Value.IsEmpty())return true;}
    return false;
}

bool ColdSteelItemRarity::IsEquipment(const FColdSteelItem& Item)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);
    return Data&&IsEquipment(*Data);
}

bool ColdSteelItemRarity::Normalize(FColdSteelItem& Item)
{
    const auto Existing=ColdSteelItemData::Read(Item.Data);
    if(!Existing||(!Existing->HasField(TEXT("rarity"))&&!Existing->HasField(TEXT("grade")))||!IsEquipment(*Existing))return false;
    // Never edit the shared read cache or nested enchantment / craftsmanship payloads.
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return false;
    Data->RemoveField(TEXT("rarity"));Data->RemoveField(TEXT("grade"));
    FString Json;FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Json));
    Item.Data=MoveTemp(Json);return true;
}

bool ColdSteelItemRarity::Normalize(TArray<FColdSteelItem>& Items)
{
    bool Changed=false;
    for(auto& Item:Items)Changed=Normalize(Item)||Changed;
    return Changed;
}
