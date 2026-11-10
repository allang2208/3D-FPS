#include "CombatControlImmunity.h"
#include "CombatStatusFormula.h"
#include "../Production/ProductionToolComponent.h"
#include "GameFramework/Actor.h"

bool CombatControl::IsImmune(const AActor* Target)
{
    if(!Target)return false;
    if(const auto* Status=Target->FindComponentByClass<UCombatStatusFormula>();Status&&Status->IsImmune())return true;
    const auto* Tool=Target->FindComponentByClass<UProductionToolComponent>();
    return Tool&&Tool->IsLeapControlImmune();
}
