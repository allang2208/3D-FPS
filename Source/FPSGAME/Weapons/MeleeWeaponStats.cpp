#include "MeleeWeaponStats.h"
#include "Staff/StaffCatalog.h"
#include "TangDaoGuardComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/SwordUppercutTuning.h"
#include "WeaponDamagePanel.h"
#include "RuneSwordRhythm.h"
#include "RuneSwordThrustRhythm.h"
#include "RuneSwordOverheadRhythm.h"
#include "RuneSwordRisingDragon.h"
#include "ModularSwordVisual.h"
#include "RuneSwordCombatTuning.h"
#include "RuneSwordGuardTuning.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/ResourceCostFormula.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"

FMeleeWeaponStats ColdSteelMelee::Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview)
{
    FMeleeWeaponStats R;
    const auto* GI=Profile?Profile->GetGameInstance():nullptr;
    const auto* Gunsmith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    const auto* Enhance=GI?GI->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    const FGunsmithParts Parts=Preview?*Preview:Gunsmith?Gunsmith->Installed(Item):FGunsmithParts{};
    if(Gunsmith)R.Modifiers=Gunsmith->Calculate(Item.Definition,Parts).Melee;
    const bool OverheadFinisher=ColdSteelModularSword::UsesOverheadFinisher(Item,&Parts);
    const bool RisingDragon=ColdSteelModularSword::UsesRisingDragonFinisher(Item,&Parts);
    if(Profile)R.QuickCombat=Profile->QuickCombatStats(-1,&R.Modifiers);
    const auto Temporary=TemporaryModifiers(Profile);
    R.ParrySeconds=RuneSwordGuardTuning::ParrySeconds*R.Modifiers.ParryWindow;
    const double Base=ColdSteelInventory::Number(Item,TEXT("melee_damage"),55),Attack=Profile?Profile->Derived(TEXT("atk")):0;
    const double BaseDamage=Enhance?Enhance->ProcessedDamage(Item,Base,Attack,R.Modifiers.Damage,Profile):Base*R.Modifiers.Damage+Attack;
    R.DamageParts=ColdSteelWeaponDamage::Evaluate(Item,Profile,BaseDamage,&R.Modifiers);
    R.Damage=R.DamageParts.Total();
    R.ComboSecondDamage=R.Damage*R.Modifiers.ComboMultiplier(2);
    R.ComboThirdDamage=R.Damage*R.Modifiers.ComboMultiplier(3);
    R.HeavyMultiplier=R.Modifiers.HeavyMultiplier(Profile?Profile->MasteryEffect(TEXT("heavyStrike")).HeavyMultiplier:2.5);
    R.HeavyChargeSpeedBonus=R.Modifiers.HeavyChargeSpeedBonus+(Enhance?Enhance->Effect(Item,TEXT("heavyChargeSpeedBonus")):0.)+ColdSteelInventory::Number(Item,TEXT("heavy_charge_speed_bonus"),0.);
    const double SkillCharge=Profile?Profile->MasteryEffect(TEXT("heavyStrike")).HeavyChargeSeconds:2.;
    R.HeavyChargeSeconds=(SkillCharge>0.?SkillCharge:2.)/FMath::Max(.1,1.+R.HeavyChargeSpeedBonus);
    R.KnockbackCM=ColdSteelInventory::Number(Item,TEXT("melee_knockback_cm"),Item.Definition==TEXT("ue_frost_crystal_sword")?20:0)*R.Modifiers.Knockback*R.Modifiers.AllAttackKnockback;
    const double Berserk=Profile?Profile->BerserkAttackSpeedMultiplier():1.;
    // Per-weapon base duration: attack_seconds scales the whole swing clock
    // (animation, contact window, camera, lunge) through AttackRate.
    const double WeaponSpeed=RuneSwordRhythm::AttackEnd/FMath::Max(.1,ColdSteelInventory::Number(Item,TEXT("attack_seconds"),RuneSwordRhythm::AttackEnd));
    R.AttackRate=FMath::Clamp((Profile?double(Profile->Derived(TEXT("aspd")))/Berserk:1.)*R.Modifiers.AttackSpeed*Temporary.AttackSpeed*WeaponSpeed/
        FMath::Max(.1,Enhance?Enhance->Effect(Item,TEXT("attackIntervalMul"),1):1.)/
        (Profile?1-Profile->MasteryEffect(TEXT("swordMastery")).CooldownReduction:1.),.2,4.)*Berserk;
    R.AttackSeconds=RuneSwordRhythm::AttackEnd/R.AttackRate;
    R.ThrustSeconds=(RisingDragon?RuneSwordRisingDragon::AttackSeconds:(OverheadFinisher?RuneSwordOverheadRhythm::FinisherSeconds:RuneSwordThrustRhythm::AttackEnd))/R.AttackRate;
    R.BaseReach=ColdSteelInventory::Number(Item,TEXT("melee_reach_cm"),180);
    R.SlashReach=RuneSwordCombatTuning::ScaledReach(R.BaseReach)*R.Modifiers.Range;
    R.ThrustReach=RuneSwordCombatTuning::ScaledReach(R.BaseReach,RuneSwordThrustRhythm::ReachBonus)*R.Modifiers.Range;
    R.AttackStamina=AttackStamina(&Item,Profile,&R.Modifiers);
    R.BlockStamina=BlockStamina(R.Modifiers,Profile);
    R.BlockReduction=FMath::Clamp((1.-RuneSwordGuardTuning::DamageTakenRatio)*R.Modifiers.BlockReduction,0.,1.);
    return R;
}

double ColdSteelMelee::UppercutMultiplier(const UColdSteelStatusModel* Profile,const FMeleeModifiers& Modifiers,int32 Level)
{
    const float Base=Profile?Profile->MasteryEffect(TEXT("swordUppercut"),Level).HeavyMultiplier:2.5f;
    return SwordUppercut::HeavyDamageScale*Modifiers.HeavyMultiplier(Base);
}

double ColdSteelMelee::UppercutReachCM(const UColdSteelStatusModel* Profile,int32 Level)
{
    const auto* Item=Profile&&!Profile->ActiveProductionTool()?Profile->Equipped():nullptr;
    if(!Item||!ColdSteelInventory::IsTwoHandedSword(*Item))return 0.;
    const double BaseReach=ColdSteelInventory::Number(*Item,TEXT("melee_reach_cm"),180);
    const double ThrustReach=RuneSwordCombatTuning::ScaledReach(BaseReach,RuneSwordThrustRhythm::ReachBonus)*EquippedModifiers(Profile).Range;
    return ThrustReach*Profile->MasteryEffect(TEXT("swordUppercut"),Level).UppercutReachMultiplier;
}

double ColdSteelMelee::BlockStamina(const FMeleeModifiers& Modifiers,const UColdSteelStatusModel* Profile)
{
    return RuneSwordGuardTuning::BlockStamina*Modifiers.BlockStamina*(Profile?Profile->ActionStaminaMultiplier():1.f);
}

FMeleeModifiers ColdSteelMelee::EquippedModifiers(const UColdSteelStatusModel* Profile)
{
    const auto* Tool=Profile?Profile->ActiveProductionTool():nullptr;
    // Blunt weapons use the tool executor but still supply equipped melee passives.
    // A held shovel/harvesting tool must continue to suppress the stored sword.
    const auto* Item=Tool?Tool:Profile?Profile->Equipped():nullptr;
    const auto* G=Profile?Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    return Item&&G&&(ColdSteelInventory::IsTwoHandedSword(*Item)||ColdSteelInventory::IsTwoHandedBlunt(*Item))?
        G->Calculate(Item->Definition,G->Installed(*Item)).Melee:FMeleeModifiers{};
}

double ColdSteelMelee::ModifiedAttackStamina(double BaseCost,double WeaponMultiplier,double TemporaryMultiplier,const UColdSteelStatusModel* Profile)
{
    // EquipmentBonus returns the product of individual remaining-cost factors,
    // minus one. Keep equipment, parts, temporary buffs and set effects separate.
    const double Equipment=Profile?1.+Profile->EquipmentBonus(TEXT("meleeStaminaCost")):1.;
    const double Set=Profile?Profile->ActionStaminaMultiplier():1.;
    // Apply the floor after every reduction zone. Explicit zero base tuning
    // still disables a cost; equipment can never erase a positive base cost.
    return ColdSteelResourceCost::Apply(BaseCost,Equipment*WeaponMultiplier*TemporaryMultiplier*Set);
}

double ColdSteelMelee::AttackStamina(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile,const FMeleeModifiers* PreviewModifiers)
{
    // The HUD attack count and the staff executor share ordinary punch cost.
    if(Item&&ColdSteelStaff::IsStaff(*Item))return UnarmedAttackStamina(Profile);
    // 采集工具按采集体力结算（改造倍率作用在同一份实值上），不套用近战 15 点口径。
    if(Item&&ColdSteelInventory::IsEquippedProductionTool(*Item))
    {
        const double Harvest=Profile?Profile->StaminaSettings().HarvestCost:FColdSteelStaminaTuning{}.HarvestCost;
        const auto* Tools=Profile?Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
        return ModifiedAttackStamina(Harvest,Tools?Tools->Calculate(Item->Definition,Tools->Installed(*Item)).Tool.Stamina:1.,1.,Profile);
    }
    double Base=Profile?Profile->StaminaSettings().MeleeCost:FColdSteelStaminaTuning{}.MeleeCost;
    const auto* Gunsmith=Profile?Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    // The one-handed ratio defines the action's base, including its cost floor.
    if(Item&&ColdSteelInventory::IsOneHandedMelee(*Item))Base*=OneHandedStaminaRatio;
    if(Item&&ColdSteelInventory::IsMeleeWeapon(*Item))
    {
        const auto Modifiers=PreviewModifiers?*PreviewModifiers:Gunsmith?
            Gunsmith->Calculate(Item->Definition,Gunsmith->Installed(*Item)).Melee:FMeleeModifiers{};
        return ModifiedAttackStamina(Base,Modifiers.Stamina,TemporaryModifiers(Profile).Stamina,Profile);
    }
    return ModifiedAttackStamina(Base,1.,1.,Profile);
}

double ColdSteelMelee::HeavyReleaseStamina(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile)
{
    // Pay for both Chixiao cuts once on release, after all ordinary cost modifiers.
    return AttackStamina(Item,Profile)*(Item&&ColdSteelModularSword::UsesChixiaoDoubleHeavy(*Item)?2.:1.);
}

double ColdSteelMelee::UnarmedAttackStamina(const UColdSteelStatusModel* Profile)
{
    const double Base=Profile?Profile->StaminaSettings().PunchCost:FColdSteelStaminaTuning{}.PunchCost;
    return ModifiedAttackStamina(Base,1.,TemporaryModifiers(Profile).Stamina,Profile);
}

FMeleeModifiers ColdSteelMelee::TemporaryModifiers(const UColdSteelStatusModel* Profile)
{
    FMeleeModifiers R;
    const auto* Pawn=Profile?Profile->RuntimePawn():nullptr;
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    if(Status){R.AttackSpeed=Status->RiposteAttackSpeed();R.Stamina=Status->RiposteStaminaMultiplier();}
    if(const auto* Guard=Pawn?Pawn->FindComponentByClass<UTangDaoGuardComponent>():nullptr)R.AttackSpeed*=Guard->AttackSpeedMultiplier();
    return R;
}
