#pragma once
#include "CoreMinimal.h"

namespace ColdSteelFrostRunes
{
    inline constexpr const TCHAR* Definition=TEXT("ue_frost_crystal_sword");
    inline constexpr const TCHAR* SpiritBurst=TEXT("spirit_burst_rune");
    inline constexpr const TCHAR* Warhammer=TEXT("ue_steel_warhammer");
    inline constexpr const TCHAR* RuneboundWarhammer=TEXT("ue_runebound_warhammer");
    inline constexpr const TCHAR* ThunderGodHammer=TEXT("ue_thunder_god_hammer");
    inline bool IsThunderExclusive(const FString& Rune){return Rune==TEXT("lei_ming_rune")||Rune==TEXT("hui_xiang_rune");}
    inline constexpr const TCHAR* SwiftMana=TEXT("swift_mana_rune");
    inline constexpr const TCHAR* DestructionMana=TEXT("destruction_mana_rune");
    inline bool IsWarhammer(const FString& Weapon){return Weapon==Warhammer||Weapon==RuneboundWarhammer||Weapon==ThunderGodHammer;}
    inline const TCHAR* Slot(const FString& Weapon){return IsWarhammer(Weapon)?TEXT("rune"):TEXT("blade_2");}
    inline const TCHAR* WarhammerRuneMaterial(const FString& Weapon,const FString& Rune=FString())
    {
        if(Weapon==ThunderGodHammer&&Rune==TEXT("lei_ming_rune"))
            return TEXT("/Game/Weapons/ThunderGodHammer20261028/LeiMingRefineV2/M_SilverRuneSurface_LeiMingRefineV2");
        if(Weapon==ThunderGodHammer&&IsThunderExclusive(Rune))
            return TEXT("/Game/Weapons/ThunderGodHammer20261028/ExclusiveRunesV1/M_SilverRuneSurface_ThunderExclusiveV1");
        if(Weapon==ThunderGodHammer)
            return TEXT("/Game/Weapons/ThunderGodHammer20261028/ModulesV1/Runes/M_SilverRuneSurface_ThunderGodHammerShaftV1");
        return Weapon==RuneboundWarhammer?
            TEXT("/Game/Weapons/RuneboundWarhammer20261022/ModulesV1/Runes/M_SilverRuneSurface_RuneboundWarhammerShaftV1"):
            TEXT("/Game/Weapons/SteelWarhammer20261014/Runes/ShaftWrapV2/M_SilverRuneSurface_WarhammerShaftV2");
    }
    inline bool IsCommon(const FString& Rune)
    {
        return Rune==TEXT("strength_rune")||Rune==TEXT("haste_rune")||Rune==TEXT("resonance_rune")||
            Rune==TEXT("erosion_rune")||Rune==TEXT("conduction_rune");
    }
    inline bool IsWarhammerRune(const FString& Weapon,const FString& Rune)
    {return IsCommon(Rune)||(Weapon==ThunderGodHammer&&IsThunderExclusive(Rune))||(Weapon==RuneboundWarhammer&&(Rune==SwiftMana||Rune==DestructionMana));}
    inline constexpr const TCHAR* TangDao=TEXT("ue_tang_dao");
    inline constexpr const TCHAR* XuanChi=TEXT("ue_xuanchi_zhenyue");
    inline constexpr const TCHAR* AuspiciousCloud=TEXT("auspicious_cloud_rune");
    inline constexpr const TCHAR* CloudMask=TEXT("/Game/Weapons/TangDao20261002/CloudRune20261002/Textures/T_Mask_auspicious_cloud_rune");
    inline constexpr const TCHAR* Jingang=TEXT("jingang_rune");
    inline constexpr const TCHAR* Zhanmadao=TEXT("ue_zhanmadao");
    inline constexpr const TCHAR* Beiwei=TEXT("beiwei_rune");
    inline constexpr const TCHAR* Chixiao=TEXT("chixiao_rune");
    inline constexpr const TCHAR* Zhufeng=TEXT("zhufeng_rune");
    inline bool IsZhanmadaoLegendary(const FString& Rune){return Rune==Chixiao||Rune==Zhufeng;}
    // Old builds allowed a legendary blade and a rune together. Keep the signature
    // skill on migration, and release the physical blade slot for an independent choice.
    inline const TCHAR* LegacyBladeRune(const FString& Weapon,const FString& Blade)
    {
        if(Weapon!=Zhanmadao)return nullptr;
        if(Blade==TEXT("chixiao"))return Chixiao;
        if(Blade==TEXT("zhufeng"))return Zhufeng;
        return nullptr;
    }
    inline constexpr const TCHAR* BeiweiMask=TEXT("/Game/Weapons/Zhanmadao20261018/BeiweiRuneV1/Textures/T_Mask_beiwei_rune");
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
        if(IsThunderExclusive(Rune)&&Weapon!=ThunderGodHammer)return {};
        if(IsWarhammer(Weapon)&&!IsWarhammerRune(Weapon,Rune))return {};
        if((Rune==Beiwei||IsZhanmadaoLegendary(Rune))&&Weapon!=Zhanmadao)return {};
        if((Rune==Zhenmo||Rune==Jingang)&&Weapon!=XuanChi)return {};
        if(Rune==TEXT("golden_glow_rune")&&Weapon!=TEXT("ue_rune_sword"))return {};
        if((Rune==AuspiciousCloud||Rune==Mountain)&&!SupportsEasternRunes(Weapon))return {};
        // Preserve the player's installed upgrade when erosion becomes innate.
        return Weapon==Definition&&Rune==TEXT("erosion_rune")?FString(SpiritBurst):Rune;
    }
}
