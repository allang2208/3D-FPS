#include "MeleeWeaponStats.h"
#include "WeaponDamagePanel.h"
#include "RuneSwordRhythm.h"
#include "RuneSwordThrustRhythm.h"
#include "RuneSwordCombatTuning.h"
#include "RuneSwordGuardTuning.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Combat/CombatStatusFormula.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"

FMeleeWeaponStats ColdSteelMelee::Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview)
{
    FMeleeWeaponStats R;
    const auto* GI=Profile?Profile->GetGameInstance():nullptr;
    const auto* Gunsmith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    const auto* Enhance=GI?GI->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    if(Gunsmith)R.Modifiers=Gunsmith->Calculate(Item.Definition,Preview?*Preview:Gunsmith->Installed(Item)).Melee;
    if(Profile)R.QuickCombat=Profile->QuickCombatStats(-1,&R.Modifiers);
    const auto Temporary=TemporaryModifiers(Profile);
    R.ParrySeconds=RuneSwordGuardTuning::ParrySeconds*R.Modifiers.ParryWindow;
    const double Base=ColdSteelInventory::Number(Item,TEXT("melee_damage"),55),Attack=Profile?Profile->Derived(TEXT("atk")):0;
    const double BaseDamage=Enhance?Enhance->ProcessedDamage(Item,Base,Attack,R.Modifiers.Damage):Base*R.Modifiers.Damage+Attack;
    R.DamageParts=ColdSteelWeaponDamage::Evaluate(Item,Profile,BaseDamage,&R.Modifiers);
    R.Damage=R.DamageParts.Total();
    R.ComboSecondDamage=R.Damage*R.Modifiers.ComboMultiplier(2);
    R.ComboThirdDamage=R.Damage*R.Modifiers.ComboMultiplier(3);
    R.HeavyMultiplier=R.Modifiers.HeavyMultiplier(Profile?Profile->MasteryEffect(TEXT("heavyStrike")).HeavyMultiplier:2.5);
    R.KnockbackCM=ColdSteelInventory::Number(Item,TEXT("melee_knockback_cm"),Item.Definition==TEXT("ue_frost_crystal_sword")?20:0)*R.Modifiers.Knockback;
    R.AttackRate=FMath::Clamp((Profile?double(Profile->Derived(TEXT("aspd"))):1.)*R.Modifiers.AttackSpeed*Temporary.AttackSpeed/
        FMath::Max(.1,Enhance?Enhance->Effect(Item,TEXT("attackIntervalMul"),1):1.)/
        (Profile?1-Profile->MasteryEffect(TEXT("swordMastery")).CooldownReduction:1.),.2,4.);
    R.AttackSeconds=RuneSwordRhythm::AttackEnd/R.AttackRate;R.ThrustSeconds=RuneSwordThrustRhythm::AttackEnd/R.AttackRate;
    R.BaseReach=ColdSteelInventory::Number(Item,TEXT("melee_reach_cm"),180);
    R.SlashReach=RuneSwordCombatTuning::ScaledReach(R.BaseReach)*R.Modifiers.Range;
    R.ThrustReach=RuneSwordCombatTuning::ScaledReach(R.BaseReach,RuneSwordThrustRhythm::ReachBonus)*R.Modifiers.Range;
    R.AttackStamina=(Profile?Profile->StaminaSettings().MeleeCost:FColdSteelStaminaTuning{}.MeleeCost)*R.Modifiers.Stamina*Temporary.Stamina;
    R.BlockStamina=BlockStamina(R.Modifiers);
    R.BlockReduction=FMath::Clamp((1.-RuneSwordGuardTuning::DamageTakenRatio)*R.Modifiers.BlockReduction,0.,1.);
    return R;
}

double ColdSteelMelee::BlockStamina(const FMeleeModifiers& Modifiers)
{
    return RuneSwordGuardTuning::BlockStamina*Modifiers.BlockStamina;
}

FMeleeModifiers ColdSteelMelee::EquippedModifiers(const UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile&&!Profile->ActiveProductionTool()?Profile->Equipped():nullptr;
    const auto* G=Profile?Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    return Item&&G&&ColdSteelInventory::IsTwoHandedSword(*Item)?G->Calculate(Item->Definition,G->Installed(*Item)).Melee:FMeleeModifiers{};
}

double ColdSteelMelee::AttackStamina(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile)
{
    const double Base=Profile?Profile->StaminaSettings().MeleeCost:FColdSteelStaminaTuning{}.MeleeCost;
    const auto* Gunsmith=Profile?Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    return Item&&Gunsmith&&ColdSteelInventory::IsMeleeWeapon(*Item)?Base*Gunsmith->Calculate(Item->Definition,Gunsmith->Installed(*Item)).Melee.Stamina*TemporaryModifiers(Profile).Stamina:Base;
}

FMeleeModifiers ColdSteelMelee::TemporaryModifiers(const UColdSteelStatusModel* Profile)
{
    FMeleeModifiers R;
    const auto* Pawn=Profile?UGameplayStatics::GetPlayerPawn(Profile,0):nullptr;
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    if(Status){R.AttackSpeed=Status->RiposteAttackSpeed();R.Stamina=Status->RiposteStaminaMultiplier();}
    return R;
}
