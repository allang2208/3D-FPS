#include "GunsmithSystem.h"
#include "FrostSwordRunes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
struct FWarhammerColumns {TArray<FString> Slots,Names,Defaults;};
FWarhammerColumns& WarhammerColumns(){static FWarhammerColumns Columns;return Columns;}
}

const TArray<FString>& UGunsmithSystem::Slots(const FString& Definition) const
{
    if(Definition==TEXT("ue_steel_warhammer"))return WarhammerColumns().Slots;
    return Definition==TEXT("ue_rsh12")?RSHSlotKeys:IsStaff(Definition)?StaffSlotKeys:IsBow(Definition)?BowSlotKeys:IsTool(Definition)?ToolSlotKeys:IsMelee(Definition)?MeleeSlotKeys:SlotKeys;
}
const TArray<FString>& UGunsmithSystem::Categories(const FString& Definition) const
{
    if(Definition==TEXT("ue_steel_warhammer"))return WarhammerColumns().Names;
    return Definition==TEXT("ue_rsh12")?RSHCategoryNames:IsStaff(Definition)?StaffCategoryNames:IsBow(Definition)?BowCategoryNames:IsTool(Definition)?ToolCategoryNames:IsMelee(Definition)?MeleeCategoryNames:CategoryNames;
}
const TArray<FString>& UGunsmithSystem::Defaults(const FString& Definition) const
{
    if(Definition==TEXT("ue_steel_warhammer"))return WarhammerColumns().Defaults;
    return Definition==TEXT("ue_rsh12")?RSHDefaultNames:IsStaff(Definition)?StaffDefaultNames:IsBow(Definition)?BowDefaultNames:IsTool(Definition)?ToolDefaultNames:IsMelee(Definition)?MeleeDefaultNames:DefaultNames;
}

void UGunsmithSystem::LoadWarhammerCatalog()
{
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/warhammer-gunsmith.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return;
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Profile)return;
    const auto Item=Profile->CreateItem(Root->GetStringField(TEXT("weapon")));
    if(!ColdSteelInventory::IsTwoHandedBlunt(Item))return;
    FGunsmithWeapon Weapon;Weapon.Id=Item.Definition;Weapon.Model=TEXT("two_handed_blunt");
    Weapon.Name=ColdSteelInventory::Text(Item,TEXT("name"));Weapon.Source=Root;
    Weapon.Base.Damage=ColdSteelInventory::Number(Item,TEXT("melee_damage"));
    Weapon.Base.Interval=ColdSteelInventory::Number(Item,TEXT("swing_seconds"));
    Weapon.Base.Range=ColdSteelInventory::Number(Item,TEXT("combat_reach_cm"))/100.;
    auto& Columns=WarhammerColumns();Columns={};
    for(const auto& Value:Root->GetArrayField(TEXT("columns")))
    {
        const auto Column=Value->AsObject();const FString Key=Column->GetStringField(TEXT("key"));
        Weapon.Allowed.Add(Key);Columns.Slots.Add(Key);Columns.Names.Add(Column->GetStringField(TEXT("name")));
        FGunsmithOption Factory;Factory.Id=TEXT("false");Factory.Name=Column->GetStringField(TEXT("default"));
        Factory.Description=Column->GetStringField(TEXT("description"));
        Columns.Defaults.Add(Factory.Name);Weapon.Options.Add(Key,{Factory});
        FString LibraryFile;const TArray<TSharedPtr<FJsonValue>>* Options=nullptr;
        TArray<TSharedPtr<FJsonValue>> AllOptions;
        TSharedPtr<FJsonObject> Library;
        if(Column->TryGetArrayField(TEXT("options"),Options))AllOptions.Append(*Options);
        if(Column->TryGetStringField(TEXT("options_library"),LibraryFile))
        {
            FString LibraryText;
            if(FFileHelper::LoadFileToString(LibraryText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/LibraryFile))&&
                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(LibraryText),Library)&&Library)
            {
                FString SourceColumn;
                if(Column->TryGetStringField(TEXT("options_column"),SourceColumn))
                {
                    const TArray<TSharedPtr<FJsonValue>>* LibraryColumns=nullptr;
                    if(Library->TryGetArrayField(TEXT("columns"),LibraryColumns))
                        for(const auto& Entry:*LibraryColumns)
                            if(const auto Source=Entry->AsObject();Source&&Source->GetStringField(TEXT("key"))==SourceColumn)
                                if(Source->TryGetArrayField(TEXT("options"),Options))AllOptions.Append(*Options);
                }
                else if(Library->TryGetArrayField(TEXT("options"),Options))AllOptions.Append(*Options);
            }
        }
        for(const auto& OptionValue:AllOptions)
        {
            const auto Data=OptionValue->AsObject();if(!Data)continue;
            if(Key==TEXT("rune")&&!ColdSteelFrostRunes::IsCommon(Data->GetStringField(TEXT("id"))))continue;
            FGunsmithOption Part;Part.Id=Data->GetStringField(TEXT("id"));Part.Name=Data->GetStringField(TEXT("name"));
            Part.Description=Data->GetStringField(TEXT("description"));Data->TryGetStringField(TEXT("appearance"),Part.Appearance);
            Part.ReadSpecialEffects(Data);
            const TArray<TSharedPtr<FJsonValue>>* Effects=nullptr;
            if(Data->TryGetArrayField(TEXT("effects"),Effects))for(const auto& Effect:*Effects)
                Part.Effects.Emplace(Effect->AsObject()->GetStringField(TEXT("text")),int32(Effect->AsObject()->GetNumberField(TEXT("benefit"))));
            const TSharedPtr<FJsonObject>* Stats=nullptr;
            if(Data->TryGetObjectField(TEXT("stats"),Stats))
            {
                (*Stats)->TryGetNumberField(TEXT("physical_damage_mult"),Part.Melee.PhysicalDamage);
                (*Stats)->TryGetNumberField(TEXT("attack_speed_mult"),Part.Melee.AttackSpeed);
                (*Stats)->TryGetNumberField(TEXT("stamina_mult"),Part.Melee.Stamina);
                (*Stats)->TryGetNumberField(TEXT("toughness_damage_mult"),Part.Melee.ToughnessDamage);
                (*Stats)->TryGetNumberField(TEXT("physical_armor_penetration"),Part.Melee.PhysicalArmorPenetration);
                (*Stats)->TryGetNumberField(TEXT("heavy_charge_speed_bonus"),Part.Melee.HeavyChargeSpeedBonus);
                (*Stats)->TryGetNumberField(TEXT("heavy_release_stamina_mult"),Part.Melee.HeavyReleaseStamina);
                (*Stats)->TryGetNumberField(TEXT("skill_cooldown_mult"),Part.Melee.SkillCooldown);
                (*Stats)->TryGetNumberField(TEXT("martial_cooldown_mult"),Part.Melee.MartialCooldown);
                (*Stats)->TryGetNumberField(TEXT("magic_cooldown_mult"),Part.Melee.MagicCooldown);
                (*Stats)->TryGetNumberField(TEXT("magic_damage_mult"),Part.Melee.MagicDamage);
                (*Stats)->TryGetNumberField(TEXT("rune_intelligence"),Part.Melee.RuneIntelligence);
                (*Stats)->TryGetNumberField(TEXT("rune_wisdom"),Part.Melee.RuneWisdom);
                (*Stats)->TryGetNumberField(TEXT("rune_vulnerability"),Part.Melee.RuneVulnerability);
                (*Stats)->TryGetNumberField(TEXT("rune_vulnerability_seconds"),Part.Melee.RuneVulnerabilitySeconds);
            }
            if(Key==TEXT("rune"))
            {
                const auto Adapt=[](const FString& Text)
                {
                    return Text.Replace(TEXT("（普攻、连段、重击、旋风、冲刺及未来的剑刃攻击）"),TEXT("（普攻、连段、重击与冲刺砸地）"))
                        .Replace(TEXT("剑刃攻击"),TEXT("战锤攻击")).Replace(TEXT("沿剑脊收束"),TEXT("沿锤身收束"))
                        .Replace(TEXT("向剑尖掠过"),TEXT("沿锤座掠过")).Replace(TEXT("沿剑刃"),TEXT("沿锤身"))
                        .Replace(TEXT("沿刃面"),TEXT("沿锤面"));
                };
                Part.Description=Adapt(Part.Description);
                for(auto& Effect:Part.Effects)Effect.Key=Adapt(Effect.Key);
                for(auto& Effect:Part.SpecialEffects)Effect=Adapt(Effect);
            }
            Weapon.Options.FindChecked(Key).Add(MoveTemp(Part));
        }
    }
    // Common paired heads retain one ID/stat source across compatible hammer hosts.
    MeleeWeapons.Add(Item.Definition,MoveTemp(Weapon));
}
