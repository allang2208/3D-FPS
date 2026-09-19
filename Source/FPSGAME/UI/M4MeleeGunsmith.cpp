#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
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
    if(IsMeleeWorkbench())return StandaloneMelee!=nullptr;
    const auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    return Profile->Equipped()&&Profile->Equipped()->InstanceId==Model()->Instance();
}

void UM4GunsmithWidget::AppendMeleeOverview(const FColdSteelItem& Item)
{
    const auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto Parts=bCompareFactory?FGunsmithParts():Model()->Installed(Item);
    const auto Before=ColdSteelMelee::Evaluate(Item,Profile,&Parts);
    const auto After=ColdSteelMelee::Evaluate(Item,Profile,&Model()->Draft());
    auto Row=[this](const TCHAR* Name,double Base,double Final,int32 Digits,const TCHAR* Unit,bool Lower=false)
    {
        const double Delta=Final-Base;const bool Same=FMath::Abs(Delta)<.00001;
        Overview.Add({Name,FString::Printf(TEXT("%.*f%s"),Digits,Base,Unit),FString::Printf(TEXT("%.*f%s"),Digits,Final,Unit),
            Same?TEXT("—"):FString::Printf(TEXT("%+.*f%s"),Digits,Delta,Unit),Same?0:((Delta>0)!=Lower?1:-1)});
    };
    Row(TEXT("普通攻击总伤害"),Before.Damage,After.Damage,2,TEXT(""));
    Row(TEXT("基础物理伤害"),Before.DamageParts.BasePhysical,After.DamageParts.BasePhysical,2,TEXT(""));
    Row(TEXT("附加物理伤害"),Before.DamageParts.AddedPhysical,After.DamageParts.AddedPhysical,2,TEXT(""));
    Row(TEXT("附加魔法伤害"),Before.DamageParts.AddedMagic,After.DamageParts.AddedMagic,2,TEXT(""));
    Row(TEXT("三连击第二段伤害"),Before.ComboSecondDamage,After.ComboSecondDamage,2,TEXT(""));
    Row(TEXT("三连击第三段伤害"),Before.ComboThirdDamage,After.ComboThirdDamage,2,TEXT(""));
    Row(TEXT("重击伤害倍率"),Before.HeavyMultiplier,After.HeavyMultiplier,2,TEXT("×"));
    Row(TEXT("攻击击退距离"),Before.KnockbackCM,After.KnockbackCM,1,TEXT(" cm"));
    Row(TEXT("魔法值消耗倍率"),Before.Modifiers.MagicCost,After.Modifiers.MagicCost,2,TEXT("×"),true);
    Row(TEXT("魔法技能冷却倍率"),Before.Modifiers.MagicCooldown,After.Modifiers.MagicCooldown,2,TEXT("×"),true);
    Row(TEXT("魔法伤害倍率"),Before.Modifiers.MagicDamage,After.Modifiers.MagicDamage,2,TEXT("×"));
    Row(TEXT("命中施加魔法易伤"),Before.Modifiers.RuneVulnerability*100,After.Modifiers.RuneVulnerability*100,0,TEXT("%"));
    Row(TEXT("魔法易伤持续时间"),Before.Modifiers.RuneVulnerabilitySeconds,After.Modifiers.RuneVulnerabilitySeconds,0,TEXT(" s"));
    Row(TEXT("普通攻击间隔"),Before.AttackSeconds,After.AttackSeconds,2,TEXT(" s"),true);
    Row(TEXT("突刺时间"),Before.ThrustSeconds,After.ThrustSeconds,2,TEXT(" s"),true);
    Row(TEXT("普通挥砍距离"),Before.SlashReach/100,After.SlashReach/100,2,TEXT(" m"));
    Row(TEXT("最大攻击距离（含突刺）"),Before.ThrustReach/100,After.ThrustReach/100,2,TEXT(" m"));
    Row(TEXT("攻击耐力消耗（含重击）"),Before.AttackStamina,After.AttackStamina,2,TEXT(""),true);
    Row(TEXT("命中硬直时间倍率"),Before.Modifiers.HitReaction,After.Modifiers.HitReaction,2,TEXT("×"));
    Row(TEXT("格挡伤害减免"),Before.BlockReduction*100,After.BlockReduction*100,0,TEXT("%"));
    Row(TEXT("弹反判定时间"),Before.ParrySeconds,After.ParrySeconds,2,TEXT(" s"));
    Row(TEXT("反击激励持续时间"),Before.Modifiers.RiposteSeconds,After.Modifiers.RiposteSeconds,0,TEXT(" s"));
    Row(TEXT("防御受击耐力消耗"),Before.BlockStamina,After.BlockStamina,2,TEXT(""),true);
    Overview.Add({TEXT("握持"),TEXT("双手 · 占用副手"),TEXT("双手 · 占用副手"),TEXT("—"),0});
}
