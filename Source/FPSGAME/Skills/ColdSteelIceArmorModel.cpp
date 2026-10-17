#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Combat/CombatStatusFormula.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "Engine/GameInstance.h"

FIceArmorCast UColdSteelStatusModel::IceArmorStats(int32 AtLevel) const
{
    const auto& T=IceArmorSkill.IceArmor;
    const int32 L=FMath::Clamp(AtLevel<0?MasteryProgress(TEXT("iceArmor")).Level:AtLevel,1,IceArmorSkill.MaxLevel);
    const float K=L-1,G=K/FMath::Max(1,IceArmorSkill.MaxLevel-1),M=Derived(TEXT("matk"));
    FIceArmorCast C;C.PhysicalDefense=FMath::FloorToFloat(T.PhysicalBase+K*T.PhysicalPerLevel+M*T.PhysicalMagic);
    C.MagicDefense=FMath::FloorToFloat(T.MagicBase+K*T.MagicPerLevel+M*T.MagicMagic);
    C.Duration=T.DurationBase+FMath::FloorToFloat(T.DurationGrowth*G);C.Radius=T.RadiusBase+G*T.RadiusGrowth;
    C.PulseSeconds=T.PulseSeconds;C.ChillSeconds=T.ChillSeconds+G*T.ChillGrowth;C.SlowPerStack=T.SlowPerStack;
    C.Cooldown=T.Cooldown-FMath::FloorToFloat(T.CooldownReduction*G);C.ManaCost=SpellManaCostBeforeFocus(TEXT("iceArmor"),L);
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);float Reduction=0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {Reduction=E->CraftEffect(*Item,TEXT("magicCooldownPercent"));C.CastSpeed=FMath::Max(.1f,1.f+float(E->CraftEffect(*Item,TEXT("castSpeedPercent"))));}
    C.Cooldown*=FMath::Max(.2f,(1-Reduction)*(1-float(SetEffect(TEXT("cooldown")))))*Rune.SkillCooldown*Rune.MagicCooldown;
    ApplySpellbookFocus(C.CastSpeed,C.ManaCost);
    C.CastExperience=T.CastExperience;C.MeleeExperience=T.MeleeExperience;C.RangedExperience=T.RangedExperience;C.ExperienceCap=T.ExperienceCap;C.TrainingSourceInterval=T.TrainingSourceInterval;
    return C;
}
bool UColdSteelStatusModel::BeginIceArmorCast(const FIceArmorCast& Spell)
{
    if(IceArmorCooldown()>0||!CanSpendMana(Spell.ManaCost))return false;
    if(const auto* P=RuntimePawn())if(const auto* S=P->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune())return false;
    SyncRuntime();auto P=Snapshot();if(!HasInfiniteMana())P.Mana-=Spell.ManaCost;
    P.IceArmorCooldown=P.IceArmorCooldownDuration=HasNoAbilityCooldown()?0.f:Spell.Cooldown;return CommitState(MoveTemp(P));
}
void UColdSteelStatusModel::FinishIceArmorTraining(int32 Experience)
{
    if(Experience<=0)return;SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,IceArmorSkill,Experience);StageTraining(MoveTemp(P));
}
