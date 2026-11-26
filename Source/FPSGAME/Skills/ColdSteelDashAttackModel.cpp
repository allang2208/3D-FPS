#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/PojunGrip.h"
#include "ColdSteelSkillRules.h"
#include "ColdSteelSpellRewards.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"

void ColdSteelSkills::CapturePairedDash(FColdSteelSkillShot& Shot,AActor* Shooter,const UColdSteelStatusModel* Profile)
{
    Shot.PairedDashMainPhysical={};Shot.PairedDashOffPhysical={};Shot.PairedDashOffPenetration=0.f;
    Shot.bPairedDashOffGhostScythe=false;
    const auto* Main=Profile?Profile->Equipped():nullptr;
    if(Shot.AttackMeta!=0x16||!Main||Main->InstanceId!=Shot.ItemInstance||!ColdSteelInventory::IsOneHandedMelee(*Main))return;
    const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,Profile);if(!Off)return;
    const auto MainMods=ColdSteelMelee::ItemModifiers(Main,Profile);
    const auto OffMods=ColdSteelMelee::ItemModifiers(Off,Profile);
    const auto Other=ColdSteelSkills::Snapshot(Shooter,Off);
    Shot.PairedDashMainPhysical={Shot.DamagePanel.BasePhysical*MainMods.MartialDamage,0.,Shot.DamagePanel.AddedPhysical*MainMods.MartialDamage,0.};
    Shot.PairedDashOffPhysical={Other.DamagePanel.BasePhysical*OffMods.MartialDamage,0.,Other.DamagePanel.AddedPhysical*OffMods.MartialDamage,0.};
    Shot.PairedDashOffPenetration=Other.ArmorPenetration;
    Shot.bPairedDashOffGhostScythe=Other.bGhostScytheContact;
}

FDashAttackCast UColdSteelStatusModel::DashAttackStats(int32 AtLevel) const
{
    const auto& D=MasteryDefinition(TEXT("dashAttack"));const auto& T=D.DashAttack;
    const int32 L=FMath::Clamp(AtLevel<0?MasteryProgress(D.Id).Level:AtLevel,1,D.MaxLevel);
    FDashAttackCast C;
    C.DamageMultiplier=T.DamageBase+L*T.DamagePerLevel;
    C.ReadySeconds=FMath::Max(.01f,T.ReadySeconds*(1.f-(L-1)*T.ReadyReductionPerLevel));
    C.StaminaCost=T.StaminaCost;
    C.DistanceCM=FMath::Max(0.f,T.Distance); // 距离直接使用厘米，不套用旧版范围换算。
    C.RangeBonusCM=(T.RangeBase+L*T.RangePerLevel+T.RangeFlat)*T.UnitsToCM;
    C.KnockbackBonusCM=(T.KnockbackBonus+L*T.KnockbackPerLevel)*T.UnitsToCM;
    // 扇区宽度由 skills.json:arcDegrees 配置（当前 45°）；限幅防止旧缓存值回灌。
    C.ArcDegrees=FMath::Clamp(T.ArcDegrees,10.f,90.f);
    // The main hand's weapon, or -- main hand empty -- the lone off-hand kukri / hatchet that acts alone (2026-11-04).
    // Client cast and authority (ColdSteelPlayerState 0x16 damage and range) read this same function.
    const auto* Tool=ActiveProductionTool();
    const bool ZhufengTool=Tool&&PojunGrip::Attack(*Tool,false,true,2)==PojunGrip::EAttack::Zhufeng;
    const auto* Item=ZhufengTool?Tool:ActiveKukriWeapon();
    if(Item&&(!Tool||ZhufengTool)&&ColdSteelInventory::IsMeleeWeapon(*Item))
    {
        const auto Stats=ColdSteelMelee::Evaluate(*Item,this);
        const auto* Enhance=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
        const auto WeaponCost=[&](const FColdSteelItem& Weapon,const FMeleeModifiers& Mods)
        {
            const double Delta=Enhance?Enhance->CraftEffect(Weapon,TEXT("skillStaminaCostDelta")):0.;
            return FMath::Max(0.,(T.StaminaCost+Delta)*Mods.Stamina);
        };
        double Cost=WeaponCost(*Item,Stats.Modifiers);
        C.ToughnessMultiplier=float(Stats.Modifiers.ToughnessDamage);
        // Dual kukri (a one-handed melee in the active slot and another in its paired off-hand slot -- the pair
        // UKukriWeaponComponent::RefreshOffhand presents as two blades; user 2026-10-26): the sprint attack's base is the sum
        // of both weapons' physical panels (base + added), then the same skill formula.  The authority's 0x16 branch reads
        // this same function on the shadow profile, so client and server agree.
        double Base=Stats.Damage;
        double MartialDamage=Stats.Modifiers.MartialDamage;
        if(const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Item,this);
            Off&&ColdSteelInventory::IsOneHandedMelee(*Item))
        {
            const auto OffStats=ColdSteelMelee::Evaluate(*Off,this);
            const double Right=(Stats.DamageParts.BasePhysical+Stats.DamageParts.AddedPhysical)*Stats.Modifiers.MartialDamage;
            const double Left=(OffStats.DamageParts.BasePhysical+OffStats.DamageParts.AddedPhysical)*OffStats.Modifiers.MartialDamage;
            Base=Right+Left;MartialDamage=1.;
            if(Base>0.)C.ToughnessMultiplier=float((Right*Stats.Modifiers.ToughnessDamage+Left*OffStats.Modifiers.ToughnessDamage)/Base);
            // One combined skill bill: split its base between the participating blades, then apply each blade's mods.
            Cost=.5*Cost+.5*WeaponCost(*Off,OffStats.Modifiers);
        }
        C.Damage=FMath::FloorToFloat(Base*C.DamageMultiplier)*MartialDamage;
        // SlashReach already includes this weapon family's reach scale and Range once.
        // A short blade stays short for the dash; apply Range only to the skill's extra reach.
        C.RangeCM=(Stats.SlashReach+C.RangeBonusCM*Stats.Modifiers.Range)*Stats.Modifiers.MartialRange;
        if(HighlandRidgeThrust::Installed(GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Item))
        {
            // Owner execution, skill preview and server movement authorization
            // all consume this snapshot. Extend travel, not the blade rectangle.
            C.DistanceCM*=HighlandRidgeThrust::DashDistanceScale;
            C.Damage*=HighlandRidgeThrust::StrikeDamageScale;
            C.DamageMultiplier*=HighlandRidgeThrust::StrikeDamageScale;
            C.RangeCM*=HighlandRidgeThrust::ReachScale;
            C.RectangleWidthCM=2.f*HighlandRidgeThrust::HalfWidthCM;
        }
        C.KnockbackBonusCM*=Stats.Modifiers.AllAttackKnockback;
        C.KnockbackCM=Stats.KnockbackCM+C.KnockbackBonusCM;
        C.StaminaCost=float(Cost*ColdSteelMelee::TemporaryModifiers(this).Stamina);
    }
    C.StaminaCost=UEagleTalonGuardComponent::Ready(this)?0.f:C.StaminaCost*ActionStaminaMultiplier();
    return C;
}

void UColdSteelStatusModel::TrainDashAttack(int32 Hits,int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("dashAttack"));
    const int32 XP=ColdSteelSpellRewards::MartialHitTrainingExperience(D,Hits,Kills);
    if(XP<=0||MasteryProgress(D.Id).Level>=D.MaxLevel)return;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);StageTraining(MoveTemp(P));
}
