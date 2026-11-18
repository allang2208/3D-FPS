#pragma once

#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatItemFormula.h"
#include "../Combat/CombatStatusFormula.h"
#include "Dom/JsonObject.h"
#include "GameFramework/Pawn.h"

namespace ColdSteelSpellCrafting
{
inline int32 ChainSpellStacks(const APawn* Pawn)
{
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    return Status?Status->ChainSpellStacks():0;
}

inline bool HasStaffSpecialty(const FColdSteelItem& Item,const TCHAR* Expected)
{
    const auto Data=CombatItemFormula::ReadOnly(Item);
    const TSharedPtr<FJsonObject>* Effects=nullptr;FString Specialty;
    return Data&&Data->TryGetObjectField(TEXT("_craftEffects"),Effects)
        &&(*Effects)->TryGetStringField(TEXT("staffSpecialty"),Specialty)&&Specialty==Expected;
}

// Keep both float assignments: combining the products changes intermediate rounding.
inline void ApplyCooldownMultipliers(float& Cooldown,double CooldownReduction,
    double SetCooldownReduction,double RuneMultiplier)
{
    Cooldown*=FMath::Max(.2,double(1-CooldownReduction)*(1-SetCooldownReduction));
    Cooldown*=RuneMultiplier;
}

// Buff cooldowns keep float reduction math, then left-to-right double rune products.
inline double AuraCooldownMultiplier(float CooldownReduction,float SetCooldownReduction,
    double SkillCooldown,double MagicCooldown)
{
    return FMath::Max(.2f,(1-CooldownReduction)*(1-SetCooldownReduction))*SkillCooldown*MagicCooldown;
}

// The caller retains staff eligibility and the position of each group of reads.
template <typename TCast>
inline void ApplyCriticalStats(TCast& Spell,const UColdSteelEnhancementSystem& Enhancement,
    const FColdSteelItem& Item)
{
    Spell.CriticalChance+=100*(Enhancement.Effect(Item,TEXT("critRate"))
        +Enhancement.CraftEffect(Item,TEXT("critChancePercent"))
        +Enhancement.CraftEffect(Item,TEXT("magicCritPercent")));
    Spell.MagicPenetration=Enhancement.Effect(Item,TEXT("magicPenetrationPercent"))
        +Enhancement.CraftEffect(Item,TEXT("magicPenetrationPercent"));
}

template <typename TCast>
inline void ApplyChainAndCastHaste(TCast& Spell,const UColdSteelEnhancementSystem& Enhancement,
    const FColdSteelItem& Item)
{
    Spell.bGrantChain=Enhancement.CraftEffect(Item,TEXT("chainSpellDamagePercent"))!=0;
    Spell.CastHasteStacks=Enhancement.CraftEffect(Item,TEXT("castHasteStacks"));
    Spell.CastHasteDuration=Enhancement.CraftEffect(Item,TEXT("castHasteDuration"),5000)/1000;
}
}
