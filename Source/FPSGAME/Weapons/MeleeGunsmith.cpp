#include "GunsmithSystem.h"
#include "ModularSwordVisual.h"
#include "RuneSwordRhythm.h"
#include "FrostSwordRunes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

const FGunsmithWeapon* UGunsmithSystem::ModifiableWeapon(const FString& Definition) const
{
    if(const auto* Firearm=Weapon(Definition))return Firearm;
    if(const auto* Sword=MeleeWeapons.Find(Definition))return Sword;
    if(const auto* Bow=BowWeapons.Find(Definition))return Bow;
    if(const auto* Staff=StaffWeapons.Find(Definition))return Staff;
    return ToolWeapons.Find(Definition);
}

void UGunsmithSystem::LoadMeleeCatalog()
{
    // Option data and assembly data share a game-instance lifetime. A process-
    // lifetime assembly cache otherwise falls back to factory after new imports.
    ColdSteelModularSword::ResetCatalogCache();
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
            Part.ReadSpecialEffects(Data);
            const TArray<TSharedPtr<FJsonValue>>* Compatible=nullptr;
            if(Data->TryGetArrayField(TEXT("weapons"),Compatible))for(const auto& Id:*Compatible)Part.CompatibleWeapons.Add(Id->AsString());
            for(const auto& Effect:Data->GetArrayField(TEXT("effects")))
                Part.Effects.Emplace(Effect->AsObject()->GetStringField(TEXT("text")),int32(Effect->AsObject()->GetNumberField(TEXT("benefit"))));
            const auto Stats=Data->GetObjectField(TEXT("stats"));
            Stats->TryGetNumberField(TEXT("damage_mult"),Part.Melee.Damage);
            Stats->TryGetNumberField(TEXT("physical_damage_mult"),Part.Melee.PhysicalDamage);
            Stats->TryGetNumberField(TEXT("attack_speed_mult"),Part.Melee.AttackSpeed);
            Stats->TryGetNumberField(TEXT("range_mult"),Part.Melee.Range);
            Stats->TryGetNumberField(TEXT("stamina_mult"),Part.Melee.Stamina);
            Stats->TryGetNumberField(TEXT("kill_stamina_max_ratio"),Part.Melee.KillStaminaMaxRatio);
            Stats->TryGetNumberField(TEXT("hit_reaction_mult"),Part.Melee.HitReaction);
            Stats->TryGetNumberField(TEXT("toughness_damage_mult"),Part.Melee.ToughnessDamage);
            Stats->TryGetNumberField(TEXT("physical_armor_penetration"),Part.Melee.PhysicalArmorPenetration);
            Stats->TryGetNumberField(TEXT("block_reduction_mult"),Part.Melee.BlockReduction);
            Stats->TryGetNumberField(TEXT("block_stamina_mult"),Part.Melee.BlockStamina);
            Stats->TryGetNumberField(TEXT("damage_taken_mult"),Part.Melee.DamageTaken);
            Stats->TryGetNumberField(TEXT("dodge_stamina_mult"),Part.Melee.DodgeStamina);
            Stats->TryGetNumberField(TEXT("sprint_stamina_mult"),Part.Melee.SprintStamina);
            Stats->TryGetNumberField(TEXT("dragon_seconds"),Part.Melee.DragonSeconds);
            Stats->TryGetNumberField(TEXT("dragon_cooldown"),Part.Melee.DragonCooldown);
            Stats->TryGetNumberField(TEXT("dragon_damage_mult"),Part.Melee.DragonDamage);
            Stats->TryGetNumberField(TEXT("dragon_toughness_base"),Part.Melee.DragonToughness);
            Stats->TryGetNumberField(TEXT("phoenix_seconds"),Part.Melee.PhoenixSeconds);
            Stats->TryGetNumberField(TEXT("phoenix_cooldown"),Part.Melee.PhoenixCooldown);
            Stats->TryGetNumberField(TEXT("phoenix_attack_speed_mult"),Part.Melee.PhoenixSpeed);
            Stats->TryGetNumberField(TEXT("phoenix_heal_max_ratio"),Part.Melee.PhoenixHealRatio);
            Stats->TryGetNumberField(TEXT("phoenix_heal_hits"),Part.Melee.PhoenixHealHits);
            Stats->TryGetNumberField(TEXT("combo_second_damage_mult"),Part.Melee.ComboSecond);
            Stats->TryGetNumberField(TEXT("combo_third_damage_mult"),Part.Melee.ComboThird);
            Stats->TryGetNumberField(TEXT("combo_third_toughness_mult"),Part.Melee.ComboThirdToughness);
            Stats->TryGetNumberField(TEXT("magic_cooldown_mult"),Part.Melee.MagicCooldown);
            Stats->TryGetNumberField(TEXT("cooldown_reduce_seconds_per_hit"),Part.Melee.CooldownReduceSecondsPerHit);
            Stats->TryGetNumberField(TEXT("magic_damage_mult"),Part.Melee.MagicDamage);
            Stats->TryGetNumberField(TEXT("magic_cost_mult"),Part.Melee.MagicCost);
            Stats->TryGetNumberField(TEXT("heavy_damage_mult"),Part.Melee.HeavyDamage);
            Stats->TryGetNumberField(TEXT("heavy_toughness_mult"),Part.Melee.HeavyToughness);
            Stats->TryGetNumberField(TEXT("heavy_damage_add"),Part.Melee.HeavyDamageAdd);
            Stats->TryGetNumberField(TEXT("heavy_charge_speed_bonus"),Part.Melee.HeavyChargeSpeedBonus);
            Stats->TryGetNumberField(TEXT("knockback_mult"),Part.Melee.Knockback);
            Stats->TryGetNumberField(TEXT("all_attack_knockback_mult"),Part.Melee.AllAttackKnockback);
            Stats->TryGetNumberField(TEXT("all_attack_damage_mult"),Part.Melee.AllAttackDamage);
            Stats->TryGetNumberField(TEXT("quick_combat_damage_add"),Part.Melee.QuickCombatDamageAdd);
            Stats->TryGetNumberField(TEXT("quick_combat_knockback_mult"),Part.Melee.QuickCombatKnockback);
            Stats->TryGetNumberField(TEXT("quick_combat_toughness_mult"),Part.Melee.QuickCombatToughness);
            Stats->TryGetNumberField(TEXT("quick_combat_bleed_chance"),Part.Melee.QuickCombatBleedChance);
            Stats->TryGetNumberField(TEXT("quick_combat_tiger_roar_toughness_bonus"),Part.Melee.QuickCombatTigerRoarToughnessBonus);
            Stats->TryGetNumberField(TEXT("quick_combat_tiger_roar_seconds"),Part.Melee.QuickCombatTigerRoarSeconds);
            Stats->TryGetNumberField(TEXT("quick_combat_physical_vulnerability_bonus"),Part.Melee.QuickCombatPhysicalVulnerabilityBonus);
            Stats->TryGetNumberField(TEXT("quick_combat_physical_vulnerability_seconds"),Part.Melee.QuickCombatPhysicalVulnerabilitySeconds);
            Stats->TryGetBoolField(TEXT("quick_combat_aoe"),Part.Melee.bQuickCombatAOE);
            Stats->TryGetNumberField(TEXT("quick_combat_rune_vulnerability"),Part.Melee.QuickCombatRuneVulnerability);
            Stats->TryGetNumberField(TEXT("quick_combat_rune_vulnerability_seconds"),Part.Melee.QuickCombatRuneVulnerabilitySeconds);
            Stats->TryGetNumberField(TEXT("rune_intelligence"),Part.Melee.RuneIntelligence);
            Stats->TryGetNumberField(TEXT("rune_wisdom"),Part.Melee.RuneWisdom);
            Stats->TryGetNumberField(TEXT("innate_erosion_mult"),Part.Melee.InnateErosionMultiplier);
            Stats->TryGetNumberField(TEXT("rune_vulnerability"),Part.Melee.RuneVulnerability);
            Stats->TryGetNumberField(TEXT("rune_vulnerability_seconds"),Part.Melee.RuneVulnerabilitySeconds);
            Stats->TryGetNumberField(TEXT("parry_window_mult"),Part.Melee.ParryWindow);
            Stats->TryGetNumberField(TEXT("riposte_attack_speed_mult"),Part.Melee.RiposteSpeed);
            Stats->TryGetNumberField(TEXT("riposte_stamina_mult"),Part.Melee.RiposteStamina);
            Stats->TryGetNumberField(TEXT("riposte_seconds"),Part.Melee.RiposteSeconds);
            Stats->TryGetNumberField(TEXT("cloven_seconds"),Part.Melee.ClovenSeconds);
            Stats->TryGetNumberField(TEXT("cloven_physical_mult"),Part.Melee.ClovenPhysical);
            Stats->TryGetNumberField(TEXT("cloven_toughness_mult"),Part.Melee.ClovenToughness);
            Stats->TryGetNumberField(TEXT("critical_chance_add"),Part.Melee.CriticalChanceAdd);
            Stats->TryGetNumberField(TEXT("zhenmo_seconds"),Part.Melee.ZhenmoSeconds);
            Stats->TryGetNumberField(TEXT("zhenmo_radius_cm"),Part.Melee.ZhenmoRadiusCM);
            Stats->TryGetNumberField(TEXT("zhenmo_damage_taken_bonus"),Part.Melee.ZhenmoDamageTakenBonus);
            Stats->TryGetNumberField(TEXT("zhenmo_slow"),Part.Melee.ZhenmoSlow);
            Stats->TryGetNumberField(TEXT("jingang_bonus"),Part.Melee.JingangBonus);
            Stats->TryGetNumberField(TEXT("jingang_high_threshold"),Part.Melee.JingangHighThreshold);
            Stats->TryGetNumberField(TEXT("jingang_low_threshold"),Part.Melee.JingangLowThreshold);
            Stats->TryGetNumberField(TEXT("jingang_leech_seconds"),Part.Melee.JingangLeechSeconds);
            Stats->TryGetNumberField(TEXT("jingang_leech_ratio"),Part.Melee.JingangLeechRatio);
            Stats->TryGetNumberField(TEXT("panchi_seconds"),Part.Melee.PanChiSeconds);
            Stats->TryGetNumberField(TEXT("panchi_max_stacks"),Part.Melee.PanChiMaxStacks);
            Stats->TryGetNumberField(TEXT("panchi_toughness_per_stack"),Part.Melee.PanChiToughnessPerStack);
            Stats->TryGetNumberField(TEXT("panchi_cooldown"),Part.Melee.PanChiCooldown);
            Stats->TryGetNumberField(TEXT("panchi_radius_cm"),Part.Melee.PanChiRadiusCM);
            Stats->TryGetNumberField(TEXT("panchi_angle_degrees"),Part.Melee.PanChiAngleDegrees);
            Stats->TryGetNumberField(TEXT("panchi_pull_cm"),Part.Melee.PanChiPullCM);
            Stats->TryGetNumberField(TEXT("panchi_magic_damage_scale"),Part.Melee.PanChiMagicDamageScale);
            FactoryOptions.FindChecked(Key).Add(MoveTemp(Part));
        }
    }
    for(const auto& Value:Root->GetArrayField(TEXT("weapons")))
    {
        // 目录条目是对象（保留 traits 等只读展示字段）；仍兼容旧的纯字符串写法。
        const TSharedPtr<FJsonObject> Entry=Value->AsObject();
        const FString Id=Entry?Entry->GetStringField(TEXT("id")):Value->AsString();
        const auto Item=Profile->CreateItem(Id);
        if(!ColdSteelInventory::IsTwoHandedSword(Item))continue;
        FGunsmithWeapon Weapon;Weapon.Id=Id;Weapon.Model=TEXT("two_handed_sword");
        Weapon.Name=ColdSteelInventory::Text(Item,TEXT("name"));
        Weapon.Allowed=MeleeSlotKeys;Weapon.Options=FactoryOptions;
        // Source 让工具提示能读到 traits；没有它近战就永远没有「特殊性质」段。
        Weapon.Source=Entry;
        for(auto& Column:Weapon.Options)Column.Value.RemoveAll([&](const FGunsmithOption& Part){return !Part.CompatibleWeapons.IsEmpty()&&!Part.CompatibleWeapons.Contains(Id);});
        if(Id==ColdSteelFrostRunes::Definition)
            if(auto* Runes=Weapon.Options.Find(TEXT("blade_2"));Runes&&!Runes->IsEmpty())
                (*Runes)[0].Description=TEXT("寒晶自带紫色侵蚀裂纹，近战附加智力与精神转化的魔法伤害；其他符文改造仍保留此效果。");
        Weapon.Base.Damage=ColdSteelInventory::Number(Item,TEXT("melee_damage"),55);
        Weapon.Base.Interval=RuneSwordRhythm::AttackEnd;
        Weapon.Base.Range=ColdSteelInventory::Number(Item,TEXT("melee_reach_cm"),180)/100.;
        Weapon.Base.ADS=Weapon.Base.Reload=Weapon.Base.EmptyReload=Weapon.Base.Speed=0;
        Weapon.Base.Recoil=Weapon.Base.Shake=Weapon.Base.Spread=0;Weapon.Base.Capacity=0;
        MeleeWeapons.Add(Id,MoveTemp(Weapon));
    }
}
