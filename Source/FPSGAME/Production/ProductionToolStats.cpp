#include "ProductionToolStats.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../FPSGAMECharacter.h"
#include "ProductionResource.h"
#include "WarhammerHeavyMotion.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "RuneboundHammerTuning.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/WeaponDamagePanel.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Movement/FPSStaminaTuning.h"
#include "Engine/GameInstance.h"

bool ColdSteelTool::Supports(const FColdSteelItem& Item)
{
    return ColdSteelInventory::IsEquippedProductionTool(Item) || PojunGrip::UsesHammerMotion(Item);
}

FProductionToolStats ColdSteelTool::Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview,const FMeleeModifiers* BluntOverride)
{
    FProductionToolStats R;
    const auto* GI=Profile?Profile->GetGameInstance():nullptr;
    const auto* Gunsmith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    const auto* Enhance=GI?GI->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    R.bModifiable=Gunsmith&&Gunsmith->IsTool(Item.Definition);
    if(R.bModifiable)R.Modifiers=Gunsmith->Calculate(Item.Definition,Preview?*Preview:Gunsmith->Installed(Item)).Tool;
    const bool Pojun=Item.Definition==PojunGrip::Weapon&&(Preview?Preview->FindRef(TEXT("grip"))==PojunGrip::Part:PojunGrip::Installed(Item));
    const bool Blunt=Pojun||ColdSteelInventory::IsTwoHandedBlunt(Item);
    FMeleeModifiers BluntModifiers;
    if(Blunt&&Gunsmith)
    {
        R.bModifiable=Gunsmith->IsMelee(Item.Definition);
        BluntModifiers=BluntOverride?*BluntOverride:Gunsmith->Calculate(Item.Definition,Preview?*Preview:Gunsmith->Installed(Item)).Melee;
        R.Modifiers.Damage=BluntModifiers.Damage;
        if(Pojun&&ColdSteelModularSword::UsesOverheadFinisher(Item,Preview))
            R.PofengFinisherMultiplier=BluntModifiers.ComboMultiplier(3);
    }

    // 自卫伤害：工具自己的基础数值 × 改造倍率，再走与剑类相同的附魔／加工后处理。
    // 不借用剑类 Evaluate，避免把连击、格挡与精通口径带进采集工具。
    const double Base=ColdSteelInventory::Number(Item,TEXT("melee_damage"),12);
    double Attack=Profile?Profile->Derived(TEXT("atk")):0;
    // Replace the held grip's flat attack with this item's selected/draft grip.
    // This also keeps inventory previews from inheriting another held grip.
    Attack+=(Blunt?BluntModifiers.PhysicalAttackAdd:0.)-(Profile?ColdSteelMelee::EquippedModifiers(Profile).PhysicalAttackAdd:0.);
    if(Profile&&Preview&&Item.Definition==RuneboundHammer::Definition)
    {
        const auto* Active=Profile->ActiveProductionTool();
        const double Installed=Active?RuneboundHammer::AttackMultiplier(*Active):1.;
        const double Draft=Preview->FindRef(TEXT("hammer_heads"))==RuneboundHammer::StarOathHead?
            RuneboundHammer::StarOathAttackMultiplier:1.;
        Attack=Attack/Installed*Draft;
    }
    R.PhysicalAttack=Attack;
    const double Processed=Enhance?Enhance->ProcessedDamage(Item,Base,Attack,R.Modifiers.Damage,Profile):Base*R.Modifiers.Damage+Attack;
    R.Damage=ColdSteelWeaponDamage::Evaluate(Item,Profile,Processed,Blunt?&BluntModifiers:nullptr);

    R.RateScale=FMath::Clamp(R.Modifiers.AttackSpeed,.25,4.)*(Profile?Profile->BerserkAttackSpeedMultiplier():1.f);
    R.SwingSeconds=ColdSteelInventory::Number(Item,TEXT("swing_seconds"),1.1)/R.RateScale;
    R.ContactSeconds=FMath::Min(ColdSteelInventory::Number(Item,TEXT("contact_seconds"),.48)/R.RateScale,R.SwingSeconds*.9);
    // The preview and server harvest executor use the same final cost floor.
    R.StaminaCost=ColdSteelMelee::ModifiedAttackStamina(
        Profile?Profile->StaminaSettings().HarvestCost:FColdSteelStaminaTuning{}.HarvestCost,R.Modifiers.Stamina,1.,Profile);
    R.HarvestReachCM=ColdSteelInventory::Number(Item,TEXT("harvest_reach_cm"),320)*R.Modifiers.HarvestReach;
    // 宽容半径是「倍率后再加绝对值」：矿镐出厂为 0（只认中心射线），改件的加值才给它辅助宽度。
    R.HarvestRadiusCM=ColdSteelInventory::Number(Item,TEXT("harvest_sweep_radius_cm"),0)*R.Modifiers.HarvestReach
        +R.Modifiers.HarvestRadiusAddCM;
    R.CombatReachCM=ColdSteelInventory::Number(Item,TEXT("combat_reach_cm"),180)*R.Modifiers.CombatReach;
    R.CombatRadiusCM=ColdSteelInventory::Number(Item,TEXT("combat_sweep_radius_cm"),0)*R.Modifiers.CombatReach;
    R.HarvestYield=R.Modifiers.HarvestYield;
    R.BonusHarvestChance=R.Modifiers.BonusHarvestChance;
    R.ToughnessDamage=R.Modifiers.ToughnessDamage;
    R.CriticalChanceAdd=R.Modifiers.CriticalChanceAdd;
    R.HarvestHitsAdd=R.Modifiers.HarvestHitsAdd;
    if(Blunt)
    {
        const auto* Enhancement=GI?GI->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
        R.RateScale=FMath::Clamp((Profile?double(Profile->Derived(TEXT("aspd"))):1.)*BluntModifiers.AttackSpeed/
            FMath::Max(.1,Enhancement?Enhancement->Effect(Item,TEXT("attackIntervalMul"),1):1.),.2,4.)/
            (Profile?Profile->MeleeMasteryIntervalMultiplier(Item):1.f);
        R.SwingSeconds=ColdSteelInventory::Number(Item,Pojun?TEXT("attack_seconds"):TEXT("swing_seconds"),1.16)/R.RateScale;
        R.ContactSeconds=ColdSteelInventory::Number(Item,TEXT("contact_seconds"),Pojun?1.24125:.6)/R.RateScale;
        if(Pojun)R.CombatReachCM=RuneSwordCombatTuning::ScaledReach(ColdSteelInventory::Number(Item,TEXT("melee_reach_cm"),225))*BluntModifiers.Range;
        const auto Heavy=Profile?Profile->MasteryEffect(TEXT("heavyStrike")):FColdSteelSkillEffect{};
        R.HeavyDamageMultiplier=BluntModifiers.HeavyMultiplier(Profile?Heavy.HeavyMultiplier:WarhammerHeavy::DamageMultiplier);
        R.HeavyChargeSpeedBonus=BluntModifiers.HeavyChargeSpeedBonus+
            (Enhance?Enhance->Effect(Item,TEXT("heavyChargeSpeedBonus")):0.)+
            ColdSteelInventory::Number(Item,TEXT("heavy_charge_speed_bonus"),0.);
        R.HeavyChargeSeconds=FMath::Max(.2,(Profile?Heavy.HeavyChargeSeconds:WarhammerHeavy::ChargeSeconds)/
            FMath::Max(.1,1.+R.HeavyChargeSpeedBonus));
        // Supply draft parts before applying the final floor; rescaling an
        // already-clamped installed cost would make the preview inaccurate.
        R.StaminaCost=ColdSteelMelee::AttackStamina(&Item,Profile,&BluntModifiers);
        R.HarvestReachCM=R.HarvestRadiusCM=0.;
        R.ToughnessDamage=ColdSteelInventory::Number(Item,TEXT("toughness_damage_mult"),1.)*BluntModifiers.ToughnessDamage;
    }
    const float Haste=LightningHaste::ActionSpeed(Profile?Profile->RuntimePawn():nullptr);
    R.RateScale*=Haste;R.SwingSeconds/=Haste;R.ContactSeconds/=Haste;R.HeavyChargeSeconds/=Haste;
    R.HeavyReleaseStaminaCost=R.StaminaCost*(Blunt?BluntModifiers.HeavyReleaseStamina:1.);
    return R;
}

FProductionToolStats ColdSteelTool::EvaluateActive(const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview)
{
    const auto* Tool=Profile?Profile->ActiveProductionTool():nullptr;
    return Tool?Evaluate(*Tool,Profile,Preview):FProductionToolStats{};
}

int64 ColdSteelTool::Yield(int64 Factory,const FProductionToolStats& Stats)
{
    if(Factory<=0)return Factory;
    return FMath::Max<int64>(1,FMath::RoundToDouble(double(Factory)*Stats.HarvestYield));
}
