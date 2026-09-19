#pragma once
#include "GunsmithSystem.h"
namespace ColdSteelMeleeGuard
{
    FString Selected(const FColdSteelItem& Item,const FGunsmithParts* Preview=nullptr);
    FString WorldMesh(const FColdSteelItem& Item,const FGunsmithParts* Preview=nullptr);
    FString Viewmodel(const FColdSteelItem& Item);
}
