#include "MeleeWeaponStats.h"
#include "WoodenTorchItem.h"
#include "EagleTalonGuardComponent.h"
#include "../Weapons/PojunGrip.h"
#include "Kukri/KukriBerserkerComponent.h"
#include "Kukri/KukriEnchantment.h"
#include "../Skills/LightningHasteSpeed.h"
#include "Staff/StaffCatalog.h"
#include "TangDaoGuardComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Skills/SwordUppercutWeapon.h"
#include "WeaponDamagePanel.h"
#include "RuneSwordRhythm.h"
#include "RuneSwordThrustRhythm.h"
#include "RuneSwordOverheadRhythm.h"
#include "RuneSwordRisingDragon.h"
#include "ModularSwordVisual.h"
#include "HighlandRidgeThrust.h"
#include "RuneSwordCombatTuning.h"
#include "RuneSwordGuardTuning.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/ResourceCostFormula.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"

double FMeleeWeaponStats::AttackSpeedMultiplier(const FColdSteelItem& Item) const
{
    const double BaseAttackSeconds=FMath::Max(.1,ColdSteelInventory::Number(Item,TEXT("attack_seconds"),RuneSwordRhythm::AttackEnd));
    return BaseAttackSeconds/AttackSeconds;
}

FMeleeWeaponStats ColdSteelMelee::Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview)
{
    FMeleeWeaponStats R;
    const auto* GI=Profile?Profile->GetGameInstance():nullptr;
    const auto* Gunsmith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    const auto* Enhance=GI?GI->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    const FGunsmithParts Parts=Preview?*Preview:Gunsmith?Gunsmith->Installed(Item):FGunsmithParts{};
    if(Gunsmith)R.Modifiers=Gunsmith->Calculate(Item.Definition,Parts).Melee;
    R.Modifiers.CriticalChanceAdd+=KukriEnchantment::CriticalChanceAdd(Item);
    if(Profile&&ColdSteelInventory::IsOneHandedMelee(Item)&&!ColdSteelInventory::IsWoodenTorch(Item))
        R.Modifiers.CriticalChanceAdd+=Profile->MasteryEffect(TEXT("oneHandedMastery")).CriticalChance;
    const bool Berserker=UKukriBerserkerComponent::Active(&Item,Profile);
    if(Berserker)R.Modifiers.Stamina=0.;
    const bool OverheadFinisher=ColdSteelModularSword::UsesOverheadFinisher(Item,&Parts);
    const bool RisingDragon=ColdSteelModularSword::UsesRisingDragonFinisher(Item,&Parts);
    if(Profile)R.QuickCombat=Profile->QuickCombatStats(-1,&R.Modifiers,&Item,Preview);
    const auto Temporary=TemporaryModifiers(Profile);
    R.ParrySeconds=RuneSwordGuardTuning::ParrySeconds*R.Modifiers.ParryWindow;
    R.PhysicalAttack=Profile?Profile->Derived(TEXT("atk")):0.;
    // Derived attack contains the currently equipped parts. A previously
    // committed swing can refer to older parts on the very same sword.
    const auto* Equipped=Profile&&Item.Definition==TEXT("ue_forged_steel_greatsword")?Profile->Equipped():nullptr;
    const bool bEarlierParts=Equipped&&Equipped!=&Item&&Equipped->InstanceId==Item.InstanceId&&Equipped->Data!=Item.Data;
    if(Profile&&(Preview||bEarlierParts))
    {
        const auto Held=EquippedModifiers(Profile);
        R.PhysicalAttack=R.PhysicalAttack/Held.PhysicalAttackMultiplier*R.Modifiers.PhysicalAttackMultiplier;
    }
    const double Base=ColdSteelInventory::Number(Item,TEXT("melee_damage"),55),Attack=R.PhysicalAttack;
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
    const double BaseAttackSeconds=FMath::Max(.1,ColdSteelInventory::Number(Item,TEXT("attack_seconds"),RuneSwordRhythm::AttackEnd));
    // Limit bonuses relative to this weapon's own base interval. A naturally fast
    // blade must not spend its speed allowance on conversion to the sword clock.
    const double AttackSpeedMultiplier=FMath::Clamp((Profile?double(Profile->Derived(TEXT("aspd")))/Berserk:1.)*R.Modifiers.AttackSpeed*Temporary.AttackSpeed/
        FMath::Max(.1,Enhance?Enhance->Effect(Item,TEXT("attackIntervalMul"),1):1.)/
        (Profile?Profile->MeleeMasteryIntervalMultiplier(Item):1.),.2,4.)*Berserk;
    R.AttackSeconds=BaseAttackSeconds/(AttackSpeedMultiplier*(Berserker?1.25:1.)*LightningHaste::ActionSpeed(Profile?Profile->RuntimePawn():nullptr));
    // Animation, contact windows, camera and movement retain their shared clock.
    // Convert only after applying the one per-weapon speed limit above.
    R.AttackRate=RuneSwordRhythm::AttackEnd/R.AttackSeconds;
    R.HeavyChargeSeconds/=LightningHaste::ActionSpeed(Profile?Profile->RuntimePawn():nullptr);
    R.ThrustSeconds=(RisingDragon?RuneSwordRisingDragon::AttackSeconds:(OverheadFinisher?RuneSwordOverheadRhythm::FinisherSeconds:RuneSwordThrustRhythm::AttackEnd))/R.AttackRate;
    R.BaseReach=ColdSteelInventory::Number(Item,TEXT("melee_reach_cm"),180);
    R.SlashReach=RuneSwordCombatTuning::ScaledReach(R.BaseReach)*R.Modifiers.Range;
    R.ThrustReach=RuneSwordCombatTuning::ScaledReach(R.BaseReach,RuneSwordThrustRhythm::ReachBonus)*R.Modifiers.Range;
    if(Item.Definition==TEXT("ue_highland_claymore")&&Parts.FindRef(TEXT("blade_1"))==TEXT("highland_ridge_piercer"))
    {
        R.ThrustSeconds=HighlandRidgeThrust::ToWall(HighlandRidgeThrust::CounterLead+HighlandRidgeThrust::ReleaseSeconds,
            HighlandRidgeThrust::CounterLead,R.AttackRate*HighlandRidgeThrust::FinisherPlaybackRate);
        R.ThrustReach*=HighlandRidgeThrust::ReachScale;
    }
    if(ColdSteelInventory::IsOneHandedMelee(Item))
    {
        // The kukri executor consumes its own blade reach, without the sword's scale.
        R.BaseReach*=R.Modifiers.Range;
        R.SlashReach=R.BaseReach;
        R.ThrustReach=R.BaseReach;
    }
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
    const auto* Tool=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* Item=Tool?Tool:SwordUppercutWeapon::Resolve(Profile);
    if(!Item||(!PojunGrip::UsesHammerMotion(*Item)&&!SwordUppercutWeapon::Supports(Profile,Item)))return 0.;
    if(Tool)return Evaluate(*Item,Profile).ThrustReach*Profile->MasteryEffect(TEXT("swordUppercut"),Level).UppercutReachMultiplier;
    const double BaseReach=ColdSteelInventory::Number(*Item,TEXT("melee_reach_cm"),180);
    const auto Modifiers=EquippedModifiers(Profile);
    // The kukri's uppercut reaches from its plain blade reach (KukriUppercut.cpp BeginUppercut).
    if(ColdSteelInventory::IsOneHandedMelee(*Item)||SwordUppercutWeapon::IsStaffBlade(Profile,Item))
    {
        const auto Stats=Evaluate(*Item,Profile);
        return Stats.BaseReach*Profile->MasteryEffect(TEXT("swordUppercut"),Level).UppercutReachMultiplier*Stats.Modifiers.MartialRange;
    }
    const double ThrustReach=RuneSwordCombatTuning::ScaledReach(BaseReach,RuneSwordThrustRhythm::ReachBonus)*Modifiers.Range;
    return ThrustReach*Profile->MasteryEffect(TEXT("swordUppercut"),Level).UppercutReachMultiplier*Modifiers.MartialRange;
}

double ColdSteelMelee::BlockStamina(const FMeleeModifiers& Modifiers,const UColdSteelStatusModel* Profile)
{
    return RuneSwordGuardTuning::BlockStamina*Modifiers.BlockStamina*(Profile?Profile->ActionStaminaMultiplier():1.f);
}

FMeleeModifiers ColdSteelMelee::ItemModifiers(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile)
{
    const auto* GI=Profile?Profile->GetGameInstance():nullptr;
    const auto* G=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    auto Result=Item&&G?G->Calculate(Item->Definition,G->Installed(*Item)).Melee:FMeleeModifiers{};
    if(Item)Result.CriticalChanceAdd+=KukriEnchantment::CriticalChanceAdd(*Item);
    if(Item&&Profile&&ColdSteelInventory::IsOneHandedMelee(*Item)&&!ColdSteelInventory::IsWoodenTorch(*Item))
        Result.CriticalChanceAdd+=Profile->MasteryEffect(TEXT("oneHandedMastery")).CriticalChance;
    if(UKukriBerserkerComponent::Active(Item,Profile))Result.Stamina=0.;
    return Result;
}

const FColdSteelItem* ColdSteelMelee::PairedOneHandedWeapon(const FColdSteelItem* Main,const UColdSteelStatusModel* Profile)
{
    const auto* Active=Profile?Profile->Equipped():nullptr;
    if(!Main||!Active||Main->InstanceId!=Active->InstanceId||Profile->ActiveProductionTool()||
        !(ColdSteelInventory::IsOneHandedMelee(*Main)||KukriEnchantment::Supports(*Main)||ColdSteelInventory::IsDualPistol(*Main)||ColdSteelInventory::UsesStaffMelee(*Main)))return nullptr;
    const auto* First=Profile->Equipped(6);
    const auto* Off=Profile->Equipped(First&&First->InstanceId==Main->InstanceId?8:11);
    return Off&&!ColdSteelInventory::IsWoodenTorch(*Off)&&Off->InstanceId!=Main->InstanceId&&
        (ColdSteelInventory::IsOneHandedMelee(*Off)||KukriEnchantment::Supports(*Off))?Off:nullptr;
}

FMeleeModifiers ColdSteelMelee::QuickCombatModifiers(const UColdSteelStatusModel* Profile)
{
    const auto* Tool=Profile?Profile->ActiveProductionTool():nullptr;
    // (Main hand empty: the lone off-hand kukri / hatchet strikes.)
    const auto* Item=Tool?Tool:Profile?Profile->ActiveKukriWeapon():nullptr;
    if(!Tool&&Item&&(ColdSteelInventory::IsDualPistol(*Item)||ColdSteelInventory::UsesStaffMelee(*Item)))Item=PairedOneHandedWeapon(Item,Profile);
    return Item&&(ColdSteelInventory::IsMeleeWeapon(*Item)||ColdSteelInventory::IsTwoHandedBlunt(*Item))?
        ItemModifiers(Item,Profile):FMeleeModifiers{};
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

double ColdSteelMelee::AttackStamina(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile,const FMeleeModifiers* PreviewModifiers,bool NormalAttack)
{
    // An explicitly free attack bypasses the ordinary stamina reduction floor.
    if(UKukriBerserkerComponent::Active(Item,Profile)||UEagleTalonGuardComponent::Ready(Profile,Item))return 0.;
    // The HUD attack count and the staff executor share ordinary punch cost.
    if(Item&&ColdSteelInventory::UsesStaffMelee(*Item))return UnarmedAttackStamina(Profile);
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
    // A catalog cost is the weapon's complete base cost, after handedness and
    // before equipment/parts. Profile refresh and network sanitization own this field.
    if(Item)Base=FMath::Max(0.,ColdSteelInventory::Number(*Item,TEXT("melee_stamina"),Base));
    if(Item&&ColdSteelInventory::IsMeleeWeapon(*Item))
    {
        const auto Modifiers=PreviewModifiers?*PreviewModifiers:Gunsmith?
            Gunsmith->Calculate(Item->Definition,Gunsmith->Installed(*Item)).Melee:FMeleeModifiers{};
        return ModifiedAttackStamina(Base,Modifiers.Stamina*(NormalAttack?Modifiers.NormalAttackStamina:1.),TemporaryModifiers(Profile).Stamina,Profile);
    }
    return ModifiedAttackStamina(Base,1.,1.,Profile);
}

double ColdSteelMelee::ComboAttackStamina(const FColdSteelItem* Main,const UColdSteelStatusModel* Profile,bool BothBlades,bool NormalAttack)
{
    const double MainCost=AttackStamina(Main,Profile,nullptr,NormalAttack);
    // Preserve the existing combined action's base cost, billing each blade's half
    // through its own equipment/modifier/floor calculation. Never multiply the two.
    const auto* Off=BothBlades?PairedOneHandedWeapon(Main,Profile):nullptr;
    return Main&&ColdSteelInventory::IsOneHandedMelee(*Main)&&Off?
        .5*MainCost+.5*AttackStamina(Off,Profile,nullptr,NormalAttack):MainCost;
}

double ColdSteelMelee::HeavyChargeSeconds(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,bool BothBlades)
{
    const auto* Off=BothBlades&&ColdSteelInventory::IsOneHandedMelee(Item)?PairedOneHandedWeapon(&Item,Profile):nullptr;
    if(!Off)return Evaluate(Item,Profile).HeavyChargeSeconds;

    const auto* GI=Profile->GetGameInstance();
    const auto* Gunsmith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    const FGunsmithParts MainParts=Gunsmith?Gunsmith->Installed(Item):FGunsmithParts{};
    const FGunsmithParts OffParts=Gunsmith?Gunsmith->Installed(*Off):FGunsmithParts{};
    const double MainSeconds=Evaluate(Item,Profile,&MainParts).HeavyChargeSeconds;
    const double OffSeconds=Evaluate(*Off,Profile,&OffParts).HeavyChargeSeconds;
    const double PairedSeconds=(MainSeconds+OffSeconds)*.5;
    const TCHAR* YanguId=TEXT("knife_pommel_yangu");
    const bool bDualYangu=MainParts.FindRef(TEXT("pommel"))==YanguId && OffParts.FindRef(TEXT("pommel"))==YanguId;
    return bDualYangu ? PairedSeconds/1.10 : PairedSeconds;
}

double ColdSteelMelee::HeavyReleaseStamina(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile,bool BothBlades)
{
    // Pay for both Chixiao cuts once on release, after all ordinary cost modifiers.
    return ComboAttackStamina(Item,Profile,BothBlades,false)*(Item&&ColdSteelModularSword::UsesChixiaoDoubleHeavy(*Item)?2.:1.);
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
