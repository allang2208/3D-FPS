#pragma once
#include "CoreMinimal.h"
#include "../Weapons/PojunGrip.h"
#include "RSH12OpticAssets.h"
#include "TacticalDeviceVariants.h"
#include "LegendaryTacticalStock.h"
#include "FullAutoTrigger.h"
#include "Saiga12KMagazineAssets.h"
#include "Saiga12KSpecialStockAssets.h"
#include "SniperSuppressorAssets.h"
#include "FrostSwordRunes.h"
#include "LMGStabilityGrip.h"

enum class EGunsmithModificationTier : uint8 { Common, Special, Legendary };
namespace ColdSteelModification
{
inline bool IsSharedSpecialBowstring(const FString& Slot,const FString& Id)
{
    return Slot==TEXT("string")&&(Id==TEXT("highland_mountain_echo")||Id==TEXT("highland_cadence"));
}
inline EGunsmithModificationTier Tier(const FString& Weapon,const FString& SlotKey,const FString& Id)
{
    if(Weapon==PojunGrip::Weapon&&SlotKey==TEXT("grip")&&Id==PojunGrip::Part)return EGunsmithModificationTier::Special;
    if(SlotKey==TEXT("underbarrel")&&Id==LMGStabilityGrip::Id&&LMGStabilityGrip::Supports(Weapon))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_highland_claymore")&&SlotKey==TEXT("blade_1")&&
        (Id==TEXT("highland_broadblade")||Id==TEXT("highland_ridge_piercer")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_forged_steel_greatsword")&&SlotKey==TEXT("blade_1")&&
        (Id==TEXT("hollow_blade")||Id==TEXT("executioner_blade")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_forged_steel_greatsword")&&SlotKey==TEXT("pommel")&&
        (Id==TEXT("ring_chain_pommel")||Id==TEXT("fishtail_pommel")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_tactical_hatchet")&&SlotKey==TEXT("blade_1")&&
        (Id==TEXT("hatchet_ghost_scythe")||Id==TEXT("hatchet_falcon_edge")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_tactical_hatchet")&&SlotKey==TEXT("grip")&&
        (Id==TEXT("hatchet_grip_long")||Id==TEXT("hatchet_grip_agile")))
        return EGunsmithModificationTier::Special;
    if((Weapon==TEXT("ue_tactical_hatchet")||Weapon==TEXT("ue_kukri"))&&SlotKey==TEXT("pommel")&&
        (Id==TEXT("knife_pommel_chenheng")||Id==TEXT("knife_pommel_yangu")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_rune_sword")&&SlotKey==TEXT("blade_material")&&(Id==TEXT("time_sand_gold")||Id==TEXT("frost_crystal")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_frost_crystal_sword")&&SlotKey==TEXT("blade_material")&&
        (Id==TEXT("red_magic_crystal")||Id==TEXT("high_energy_magic_crystal")))
        return EGunsmithModificationTier::Special;
    if(SlotKey==TEXT("blade_material")&&(Id==TEXT("damascus_steel")||Id==TEXT("meteoric_iron")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_highland_claymore")&&SlotKey==TEXT("blade_material")&&
        (Id==TEXT("blackthorn_steel")||Id==TEXT("whitehart_mithril")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_tactical_hatchet")&&SlotKey==TEXT("lanyard")&&
        (Id==TEXT("hatchet_lanyard_ember_wedge")||Id==TEXT("hatchet_lanyard_raven_whistle")))return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_kukri")&&SlotKey==TEXT("lanyard")&&(Id==TEXT("kukri_lanyard_relentless")||Id==TEXT("kukri_lanyard_decisive")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_m24")&&SlotKey==TEXT("stock")&&Id==TEXT("m24_carbon_spine_stock"))
        return EGunsmithModificationTier::Special;
    if(SlotKey==TEXT("stock")&&Id==TEXT("sniper_skeleton_stock")&&
        (Weapon==TEXT("ue_m24")||Weapon==TEXT("ue_svd")||Weapon==TEXT("ue_svch")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_m24")&&SlotKey==TEXT("body")&&Id==TEXT("m24_advanced_action"))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_m24")&&SlotKey==TEXT("bolt")&&Id==TEXT("m24_carbon_light_bolt"))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_thunder_god_hammer")&&SlotKey==TEXT("head_mount")&&
        (Id==TEXT("guan_lei_seat")||Id==TEXT("ji_lei_seat")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_thunder_god_hammer")&&SlotKey==TEXT("pommel")&&
        (Id==TEXT("lei_xi_pommel")||Id==TEXT("zhen_ting_pommel")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_thunder_god_hammer")&&SlotKey==TEXT("rune")&&
        (Id==TEXT("lei_ming_rune")||Id==TEXT("hui_xiang_rune")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_thunder_god_hammer")&&SlotKey==TEXT("grip")&&(Id==TEXT("static_field_grip")||Id==TEXT("coil_grip")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_kukri")&&SlotKey==TEXT("blade_1")&&
        (Id==TEXT("hunter_blade")||Id==TEXT("canine_blade")))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("bow_frontier_compound")&&SlotKey==TEXT("riser")&&
        (Id==TEXT("frontier_eclipse")||Id==TEXT("frontier_aurora")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("bow_frontier_compound")&&SlotKey==TEXT("stabilizer")&&
        (Id==TEXT("shade_compact")||Id==TEXT("far_ridge")))
        return EGunsmithModificationTier::Special;
    if(IsSharedSpecialBowstring(SlotKey,Id))return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("bow_woodsteel")&&SlotKey==TEXT("sight")&&Id==TEXT("highland_peakwatch_3_6x"))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("bow_woodsteel")&&SlotKey==TEXT("riser")&&
        (Id==TEXT("highland_far_peak")||Id==TEXT("highland_cloudpiercer")))
        return EGunsmithModificationTier::Special;
    if(ColdSteelFrostRunes::IsWarhammer(Weapon)&&
        SlotKey==TEXT("head_mount")&&(Id==TEXT("ancient_breaking_seal_seat")||Id==TEXT("storm_drive_seat")||Id==TEXT("conical_seat")))
        return EGunsmithModificationTier::Special;
    if(Weapon==ColdSteelFrostRunes::RuneboundWarhammer&&SlotKey==TEXT("pommel")&&
        (Id==TEXT("empowered_mana_orb")||Id==TEXT("star_tide_core")))
        return EGunsmithModificationTier::Special;
    if(Weapon==ColdSteelFrostRunes::RuneboundWarhammer&&SlotKey==TEXT("rune")&&
        (Id==ColdSteelFrostRunes::SwiftMana||Id==ColdSteelFrostRunes::DestructionMana))
        return EGunsmithModificationTier::Special;
    if(SlotKey==TEXT("muzzle")&&Id==SniperSuppressorAssets::Part&&SniperSuppressorAssets::Supports(Weapon))
        return EGunsmithModificationTier::Special;
    if(SlotKey==TEXT("muzzle")&&Id==SniperSuppressorAssets::Zhiming&&SniperSuppressorAssets::SupportsZhiming(Weapon))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_rune_sword")&&SlotKey==TEXT("guard")&&(Id==TEXT("twin_star_guard")||Id==TEXT("starfall_nexus_guard")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_saiga12k")&&SlotKey==TEXT("stock")&&Id==Saiga12KSpecialStockAssets::Part)
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_saiga12k")&&SlotKey==TEXT("magazine")&&Id==Saiga12KMagazineAssets::DrumPart)
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_steel_warhammer")&&SlotKey==TEXT("hammer_heads")&&Id==TEXT("meteor_core"))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==ColdSteelFrostRunes::RuneboundWarhammer&&SlotKey==TEXT("hammer_heads")&&(Id==TEXT("star_oath_sealing_anvil")||Id==TEXT("final_toll_soul_bell")))
        return EGunsmithModificationTier::Legendary;
    if(SlotKey==TEXT("optic")&&Id==TEXT("thermal_scope"))return EGunsmithModificationTier::Legendary;
    if(SlotKey==TEXT("trigger")&&Id==FullAutoTrigger::Part&&FullAutoTrigger::Supports(Weapon))
        return EGunsmithModificationTier::Legendary;
    if(SlotKey==TEXT("stock")&&Id==LegendaryTacticalStock::Part)
        return EGunsmithModificationTier::Legendary;
    if(TacticalDeviceVariants::IsSlot(SlotKey)&&Id==TacticalDeviceVariants::BlessedLaser)
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_xuanchi_zhenyue")&&SlotKey==TEXT("blade_2")&&(Id==TEXT("zhenmo_rune")||Id==TEXT("jingang_rune")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==TEXT("ue_zhanmadao")&&SlotKey==TEXT("blade_2")&&Id==TEXT("beiwei_rune"))
        return EGunsmithModificationTier::Special;
    if(Weapon==TEXT("ue_frost_crystal_sword")&&SlotKey==TEXT("blade_1")&&(Id==TEXT("star_marrow")||Id==TEXT("rift_piercer")))
        return EGunsmithModificationTier::Legendary;
    if(Weapon==ColdSteelFrostRunes::Zhanmadao&&SlotKey==TEXT("blade_2")&&ColdSteelFrostRunes::IsZhanmadaoLegendary(Id))
        return EGunsmithModificationTier::Legendary;
    if(SlotKey==TEXT("hammer_heads")&&Id==TEXT("pointed_hammer"))
        return EGunsmithModificationTier::Special;
    const bool VipGrip=Weapon==TEXT("ue_pit_viper2011")&&SlotKey==TEXT("reargrip")&&Id==TEXT("pit_viper_vip_scales");
    const bool SiMuzzle=Weapon==TEXT("ue_pit_viper2011")&&SlotKey==TEXT("muzzle")&&Id==TEXT("pit_viper_si_compensator");
    const bool G18Drum=Weapon==TEXT("ue_g18")&&SlotKey==TEXT("magazine")&&Id==TEXT("g18_drum_50");
    const bool ShotgunMuzzle=SlotKey==TEXT("muzzle")&&
        (Id==TEXT("shotgun_choke")||Id==TEXT("shotgun_birdcage_flash_hider")||Id==TEXT("shotgun_suppressor")||Id==TEXT("shotgun_duckbill"));
    const bool ShotgunTube=SlotKey==TEXT("magazine")&&
        ((Weapon==TEXT("ue_super90")&&Id==TEXT("super90_extended_tube"))
         ||(Weapon==TEXT("ue_m870")&&Id==TEXT("m870_tube_extension")));
    const bool M870Trigger=Weapon==TEXT("ue_m870")&&SlotKey==TEXT("trigger")&&Id==TEXT("m870_lightweight_trigger_kit");
    const bool Special=
        VipGrip || SiMuzzle || G18Drum || ShotgunMuzzle || ShotgunTube || M870Trigger ||
        ((Weapon==TEXT("ue_frost_crystal_sword")||Weapon==TEXT("ue_rune_sword")) &&
            SlotKey==TEXT("pommel") && (Id==TEXT("pommel_mana_orb")||Id==TEXT("ballast_rune"))) ||
        (Weapon==TEXT("ue_xuanchi_zhenyue") && SlotKey==TEXT("guard") && Id==TEXT("panchi_zhanyue")) ||
        (Weapon==TEXT("ue_rsh12") && SlotKey==TEXT("muzzle") &&
            (Id==TEXT("rsh12_heavy_suppressor")||Id==TEXT("rsh12_large_caliber_brake"))) ||
        (Weapon==TEXT("ue_rsh12") && SlotKey==TEXT("grip_body") && (Id==TEXT("rsh12_heavy_grip")||Id==TEXT("rsh12_quickdraw_grip"))) ||
        (Weapon==TEXT("ue_rsh12") && SlotKey==TEXT("optic") && RSH12OpticAssets::IsSquare(Id)) ||
        (Weapon==TEXT("ue_zhanmadao") && SlotKey==TEXT("blade_1") &&
            (Id==TEXT("yanling_edge")||Id==TEXT("tengyun_dragon"))) ||
        ((Weapon==TEXT("ue_tang_dao")||Weapon==TEXT("ue_xuanchi_zhenyue")) &&
            ((SlotKey==TEXT("blade_1") && (Id==TEXT("yanling_edge")||Id==TEXT("tengyun_dragon"))) ||
             (SlotKey==TEXT("blade_2") && (Id==TEXT("auspicious_cloud_rune")||Id==TEXT("mountain_rune"))) ||
             (SlotKey==TEXT("guard") && (Id==TEXT("xuan_cloud_dragon")||Id==TEXT("phoenix_feather"))) ||
             (SlotKey==TEXT("pommel") && (Id==TEXT("yanling_breaker")||Id==TEXT("tiger_mountain"))))) ||
        (Weapon==TEXT("ue_highland_claymore") &&
            ((SlotKey==TEXT("blade_2") && (Id==TEXT("wild_rune")||Id==TEXT("highland_oath_rune"))) ||
             (SlotKey==TEXT("guard") && (Id==TEXT("highland_cloven_guard")||Id==TEXT("highland_gale_wing"))) ||
             (SlotKey==TEXT("pommel") && (Id==TEXT("highland_thorn_crown")||Id==TEXT("highland_gale_oath"))))) ||
        (Weapon==TEXT("ue_frost_crystal_sword") && SlotKey==TEXT("blade_2") && Id==TEXT("spirit_burst_rune")) ||
        (Weapon==TEXT("ue_rune_sword") && SlotKey==TEXT("blade_2") && (Id==TEXT("golden_glow_rune")||Id==TEXT("silver_glow_rune"))) ||
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
