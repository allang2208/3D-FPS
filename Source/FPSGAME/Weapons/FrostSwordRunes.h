#pragma once
#include "CoreMinimal.h"

namespace ColdSteelFrostRunes
{
    inline constexpr const TCHAR* Definition=TEXT("ue_frost_crystal_sword");
    inline constexpr const TCHAR* SpiritBurst=TEXT("spirit_burst_rune");
    // Shared by catalog normalization, saved items and every sword visual.
    inline FString Upgrade(const FString& Weapon,const FString& Rune)
    {
        if(Rune==TEXT("golden_glow_rune")&&Weapon!=TEXT("ue_rune_sword"))return {};
        // Preserve the player's installed upgrade when erosion becomes innate.
        return Weapon==Definition&&Rune==TEXT("erosion_rune")?FString(SpiritBurst):Rune;
    }
}
