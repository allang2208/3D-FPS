#pragma once
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Serialization/JsonSerializer.h"

// Seeds a fresh test weapon from the live scroll catalog. This is fixture setup,
// not an enchantment transaction or a substitute for inventory/RPC validation.
namespace KukriEnchantAuditFixture
{
inline bool SetSuffix(FColdSteelItem& Item,const UColdSteelEnhancementSystem* System,const FString& Id)
{
    const auto* Scroll=System?System->Scroll(Id):nullptr;
    if(!Scroll||Scroll->Slot!=TEXT("suffix")||!Scroll->Effects||!System->CanEnchant(Item,*Scroll))return false;
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return false;
    // The fixture starts with CreateItem's complete base data. Keep those fields
    // so weapon identity, compatibility and passive comparisons remain valid.
    auto Affix=MakeShared<FJsonObject>();
    Affix->SetStringField(TEXT("id"),Scroll->Id);Affix->SetStringField(TEXT("name"),Scroll->Name);
    Affix->SetObjectField(TEXT("effects"),Scroll->Effects);
    auto Enchant=MakeShared<FJsonObject>();Enchant->SetObjectField(TEXT("suffix"),Affix);
    Data->SetObjectField(TEXT("_enchantData"),Enchant);
    Data->SetObjectField(TEXT("_enchantEffects"),Scroll->Effects);
    Data->SetBoolField(TEXT("_isEnchanted"),true);
    Item.Data.Reset();return FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Item.Data));
}
}
