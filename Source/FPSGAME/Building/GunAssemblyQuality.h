#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FColdSteelGunAssemblyJob;

namespace ColdSteelAssemblyQuality
{
    constexpr int32 Version=2;
    constexpr double MaxMaterialBonus=.10;
    constexpr double MaxSkillBonus=.15;
    double Score(const FColdSteelGunAssemblyJob& Job);
    double SkillBonus(double Score);
    double MaterialBonus(const FColdSteelGunAssemblyJob& Job);
    double MaterialBonus(const FColdSteelItem& Item);
    double Multiplier(const FColdSteelGunAssemblyJob& Job);
    double Multiplier(const FColdSteelItem& Item);
    bool Apply(FColdSteelItem& Item,const FColdSteelGunAssemblyJob& Job);
    void PreserveAuthoritative(TArray<FColdSteelItem>& Incoming,const TArray<FColdSteelItem>& Authority);
}
