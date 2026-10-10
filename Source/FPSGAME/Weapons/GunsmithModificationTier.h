#pragma once
#include "CoreMinimal.h"
#include "RSH12OpticAssets.h"
#include "TacticalDeviceVariants.h"
#include "LegendaryTacticalStock.h"

enum class EGunsmithModificationTier : uint8 { Common, Special, Legendary };
namespace ColdSteelModification
{
inline EGunsmithModificationTier Tier(const FString& Weapon,const FString& SlotKey,const FString& Id)
{
    if(SlotKey==TEXT("stock")&&Id==LegendaryTacticalStock::Part)
        return EGunsmithModificationTier::Legendary;
    if(SlotKey==TEXT("tactical")&&Id==TacticalDeviceVariants::BlessedLaser)
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_xuanchi_zhenyue")&&SlotKey==TEXT("blade_2")&&(Id==TEXT("zhenmo_rune")||Id==TEXT("jingang_rune")))
        return EGunsmithModificationTier::Legendary;
    const bool VipGrip=Weapon==TEXT("ue_pit_viper2011")&&SlotKey==TEXT("reargrip")&&Id==TEXT("pit_viper_vip_scales");
    const bool SiMuzzle=Weapon==TEXT("ue_pit_viper2011")&&SlotKey==TEXT("muzzle")&&Id==TEXT("pit_viper_si_compensator");
    const bool G18Drum=Weapon==TEXT("ue_g18")&&SlotKey==TEXT("magazine")&&Id==TEXT("g18_drum_50");
    const bool Special=
        VipGrip || SiMuzzle || G18Drum ||
        ((Weapon==TEXT("ue_frost_crystal_sword")||Weapon==TEXT("ue_rune_sword")) &&
            SlotKey==TEXT("pommel") && (Id==TEXT("pommel_mana_orb")||Id==TEXT("ballast_rune"))) ||
        (Weapon==TEXT("ue_xuanchi_zhenyue") && SlotKey==TEXT("guard") && Id==TEXT("panchi_zhanyue")) ||
        (Weapon==TEXT("ue_rsh12") && SlotKey==TEXT("muzzle") &&
            (Id==TEXT("rsh12_heavy_suppressor")||Id==TEXT("rsh12_large_caliber_brake"))) ||
        (Weapon==TEXT("ue_rsh12") && SlotKey==TEXT("grip_body") && (Id==TEXT("rsh12_heavy_grip")||Id==TEXT("rsh12_quickdraw_grip"))) ||
        (Weapon==TEXT("ue_rsh12") && SlotKey==TEXT("optic") && RSH12OpticAssets::IsSquare(Id)) ||
        ((Weapon==TEXT("ue_tang_dao")||Weapon==TEXT("ue_xuanchi_zhenyue")) &&
            ((SlotKey==TEXT("blade_1") && (Id==TEXT("yanling_edge")||Id==TEXT("tengyun_dragon"))) ||
             (SlotKey==TEXT("blade_2") && (Id==TEXT("auspicious_cloud_rune")||Id==TEXT("mountain_rune"))) ||
             (SlotKey==TEXT("guard") && (Id==TEXT("xuan_cloud_dragon")||Id==TEXT("phoenix_feather"))) ||
             (SlotKey==TEXT("pommel") && (Id==TEXT("yanling_breaker")||Id==TEXT("tiger_mountain"))))) ||
        (Weapon==TEXT("ue_highland_claymore") &&
            ((SlotKey==TEXT("blade_1") && (Id==TEXT("highland_broadblade")||Id==TEXT("highland_ridge_piercer"))) ||
             (SlotKey==TEXT("blade_2") && Id==TEXT("wild_rune")) ||
             (SlotKey==TEXT("guard") && Id==TEXT("highland_cloven_guard")) ||
             (SlotKey==TEXT("pommel") && Id==TEXT("highland_thorn_crown")))) ||
        (Weapon==TEXT("ue_frost_crystal_sword") && SlotKey==TEXT("blade_2") && Id==TEXT("spirit_burst_rune")) ||
        (Weapon==TEXT("ue_rune_sword") && SlotKey==TEXT("blade_2") && Id==TEXT("golden_glow_rune")) ||
        (Weapon==TEXT("ue_ash12") &&
            ((SlotKey==TEXT("muzzle") && (Id==TEXT("ash12_tactical_suppressor")||Id==TEXT("ash12_tactical_brake"))) ||
             (SlotKey==TEXT("stock") && Id==TEXT("ash12_cheek_rest"))));
    return Special?EGunsmithModificationTier::Special:EGunsmithModificationTier::Common;
}
inline const TCHAR* Label(EGunsmithModificationTier Tier)
{
    return Tier==EGunsmithModificationTier::Legendary?TEXT("传说级改造"):
        Tier==EGunsmithModificationTier::Special?TEXT("特殊改造"):TEXT("通用改造");
}
}
