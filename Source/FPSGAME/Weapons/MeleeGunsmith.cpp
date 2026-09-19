#include "GunsmithSystem.h"
#include "RuneSwordRhythm.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

const FGunsmithWeapon* UGunsmithSystem::ModifiableWeapon(const FString& Definition) const
{
    if(const auto* Firearm=Weapon(Definition))return Firearm;
    return MeleeWeapons.Find(Definition);
}

void UGunsmithSystem::LoadMeleeCatalog()
{
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/melee-gunsmith.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)
    {UE_LOG(LogTemp,Error,TEXT("Melee gunsmith catalog unavailable"));return;}
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    TMap<FString,TArray<FGunsmithOption>> FactoryOptions;
    for(const auto& Value:Root->GetArrayField(TEXT("columns")))
    {
        const auto Column=Value->AsObject();
        const FString Key=Column->GetStringField(TEXT("key"));
        MeleeSlotKeys.Add(Key);MeleeCategoryNames.Add(Column->GetStringField(TEXT("name")));
        FGunsmithOption Factory;Factory.Id=TEXT("false");
        Factory.Name=Column->GetStringField(TEXT("default"));
        Factory.Description=Column->GetStringField(TEXT("description"));
        MeleeDefaultNames.Add(Factory.Name);
        FactoryOptions.Add(Key,{Factory});
        const TArray<TSharedPtr<FJsonValue>>* Options=nullptr;
        if(Column->TryGetArrayField(TEXT("options"),Options))for(const auto& Entry:*Options)
        {
            const auto Data=Entry->AsObject();FGunsmithOption Part;
            Part.Id=Data->GetStringField(TEXT("id"));Part.Name=Data->GetStringField(TEXT("name"));
            Part.Description=Data->GetStringField(TEXT("description"));
            const TArray<TSharedPtr<FJsonValue>>* Compatible=nullptr;
            if(Data->TryGetArrayField(TEXT("weapons"),Compatible))for(const auto& Id:*Compatible)Part.CompatibleWeapons.Add(Id->AsString());
            for(const auto& Effect:Data->GetArrayField(TEXT("effects")))
                Part.Effects.Emplace(Effect->AsObject()->GetStringField(TEXT("text")),int32(Effect->AsObject()->GetNumberField(TEXT("benefit"))));
            const auto Stats=Data->GetObjectField(TEXT("stats"));
            Stats->TryGetNumberField(TEXT("damage_mult"),Part.Melee.Damage);
            Stats->TryGetNumberField(TEXT("attack_speed_mult"),Part.Melee.AttackSpeed);
            Stats->TryGetNumberField(TEXT("range_mult"),Part.Melee.Range);
            Stats->TryGetNumberField(TEXT("stamina_mult"),Part.Melee.Stamina);
            Stats->TryGetNumberField(TEXT("hit_reaction_mult"),Part.Melee.HitReaction);
            Stats->TryGetNumberField(TEXT("block_reduction_mult"),Part.Melee.BlockReduction);
            Stats->TryGetNumberField(TEXT("combo_second_damage_mult"),Part.Melee.ComboSecond);
            Stats->TryGetNumberField(TEXT("combo_third_damage_mult"),Part.Melee.ComboThird);
            Stats->TryGetNumberField(TEXT("magic_cooldown_mult"),Part.Melee.MagicCooldown);
            Stats->TryGetNumberField(TEXT("magic_damage_mult"),Part.Melee.MagicDamage);
            Stats->TryGetNumberField(TEXT("magic_cost_mult"),Part.Melee.MagicCost);
            Stats->TryGetNumberField(TEXT("heavy_damage_mult"),Part.Melee.HeavyDamage);
            Stats->TryGetNumberField(TEXT("heavy_damage_add"),Part.Melee.HeavyDamageAdd);
            Stats->TryGetNumberField(TEXT("knockback_mult"),Part.Melee.Knockback);
            Stats->TryGetNumberField(TEXT("rune_intelligence"),Part.Melee.RuneIntelligence);
            Stats->TryGetNumberField(TEXT("rune_wisdom"),Part.Melee.RuneWisdom);
            Stats->TryGetNumberField(TEXT("rune_vulnerability"),Part.Melee.RuneVulnerability);
            Stats->TryGetNumberField(TEXT("rune_vulnerability_seconds"),Part.Melee.RuneVulnerabilitySeconds);
            Stats->TryGetNumberField(TEXT("parry_window_mult"),Part.Melee.ParryWindow);
            Stats->TryGetNumberField(TEXT("riposte_attack_speed_mult"),Part.Melee.RiposteSpeed);
            Stats->TryGetNumberField(TEXT("riposte_stamina_mult"),Part.Melee.RiposteStamina);
            Stats->TryGetNumberField(TEXT("riposte_seconds"),Part.Melee.RiposteSeconds);
            FactoryOptions.FindChecked(Key).Add(MoveTemp(Part));
        }
    }
    for(const auto& Value:Root->GetArrayField(TEXT("weapons")))
    {
        const FString Id=Value->AsString();const auto Item=Profile->CreateItem(Id);
        if(!ColdSteelInventory::IsTwoHandedSword(Item))continue;
        FGunsmithWeapon Weapon;Weapon.Id=Id;Weapon.Model=TEXT("two_handed_sword");
        Weapon.Name=ColdSteelInventory::Text(Item,TEXT("name"));
        Weapon.Allowed=MeleeSlotKeys;Weapon.Options=FactoryOptions;
        for(auto& Column:Weapon.Options)Column.Value.RemoveAll([&](const FGunsmithOption& Part){return !Part.CompatibleWeapons.IsEmpty()&&!Part.CompatibleWeapons.Contains(Id);});
        Weapon.Base.Damage=ColdSteelInventory::Number(Item,TEXT("melee_damage"),55);
        Weapon.Base.Interval=RuneSwordRhythm::AttackEnd;
        Weapon.Base.Range=ColdSteelInventory::Number(Item,TEXT("melee_reach_cm"),180)/100.;
        Weapon.Base.ADS=Weapon.Base.Reload=Weapon.Base.EmptyReload=Weapon.Base.Speed=0;
        Weapon.Base.Recoil=Weapon.Base.Shake=Weapon.Base.Spread=0;Weapon.Base.Capacity=0;
        MeleeWeapons.Add(Id,MoveTemp(Weapon));
    }
}
