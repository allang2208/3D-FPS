#pragma once
#include "CoreMinimal.h"
#include "../UI/ColdSteelInventoryTypes.h"
class UColdSteelStatusModel;

/** Shared post-processing for runtime weapons and read-only item inspectors. */
namespace ColdSteelWeaponStats
{
    double Damage(const FColdSteelItem& Item,const UColdSteelStatusModel* Model,double WeaponBase);
    double Interval(const FColdSteelItem* Item,const UColdSteelStatusModel* Model,double WeaponBase);
    double Reload(const UColdSteelStatusModel* Model,double WeaponBase);
    FString AmmoName(const FString& Definition);
    // M4 combat still uses the character class defaults for damage/fire interval.
    double NativeM4Base(const UColdSteelStatusModel* Model,const TCHAR* Property);
}
