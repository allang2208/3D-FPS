#pragma once
#include "../UI/ColdSteelInventoryTypes.h"
#include "Dom/JsonObject.h"
namespace CombatItemFormula
{
    TSharedPtr<FJsonObject> Read(const FColdSteelItem& Item);
    // Same catalog defaults; immutable result reused until definition or payload changes.
    TSharedPtr<const FJsonObject> ReadOnly(const FColdSteelItem& Item);
}
