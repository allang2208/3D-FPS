#pragma once
#include "CoreMinimal.h"

namespace ColdSteelFrostRunes
{
    inline constexpr const TCHAR* Definition=TEXT("ue_frost_crystal_sword");
    inline constexpr const TCHAR* SpiritBurst=TEXT("spirit_burst_rune");
    inline constexpr const TCHAR* TangDao=TEXT("ue_tang_dao");
    inline constexpr const TCHAR* XuanChi=TEXT("ue_xuanchi_zhenyue");
    inline constexpr const TCHAR* AuspiciousCloud=TEXT("auspicious_cloud_rune");
    inline constexpr const TCHAR* CloudMask=TEXT("/Game/Weapons/TangDao20261002/CloudRune20261002/Textures/T_Mask_auspicious_cloud_rune");
    inline constexpr const TCHAR* Jingang=TEXT("jingang_rune");
    inline constexpr const TCHAR* JingangMask=TEXT("/Game/Weapons/XuanChiZhenYue20261004/JingangRune20261006/Textures/T_Mask_jingang_rune");
    inline constexpr const TCHAR* Zhenmo=TEXT("zhenmo_rune");
    inline constexpr const TCHAR* ZhenmoMask=TEXT("/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Textures/T_Mask_zhenmo_rune");
    inline constexpr const TCHAR* Mountain=TEXT("mountain_rune");
    inline constexpr const TCHAR* MountainMask=TEXT("/Game/Weapons/TangDao20261002/MountainRune20261004/Textures/T_Mask_mountain_rune");
    inline bool SupportsEasternRunes(const FString& Weapon)
    {
        return Weapon==TangDao||Weapon==XuanChi;
    }
    // Shared by catalog normalization, saved items and every sword visual.
    inline FString Upgrade(const FString& Weapon,const FString& Rune)
    {
        if((Rune==Zhenmo||Rune==Jingang)&&Weapon!=XuanChi)return {};
        if(Rune==TEXT("golden_glow_rune")&&Weapon!=TEXT("ue_rune_sword"))return {};
        if((Rune==AuspiciousCloud||Rune==Mountain)&&!SupportsEasternRunes(Weapon))return {};
        // Preserve the player's installed upgrade when erosion becomes innate.
        return Weapon==Definition&&Rune==TEXT("erosion_rune")?FString(SpiritBurst):Rune;
    }
}
