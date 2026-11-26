#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Combat/CombatStatusFormula.h"
#include "../FPSGAMECharacter.h"
#include "FPSLightningHasteComponent.h"
#include "ColdSteelSkillRules.h"
#include "ColdSteelSpellCrafting.h"
#include "Engine/GameInstance.h"

FLightningHasteCast UColdSteelStatusModel::LightningHasteStats(int32 AtLevel) const
{
    const auto& T=LightningHasteSkill.LightningHaste;
    const int32 L=FMath::Clamp(AtLevel<0?MasteryProgress(TEXT("lightningHaste")).Level:AtLevel,1,LightningHasteSkill.MaxLevel);
    const float K=L-1;
    FLightningHasteCast C;C.MoveBonus=T.MoveBase+K*T.MovePerLevel;C.ActionBonus=T.ActionBase+K*T.ActionPerLevel;
    C.Duration=T.DurationBase+K*T.DurationPerLevel;C.Cooldown=T.Cooldown;C.ManaCost=SpellManaCost(TEXT("lightningHaste"),L);
    float Reduction=0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {Reduction=E->CraftEffect(*Item,TEXT("magicCooldownPercent"));C.CastSpeed=FMath::Max(.1f,1.f+float(E->CraftEffect(*Item,TEXT("castSpeedPercent"))));}
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.Cooldown*=ColdSteelSpellCrafting::AuraCooldownMultiplier(Reduction,float(SetEffect(TEXT("cooldown"))),
        Rune.SkillCooldown,Rune.MagicCooldown);
    ApplySpellCastSpeed(C.CastSpeed);
    C.CastExperience=T.CastExperience;C.KillExperience=T.KillExperience;C.Kill6Bonus=T.Kill6Bonus;C.Kill11Bonus=T.Kill11Bonus;
    return C;
}
bool UColdSteelStatusModel::BeginLightningHasteCast(const FLightningHasteCast& Spell)
{
    if(LightningHasteCooldown()>0||!CanSpendMana(Spell.ManaCost))return false;
    if(const auto* P=RuntimePawn())
    {
        if(const auto* A=P->FindComponentByClass<UFPSLightningHasteComponent>();A&&A->Remaining()>0)return false;
        if(const auto* S=P->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune())return false;
    }
    SyncRuntime();auto P=Snapshot();if(!HasInfiniteMana())P.Mana-=Spell.ManaCost;
    // Reserve the cooldown with payment; release restarts its full duration.
    P.LightningHasteCooldown=P.LightningHasteCooldownDuration=HasNoAbilityCooldown()?0.f:Spell.Cooldown;
    return CommitState(MoveTemp(P));
}
void UColdSteelStatusModel::CommitLightningHasteCast(const FLightningHasteCast& Spell)
{
    SyncRuntime();auto P=Snapshot();
    P.LightningHasteCooldown=P.LightningHasteCooldownDuration=HasNoAbilityCooldown()?0.f:Spell.Cooldown;
    if(CommitState(MoveTemp(P)))NotifyMagicReleased();
}
void UColdSteelStatusModel::FinishLightningHasteTraining(int32 Experience)
{
    if(Experience<=0)return;SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,LightningHasteSkill,Experience);StageTraining(MoveTemp(P));
}
