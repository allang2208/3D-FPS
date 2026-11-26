#pragma once
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../../UI/ColdSteelItemReadCache.h"

namespace KukriEnchantment
{
inline bool Supports(const FColdSteelItem& Item)
{
    if(ColdSteelInventory::Text(Item,TEXT("category"))!=TEXT("weapon_melee")||
        ColdSteelInventory::Flag(Item,TEXT("isTwoHanded")))return false;
    const FString Type=ColdSteelInventory::Text(Item,TEXT("weaponType"));
    return ColdSteelInventory::UsesKukriMoveset(Item)||Type==TEXT("knife")||Type==TEXT("sword");
}
inline TSharedPtr<const FJsonObject> Effects(const FColdSteelItem& Item)
{
    if(!Supports(Item))return nullptr;
    const auto Data=ColdSteelItemData::Read(Item.Data);
    const TSharedPtr<FJsonObject>* Value=nullptr;
    return Data&&Data->TryGetObjectField(TEXT("_enchantEffects"),Value)?*Value:nullptr;
}
inline bool Has(const FColdSteelItem& Item,const TCHAR* Id)
{
    const auto Data=Effects(Item);bool Enabled=false;
    return Data&&Data->TryGetBoolField(Id,Enabled)&&Enabled;
}
inline FString Selected(const FColdSteelItem& Item)
{
    if(Has(Item,TEXT("bloodWolf")))return TEXT("bloodWolf");
    if(Has(Item,TEXT("frostHawk")))return TEXT("frostHawk");
    return {};
}
inline double PhysicalMultiplier(const FColdSteelItem& Item)
{
    const auto Data=Effects(Item);bool Enabled=false;double Bonus=0.;
    if(Data&&Data->TryGetBoolField(TEXT("bloodWolf"),Enabled)&&Enabled)
        Data->TryGetNumberField(TEXT("bloodWolfPhysicalBonus"),Bonus);
    return 1.+Bonus;
}
inline double CriticalChanceAdd(const FColdSteelItem& Item)
{
    const auto Data=Effects(Item);bool Enabled=false;double Bonus=0.;
    if(Data&&Data->TryGetBoolField(TEXT("frostHawk"),Enabled)&&Enabled)
        Data->TryGetNumberField(TEXT("frostHawkCriticalChanceAdd"),Bonus);
    return Bonus;
}
}
