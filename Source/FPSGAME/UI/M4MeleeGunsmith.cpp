#include "ColdSteelWeaponText.h"
#include "../Weapons/PojunGrip.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/RuneboundHammerTuning.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../Weapons/RuneSwordGuardTuning.h"
#include "Engine/GameInstance.h"

bool UM4GunsmithWidget::IsMeleeWorkbench() const
{
    return Model()->IsMelee(Model()->Definition());
}

bool UM4GunsmithWidget::HasSelectedPreview() const
{
    if(IsStandaloneWorkbench())return StandaloneMelee!=nullptr;
    const auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    return Profile->Equipped()&&Profile->Equipped()->InstanceId==Model()->Instance();
}

void UM4GunsmithWidget::AppendMeleeOverview(const FColdSteelItem& Item)
{
    const auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto Parts=bCompareFactory?FGunsmithParts():Model()->Installed(Item);
    auto Row=[this](const TCHAR* Name,double Base,double Final,int32 Digits,const TCHAR* Unit,bool Lower=false)
    {
        const double Delta=Final-Base;const bool Same=FMath::Abs(Delta)<.00001;
        Overview.Add({Name,FString::Printf(TEXT("%.*f%s"),Digits,Base,Unit),FString::Printf(TEXT("%.*f%s"),Digits,Final,Unit),
            Same?TEXT("—"):FString::Printf(TEXT("%+.*f%s"),Digits,Delta,Unit),Same?0:((Delta>0)!=Lower?1:-1)});
    };
    if(ColdSteelInventory::UsesKukriMoveset(Item))
    {
        const auto Before=ColdSteelMelee::Evaluate(Item,Profile,&Parts);
        const auto After=ColdSteelMelee::Evaluate(Item,Profile,&Model()->Draft());
        Row(ColdSteelWeaponText::TotalDamage,Before.Damage,After.Damage,2,TEXT(""));
        Row(ColdSteelWeaponText::AttackInterval,Before.AttackSeconds*1000.,After.AttackSeconds*1000.,0,TEXT(" ms"),true);
        Row(TEXT("攻击距离"),Before.BaseReach/100.,After.BaseReach/100.,2,TEXT(" m"));
        Row(TEXT("普通攻击体力消耗"),Before.AttackStamina,After.AttackStamina,1,TEXT(""),true);
        if(Before.Modifiers.CriticalChanceAdd!=0.||After.Modifiers.CriticalChanceAdd!=0.)
            Row(ColdSteelWeaponText::CriticalChance,Before.Modifiers.CriticalChanceAdd,After.Modifiers.CriticalChanceAdd,0,TEXT("%"));
        Row(ColdSteelWeaponText::ToughnessMultiplier,Before.Modifiers.ToughnessDamage,After.Modifiers.ToughnessDamage,2,TEXT("×"));
        Row(TEXT("重击蓄力速度加成"),Before.HeavyChargeSpeedBonus*100.,After.HeavyChargeSpeedBonus*100.,0,TEXT("%"));
        if(Before.Modifiers.MartialDamage!=1.||After.Modifiers.MartialDamage!=1.)
            Row(TEXT("武技伤害倍率"),Before.Modifiers.MartialDamage,After.Modifiers.MartialDamage,2,TEXT("×"));
        if(Before.Modifiers.HeavyToughness!=1.||After.Modifiers.HeavyToughness!=1.)
            Row(TEXT("重击韧性伤害倍率"),Before.Modifiers.HeavyToughnessMultiplier(),After.Modifiers.HeavyToughnessMultiplier(),2,TEXT("×"));
        if(Before.Modifiers.QuickCombatDamageAdd!=0.||After.Modifiers.QuickCombatDamageAdd!=0.)
            Row(TEXT("快速近战伤害倍率"),Before.QuickCombat.DamageMultiplier,After.QuickCombat.DamageMultiplier,2,TEXT("×"));
        if(Before.Modifiers.QuickCombatToughness!=1.||After.Modifiers.QuickCombatToughness!=1.)
            Row(TEXT("快速近战韧性伤害倍率"),Before.QuickCombat.ToughnessMultiplier,After.QuickCombat.ToughnessMultiplier,2,TEXT("×"));
        if(Before.Modifiers.QuickCombatKnockback!=1.||After.Modifiers.QuickCombatKnockback!=1.)
            Row(TEXT("快速近战击退距离"),Before.QuickCombat.KnockbackCM,After.QuickCombat.KnockbackCM,1,TEXT(" cm"));
        if(Before.Modifiers.MartialCooldown!=1.||After.Modifiers.MartialCooldown!=1.)
            Row(TEXT("武技冷却倍率"),Before.Modifiers.MartialCooldownMultiplier(),After.Modifiers.MartialCooldownMultiplier(),2,TEXT("×"),true);
        return;
    }
    if(ColdSteelInventory::IsTwoHandedBlunt(Item))
    {
        const auto Factory=ColdSteelTool::Evaluate(Item,Profile,&Parts);
        const auto Draft=ColdSteelTool::Evaluate(Item,Profile,&Model()->Draft());
        Row(ColdSteelWeaponText::TotalDamage,Factory.Damage.Total(),Draft.Damage.Total(),2,TEXT(""));
        Row(ColdSteelWeaponText::AttackInterval,Factory.SwingSeconds*1000,Draft.SwingSeconds*1000,0,TEXT(" ms"),true);
        if(Item.Definition==RuneboundHammer::Definition)
        {
            const auto Mult=[](const FGunsmithParts& Runes)
                {return Runes.FindRef(TEXT("rune"))==TEXT("destruction_mana_rune")?RuneboundHammer::DestructionAttributeMultiplier:1.;};
            const auto* Held=Profile->Equipped();
            const auto Power=[](const FGunsmithParts& Spec)
                {return Spec.FindRef(TEXT("hammer_heads"))==RuneboundHammer::StarOathHead?RuneboundHammer::StarOathAttackMultiplier:1.;};
            const auto* Active=Profile->ActiveProductionTool();
            const double InstalledPower=Active?RuneboundHammer::AttackMultiplier(*Active):1.;
            if(Power(Parts)>1.||Power(Model()->Draft())>1.)for(FName Stat:{FName(TEXT("atk")),FName(TEXT("matk"))})
                Row(Stat==TEXT("atk")?TEXT("物理攻击力"):TEXT("魔法攻击力"),
                    Profile->Derived(Stat)/InstalledPower*Power(Parts),
                    Profile->Derived(Stat)/InstalledPower*Power(Model()->Draft()),2,TEXT(""));
            const double Installed=Held?RuneboundHammer::AttributeMultiplier(*Held):1.;
            if(Mult(Parts)>1.||Mult(Model()->Draft())>1.)for(FName Attribute:{FName(TEXT("wis")),FName(TEXT("intt"))})
            {
                const double Base=Profile->Attribute(Attribute)/Installed;
                Row(Attribute==TEXT("wis")?TEXT("精神"):TEXT("智力"),Base*Mult(Parts),Base*Mult(Model()->Draft()),2,TEXT(""));
            }
        }
        Row(ColdSteelWeaponText::AttackDistance,Factory.CombatReachCM/100,Draft.CombatReachCM/100,2,TEXT(" m"));
        Row(ColdSteelWeaponText::StaminaCost,Factory.StaminaCost,Draft.StaminaCost,2,TEXT(""),true);
        if(!FMath::IsNearlyEqual(Factory.HeavyReleaseStaminaCost,Factory.StaminaCost)||!FMath::IsNearlyEqual(Draft.HeavyReleaseStaminaCost,Draft.StaminaCost))
            Row(TEXT("重击出手体力消耗"),Factory.HeavyReleaseStaminaCost,Draft.HeavyReleaseStaminaCost,2,TEXT(""),true);
        Row(TEXT("韧性伤害倍率"),Factory.ToughnessDamage,Draft.ToughnessDamage,2,TEXT("×"));
        if(!FMath::IsNearlyEqual(Factory.HeavyDamageMultiplier,1.)||!FMath::IsNearlyEqual(Draft.HeavyDamageMultiplier,1.))
            Row(TEXT("重击伤害倍率"),Factory.HeavyDamageMultiplier,Draft.HeavyDamageMultiplier,2,TEXT("×"));
        Row(TEXT("重击蓄力速度加成"),Factory.HeavyChargeSpeedBonus*100.,Draft.HeavyChargeSpeedBonus*100.,0,TEXT("%"));
        const auto BeforeRunes=Model()->Calculate(Item.Definition,Parts).Melee;
        const auto AfterRunes=Model()->Calculate(Item.Definition,Model()->Draft()).Melee;
        if(!FMath::IsNearlyEqual(BeforeRunes.BlockStamina,1.)||!FMath::IsNearlyEqual(AfterRunes.BlockStamina,1.))
            Row(ColdSteelWeaponText::BlockStaminaCost,ColdSteelMelee::BlockStamina(BeforeRunes,Profile),ColdSteelMelee::BlockStamina(AfterRunes,Profile),2,TEXT(""),true);
        if(BeforeRunes.MeleeCriticalChanceAdd!=0.||AfterRunes.MeleeCriticalChanceAdd!=0.)
            Row(ColdSteelWeaponText::CriticalChance,BeforeRunes.MeleeCriticalChanceAdd,AfterRunes.MeleeCriticalChanceAdd,0,TEXT("%"));
        if(BeforeRunes.MeleeCriticalDamageBonus!=0.||AfterRunes.MeleeCriticalDamageBonus!=0.)
            Row(TEXT("暴击伤害"),BeforeRunes.MeleeCriticalDamageBonus*100.,AfterRunes.MeleeCriticalDamageBonus*100.,0,TEXT("%"));
        if(!FMath::IsNearlyZero(BeforeRunes.PhysicalAttackAdd)||!FMath::IsNearlyZero(AfterRunes.PhysicalAttackAdd))
            Row(TEXT("物理攻击力"),Factory.PhysicalAttack,Draft.PhysicalAttack,0,TEXT(""));
        if(BeforeRunes.PhysicalArmorPenetration>0.||AfterRunes.PhysicalArmorPenetration>0.)
            Row(TEXT("改造物理防御穿透"),BeforeRunes.PhysicalArmorPenetration*100.,AfterRunes.PhysicalArmorPenetration*100.,0,TEXT("%"));
        Row(TEXT("所有技能冷却倍率"),BeforeRunes.SkillCooldown,AfterRunes.SkillCooldown,2,TEXT("×"),true);
        Row(TEXT("武技冷却倍率"),BeforeRunes.MartialCooldown,AfterRunes.MartialCooldown,2,TEXT("×"),true);
        Row(TEXT("魔法技能冷却倍率"),BeforeRunes.MagicCooldown,AfterRunes.MagicCooldown,2,TEXT("×"),true);
        Row(TEXT("魔法伤害倍率"),BeforeRunes.MagicDamage,AfterRunes.MagicDamage,2,TEXT("×"));
        Row(TEXT("战锤命中魔法易伤"),BeforeRunes.RuneVulnerability*100,AfterRunes.RuneVulnerability*100,0,TEXT("%"));
        Overview.Add({TEXT("握持"),TEXT("双手 · 占用副手"),TEXT("双手 · 占用副手"),TEXT("—"),0});
        return;
    }
    const auto Before=ColdSteelMelee::Evaluate(Item,Profile,&Parts);
    const auto After=ColdSteelMelee::Evaluate(Item,Profile,&Model()->Draft());
    if(Before.Modifiers.CriticalChanceAdd+Before.Modifiers.MeleeCriticalChanceAdd>0.||After.Modifiers.CriticalChanceAdd+After.Modifiers.MeleeCriticalChanceAdd>0.)
        Row(ColdSteelWeaponText::CriticalChance,Before.Modifiers.CriticalChanceAdd+Before.Modifiers.MeleeCriticalChanceAdd,
            After.Modifiers.CriticalChanceAdd+After.Modifiers.MeleeCriticalChanceAdd,0,TEXT("%"));
    if(Before.Modifiers.MeleeCriticalDamageBonus!=0.||After.Modifiers.MeleeCriticalDamageBonus!=0.)
        Row(TEXT("暴击伤害"),Before.Modifiers.MeleeCriticalDamageBonus*100.,After.Modifiers.MeleeCriticalDamageBonus*100.,0,TEXT("%"));
    if(Before.Modifiers.ZhenmoSeconds>0.||After.Modifiers.ZhenmoSeconds>0.)
    {
        Row(TEXT("镇魔阵持续时间"),Before.Modifiers.ZhenmoSeconds,After.Modifiers.ZhenmoSeconds,0,TEXT(" s"));
        Row(TEXT("镇魔阵半径"),Before.Modifiers.ZhenmoRadiusCM/100.,After.Modifiers.ZhenmoRadiusCM/100.,0,TEXT(" m"));
        Row(TEXT("阵内怪物所受伤害增加"),Before.Modifiers.ZhenmoDamageTakenBonus*100.,After.Modifiers.ZhenmoDamageTakenBonus*100.,0,TEXT("%"));
        Row(TEXT("阵内怪物移动减速"),Before.Modifiers.ZhenmoSlow*100.,After.Modifiers.ZhenmoSlow*100.,0,TEXT("%"));
    }
    if(Before.Modifiers.JingangBonus>0.||After.Modifiers.JingangBonus>0.)
    {
        Row(TEXT("金刚物理／魔法防御加成"),Before.Modifiers.JingangBonus*100.,After.Modifiers.JingangBonus*100.,0,TEXT("%"));
        Row(TEXT("高血量物理／魔法伤害加成"),Before.Modifiers.JingangBonus*100.,After.Modifiers.JingangBonus*100.,0,TEXT("%"));
        Row(TEXT("中血量攻速／冷却缩减"),Before.Modifiers.JingangBonus*100.,After.Modifiers.JingangBonus*100.,0,TEXT("%"));
        Row(TEXT("低血量上述全部加成"),Before.Modifiers.JingangBonus*200.,After.Modifiers.JingangBonus*200.,0,TEXT("%"));
        Row(TEXT("攻击吸血比例"),Before.Modifiers.JingangLeechRatio*100.,After.Modifiers.JingangLeechRatio*100.,0,TEXT("%"));
        Row(TEXT("攻击吸血持续时间"),Before.Modifiers.JingangLeechSeconds,After.Modifiers.JingangLeechSeconds,0,TEXT(" s"));
    }
    Row(ColdSteelWeaponText::TotalDamage,Before.Damage,After.Damage,2,TEXT(""));
    if(Before.Modifiers.PhysicalAttackMultiplier!=1.f||After.Modifiers.PhysicalAttackMultiplier!=1.f)
        Row(TEXT("物理攻击力"),Before.PhysicalAttack,After.PhysicalAttack,2,TEXT(""));
    if(ColdSteelInventory::Number(Item,TEXT("innate_erosion_intelligence"))>0||ColdSteelInventory::Number(Item,TEXT("innate_erosion_wisdom"))>0)
        Row(TEXT("自带侵蚀伤害倍率"),Before.Modifiers.InnateErosionMultiplier,After.Modifiers.InnateErosionMultiplier,2,TEXT("×"));
    Row(TEXT("重击伤害倍率"),Before.HeavyMultiplier,After.HeavyMultiplier,2,TEXT("×"));
    Row(TEXT("重击蓄力速度加成"),Before.HeavyChargeSpeedBonus*100.,After.HeavyChargeSpeedBonus*100.,0,TEXT("%"));
    Row(TEXT("重击韧性伤害倍率"),Before.Modifiers.HeavyToughnessMultiplier(),After.Modifiers.HeavyToughnessMultiplier(),2,TEXT("×"));
    Row(TEXT("攻击击退距离"),Before.KnockbackCM,After.KnockbackCM,1,TEXT(" cm"));
    if(Before.Modifiers.AllAttackKnockback!=1.||After.Modifiers.AllAttackKnockback!=1.)
        Row(TEXT("全部攻击击退倍率"),Before.Modifiers.AllAttackKnockback,After.Modifiers.AllAttackKnockback,2,TEXT("×"));
    if(Before.Modifiers.AllAttackDamage!=1.||After.Modifiers.AllAttackDamage!=1.)
        Row(TEXT("全部近战攻击伤害倍率"),Before.Modifiers.AllAttackDamage,After.Modifiers.AllAttackDamage,2,TEXT("×"));
    Row(TEXT("快速近战伤害倍率"),Before.QuickCombat.DamageMultiplier,After.QuickCombat.DamageMultiplier,2,TEXT("×"));
    Row(TEXT("快速近战击退距离"),Before.QuickCombat.KnockbackCM,After.QuickCombat.KnockbackCM,1,TEXT(" cm"));
    Row(TEXT("快速近战韧性伤害倍率"),Before.QuickCombat.ToughnessMultiplier,After.QuickCombat.ToughnessMultiplier,2,TEXT("×"));
    Row(ColdSteelWeaponText::QuickCombatBleed,Before.QuickCombat.BleedChance*100,After.QuickCombat.BleedChance*100,0,TEXT("%"));
    if(Before.Modifiers.QuickCombatTigerRoarSeconds>0||After.Modifiers.QuickCombatTigerRoarSeconds>0)
    {
        Row(ColdSteelWeaponText::TigerRoarToughnessTaken,Before.Modifiers.QuickCombatTigerRoarToughnessBonus*100,After.Modifiers.QuickCombatTigerRoarToughnessBonus*100,0,TEXT("%"));
        Row(ColdSteelWeaponText::TigerRoarDuration,Before.Modifiers.QuickCombatTigerRoarSeconds,After.Modifiers.QuickCombatTigerRoarSeconds,0,TEXT(" s"));
    }
    if(Before.Modifiers.QuickCombatPhysicalVulnerabilitySeconds>0||After.Modifiers.QuickCombatPhysicalVulnerabilitySeconds>0)
    {
        Row(ColdSteelWeaponText::QuickCombatPhysicalVulnerability,Before.Modifiers.QuickCombatPhysicalVulnerabilityBonus*100,After.Modifiers.QuickCombatPhysicalVulnerabilityBonus*100,0,TEXT("%"));
        Row(ColdSteelWeaponText::PhysicalVulnerabilityDuration,Before.Modifiers.QuickCombatPhysicalVulnerabilitySeconds,After.Modifiers.QuickCombatPhysicalVulnerabilitySeconds,0,TEXT(" s"));
    }
    Overview.Add({TEXT("快速近战命中方式"),Before.QuickCombat.bAreaHit?TEXT("范围多目标"):TEXT("单目标"),
        After.QuickCombat.bAreaHit?TEXT("范围多目标"):TEXT("单目标"),
        Before.QuickCombat.bAreaHit==After.QuickCombat.bAreaHit?TEXT("—"):After.QuickCombat.bAreaHit?TEXT("启用范围攻击"):TEXT("恢复单目标"),
        Before.QuickCombat.bAreaHit==After.QuickCombat.bAreaHit?0:After.QuickCombat.bAreaHit?1:-1});
    Row(TEXT("魔法值消耗倍率"),Before.Modifiers.MagicCost,After.Modifiers.MagicCost,2,TEXT("×"),true);
    Row(TEXT("所有技能冷却倍率"),Before.Modifiers.SkillCooldown,After.Modifiers.SkillCooldown,2,TEXT("×"),true);
    Row(TEXT("武技冷却倍率"),Before.Modifiers.MartialCooldown,After.Modifiers.MartialCooldown,2,TEXT("×"),true);
    if(Before.Modifiers.MartialDamage!=1.||After.Modifiers.MartialDamage!=1.)
        Row(TEXT("武技伤害倍率"),Before.Modifiers.MartialDamage,After.Modifiers.MartialDamage,2,TEXT("×"));
    if(Before.Modifiers.MartialRange!=1.||After.Modifiers.MartialRange!=1.)
        Row(TEXT("武技判定范围倍率"),Before.Modifiers.MartialRange,After.Modifiers.MartialRange,2,TEXT("×"));
    Row(TEXT("魔法技能冷却倍率"),Before.Modifiers.MagicCooldown,After.Modifiers.MagicCooldown,2,TEXT("×"),true);
    Row(TEXT("魔法伤害倍率"),Before.Modifiers.MagicDamage,After.Modifiers.MagicDamage,2,TEXT("×"));
    Row(ColdSteelWeaponText::RuneVulnerability,Before.Modifiers.RuneVulnerability*100,After.Modifiers.RuneVulnerability*100,0,TEXT("%"));
    Row(TEXT("剑刃易伤持续时间"),Before.Modifiers.RuneVulnerabilitySeconds,After.Modifiers.RuneVulnerabilitySeconds,0,TEXT(" s"));
    Row(ColdSteelWeaponText::AttackInterval,Before.AttackSeconds*1000,After.AttackSeconds*1000,0,TEXT(" ms"),true);
    const bool CompareSwing=Item.Definition==PojunGrip::Weapon&&
        (Parts.FindRef(TEXT("grip"))==PojunGrip::Part||Model()->Draft().FindRef(TEXT("grip"))==PojunGrip::Part);
    Row(CompareSwing?TEXT("普通攻击距离"):ColdSteelWeaponText::AttackDistance,
        (CompareSwing?Before.SlashReach:Before.ThrustReach)/100,(CompareSwing?After.SlashReach:After.ThrustReach)/100,2,TEXT(" m"));
    Row(ColdSteelWeaponText::StaminaCost,Before.AttackStamina,After.AttackStamina,2,TEXT(""),true);
    Row(TEXT("命中硬直时间倍率"),Before.Modifiers.HitReaction,After.Modifiers.HitReaction,2,TEXT("×"));
    Row(TEXT("韧性伤害倍率"),Before.Modifiers.ToughnessDamage,After.Modifiers.ToughnessDamage,2,TEXT("×"));
    Row(TEXT("改造物理防御穿透"),Before.Modifiers.PhysicalArmorPenetration*100,After.Modifiers.PhysicalArmorPenetration*100,0,TEXT("%"));
    Row(TEXT("格挡伤害减免"),Before.BlockReduction*100,After.BlockReduction*100,0,TEXT("%"));
    if(Item.Definition==TEXT("ue_tang_dao"))
    {
        Row(TEXT("所受伤害倍率（乘法叠加）"),Before.Modifiers.DamageTaken,After.Modifiers.DamageTaken,2,TEXT("×"),true);
        Row(TEXT("闪避体力消耗倍率"),Before.Modifiers.DodgeStamina,After.Modifiers.DodgeStamina,2,TEXT("×"),true);
        Row(TEXT("奔跑体力消耗倍率"),Before.Modifiers.SprintStamina,After.Modifiers.SprintStamina,2,TEXT("×"),true);
        Row(TEXT("龙威下次命中伤害倍率"),Before.Modifiers.DragonDamage,After.Modifiers.DragonDamage,2,TEXT("×"));
        Row(TEXT("龙威额外基础削韧"),Before.Modifiers.DragonToughness,After.Modifiers.DragonToughness,0,TEXT(""));
        Row(TEXT("龙威保留时间"),Before.Modifiers.DragonSeconds,After.Modifiers.DragonSeconds,0,TEXT(" s"));
        Row(TEXT("凤舞攻击速度倍率"),Before.Modifiers.PhoenixSpeed,After.Modifiers.PhoenixSpeed,2,TEXT("×"));
        Row(TEXT("凤舞单次回血（生命上限）"),Before.Modifiers.PhoenixHealRatio*100,After.Modifiers.PhoenixHealRatio*100,0,TEXT("%"));
        Row(TEXT("凤舞回血次数"),Before.Modifiers.PhoenixHealHits,After.Modifiers.PhoenixHealHits,0,TEXT(""));
        Row(TEXT("凤舞持续时间"),Before.Modifiers.PhoenixSeconds,After.Modifiers.PhoenixSeconds,0,TEXT(" s"));
    }
    Row(TEXT("弹反判定时间"),Before.ParrySeconds,After.ParrySeconds,2,TEXT(" s"));
    Row(TEXT("反击激励持续时间"),Before.Modifiers.RiposteSeconds,After.Modifiers.RiposteSeconds,0,TEXT(" s"));
    if(Before.Modifiers.ClovenSeconds>0 || After.Modifiers.ClovenSeconds>0)
    {
        Row(ColdSteelWeaponText::ParryClovenKeep,Before.Modifiers.ClovenSeconds,After.Modifiers.ClovenSeconds,1,TEXT(" s"));
        Row(ColdSteelWeaponText::ClovenPhysicalDamage,(Before.Modifiers.ClovenPhysical-1)*100,(After.Modifiers.ClovenPhysical-1)*100,0,TEXT("%"));
        Row(ColdSteelWeaponText::ClovenToughnessDamage,(Before.Modifiers.ClovenToughness-1)*100,(After.Modifiers.ClovenToughness-1)*100,0,TEXT("%"));
    }
    Row(TEXT("反击激励攻速倍率"),Before.Modifiers.RiposteSpeed,After.Modifiers.RiposteSpeed,2,TEXT("×"));
    Row(TEXT("反击激励耐力倍率"),Before.Modifiers.RiposteStamina,After.Modifiers.RiposteStamina,2,TEXT("×"),true);
    if(!FMath::IsNearlyEqual(Before.Modifiers.PhysicalDefenseMultiplier,1.)||!FMath::IsNearlyEqual(After.Modifiers.PhysicalDefenseMultiplier,1.))
        Row(TEXT("防御力加成"),(Before.Modifiers.PhysicalDefenseMultiplier-1.)*100.,(After.Modifiers.PhysicalDefenseMultiplier-1.)*100.,0,TEXT("%"));
    Row(ColdSteelWeaponText::BlockStaminaCost,Before.BlockStamina,After.BlockStamina,2,TEXT(""),true);
    Overview.Add({TEXT("握持"),TEXT("双手 · 占用副手"),TEXT("双手 · 占用副手"),TEXT("—"),0});
}
