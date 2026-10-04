#pragma once
#include "CoreMinimal.h"

namespace ColdSteelFrostRunes
{
    inline constexpr const TCHAR* Definition=TEXT("ue_frost_crystal_sword");
    inline constexpr const TCHAR* SpiritBurst=TEXT("spirit_burst_rune");
    inline constexpr const TCHAR* TangDao=TEXT("ue_tang_dao");
    inline constexpr const TCHAR* AuspiciousCloud=TEXT("auspicious_cloud_rune");
    inline constexpr const TCHAR* CloudMask=TEXT("/Game/Weapons/TangDao20261002/CloudRune20261002/Textures/T_Mask_auspicious_cloud_rune");
    inline constexpr const TCHAR* Mountain=TEXT("mountain_rune");
    inline constexpr const TCHAR* MountainMask=TEXT("/Game/Weapons/TangDao20261002/MountainRune20261004/Textures/T_Mask_mountain_rune");
    // Shared by catalog normalization, saved items and every sword visual.
    inline FString Upgrade(const FString& Weapon,const FString& Rune)
    {
        if(Rune==TEXT("golden_glow_rune")&&Weapon!=TEXT("ue_rune_sword"))return {};
        if(Rune==AuspiciousCloud&&Weapon!=TangDao)return {};
        if(Rune==Mountain&&Weapon!=TangDao)return {};
        // Preserve the player's installed upgrade when erosion becomes innate.
        return Weapon==Definition&&Rune==TEXT("erosion_rune")?FString(SpiritBurst):Rune;
    }
}
