#include "../GunsmithSystem.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

void UGunsmithSystem::LoadBowCatalog()
{
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/bow-gunsmith.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return;
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    TMap<FString,TArray<FGunsmithOption>> Options;
    for(const auto& Value:Root->GetArrayField(TEXT("columns")))
    {
        const auto C=Value->AsObject();const FString Key=C->GetStringField(TEXT("key"));
        BowSlotKeys.Add(Key);BowCategoryNames.Add(C->GetStringField(TEXT("name")));BowDefaultNames.Add(C->GetStringField(TEXT("default")));
        FGunsmithOption Factory;Factory.Id=TEXT("false");Factory.Name=C->GetStringField(TEXT("default"));Factory.Description=C->GetStringField(TEXT("description"));
        Factory.Appearance=TEXT("原装独立部件");Factory.BowVisual=C->GetObjectField(TEXT("factory_visual"));Options.Add(Key,{Factory});
        for(const auto& Entry:C->GetArrayField(TEXT("options")))
        {
            auto O=Entry->AsObject();FGunsmithOption Part;
            Part.Id=O->GetStringField(TEXT("id"));Part.Name=O->GetStringField(TEXT("name"));Part.Description=O->GetStringField(TEXT("description"));
            O->TryGetStringField(TEXT("appearance"),Part.Appearance);Part.BowVisual=O->GetObjectField(TEXT("visual"));
            const auto S=O->GetObjectField(TEXT("stats"));
            S->TryGetNumberField(TEXT("damage_mult"),Part.Bow.Damage);S->TryGetNumberField(TEXT("draw_mult"),Part.Bow.Draw);
            S->TryGetNumberField(TEXT("draw_speed_bonus"),Part.Bow.DrawSpeedBonus);
            S->TryGetNumberField(TEXT("speed_mult"),Part.Bow.Speed);S->TryGetNumberField(TEXT("stamina_mult"),Part.Bow.Stamina);
            S->TryGetNumberField(TEXT("nock_mult"),Part.Bow.Nock);S->TryGetNumberField(TEXT("hold_mult"),Part.Bow.Hold);
            S->TryGetNumberField(TEXT("sway_mult"),Part.Bow.Sway);S->TryGetNumberField(TEXT("spread_mult"),Part.Bow.Spread);S->TryGetNumberField(TEXT("ads_mult"),Part.Bow.ADS);
            Options.FindChecked(Key).Add(MoveTemp(Part));
        }
    }
    for(const auto& Entry:Root->GetArrayField(TEXT("weapons")))
    {
        const auto Source=Entry->AsObject();const FString Id=Source->GetStringField(TEXT("id"));const auto I=Profile->CreateItem(Id);
        if(!ColdSteelInventory::IsBow(I))continue;
        FGunsmithWeapon W;W.Id=Id;W.Model=TEXT("bow");W.Name=ColdSteelInventory::Text(I,TEXT("name"));W.Source=Source;
        W.Allowed=BowSlotKeys;W.Options=Options;W.Base.Capacity=0;
        W.Base.Damage=ColdSteelInventory::Number(I,TEXT("full_damage"),69);W.Base.Interval=ColdSteelInventory::Number(I,TEXT("draw_seconds"),1.4);
        W.Base.Speed=ColdSteelInventory::Number(I,TEXT("full_speed_cm"),9800)/100.;W.Base.Range=ColdSteelInventory::Number(I,TEXT("range_cm"),3200)/100.;
        W.Base.ADS=ColdSteelInventory::Number(I,TEXT("bow_ads_in_seconds"),.24);BowWeapons.Add(Id,MoveTemp(W));
    }
}

FColdSteelItem UGunsmithSystem::ResolveBowVisual(const FColdSteelItem& Item,const FGunsmithParts* Override) const
{
    FColdSteelItem Result=Item;if(!IsBow(Item.Definition))return Result;
    TSharedPtr<FJsonObject> Data;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return Result;
    const auto Parts=Override?Normalize(Item.Definition,*Override):Installed(Item);
    auto Set=[&](const FGunsmithOption* O){if(O&&O->BowVisual)for(const auto& Field:O->BowVisual->Values)Data->SetField(Field.Key,Field.Value);};
    for(const auto& Slot:BowSlotKeys)
    {
        // Saved item data is the base recipe. Factory defaults only fill missing
        // fields, preserving custom meshes; selected options are transient patches.
        const auto* Factory=Option(Item.Definition,Slot,TEXT("false"));
        if(Factory&&Factory->BowVisual)for(const auto& Field:Factory->BowVisual->Values)
            if(!Data->HasField(Field.Key))Data->SetField(Field.Key,Field.Value);
        if(const auto* Id=Parts.Find(Slot))Set(Option(Item.Definition,Slot,*Id));
    }
    if(const auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if(const auto* Ammo=Profile->AmmoType(Profile->AmmoDefinitionFor(Item));Ammo&&!Ammo->ProjectileMesh.IsEmpty())
        {
            Data->SetStringField(TEXT("bow_part_arrow_mesh"),Ammo->ProjectileMesh);
            Data->SetStringField(TEXT("bow_part_arrow_material"),TEXT(""));
        }
    if(Override)
    {
        auto Fields=MakeShared<FJsonObject>();for(const auto& Part:Parts)Fields->SetStringField(Part.Key,Part.Value);
        Data->SetObjectField(TEXT("gunsmith_parts"),Fields);
    }
    Result.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Result.Data));return Result;
}
