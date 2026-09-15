#include "DevelopmentTuningSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"

bool UColdSteelStatusModel::HasInfiniteMana() const
{
    const auto* Tuning = UDevelopmentTuningSubsystem::Find(this);
    return Tuning && Tuning->IsEnabled(EDevelopmentTuningOption::InfiniteMana);
}

bool UColdSteelStatusModel::HasNoAbilityCooldown() const
{
    const auto* Tuning = UDevelopmentTuningSubsystem::Find(this);
    return Tuning && Tuning->IsEnabled(EDevelopmentTuningOption::NoAbilityCooldown);
}

float UColdSteelStatusModel::Mana() const
{
    return HasInfiniteMana() ? Derived(TEXT("maxMp")) : Current.Mana;
}

bool UColdSteelStatusModel::CanSpendMana(float Amount) const
{
    return Amount >= 0.f && (HasInfiniteMana() || Current.Mana >= Amount);
}

float UColdSteelStatusModel::FireballCooldown() const
{
    return HasNoAbilityCooldown() ? 0.f : Current.FireballCooldown;
}

void UColdSteelStatusModel::RefreshDevelopmentTuning()
{
    if (HasNoAbilityCooldown()) Current.FireballCooldown = 0.f;
    if (HasNoAbilityCooldown()) Current.IceSpikeCooldown = 0.f;
    OnChanged.Broadcast();
}
