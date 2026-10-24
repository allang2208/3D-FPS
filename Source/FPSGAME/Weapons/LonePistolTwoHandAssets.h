#pragma once
#include "CoreMinimal.h"

// One left-primary native rig when the main slot is empty. The accepted
// Pit Viper clips keep their published path; the other pistols use this rollout.
namespace LonePistolTwoHandAssets
{
inline bool Supports(FName Definition)
{
    return Definition==TEXT("ue_m1911")||Definition==TEXT("ue_g18")||
        Definition==TEXT("ue_pit_viper2011")||Definition==TEXT("ue_dan_wesson715")||Definition==TEXT("ue_rsh12");
}
inline const TCHAR* Key(const FString& Definition)
{
    if(Definition==TEXT("ue_m1911"))return TEXT("M1911");
    if(Definition==TEXT("ue_g18"))return TEXT("G18");
    if(Definition==TEXT("ue_dan_wesson715"))return TEXT("DW715");
    return TEXT("RSH12");
}
inline const TCHAR* Mesh(const FString& Definition)
{
    if(Definition==TEXT("ue_m1911"))return TEXT("/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny");
    if(Definition==TEXT("ue_g18"))return TEXT("/Game/Weapons/G18/Integrated20260929/Single/SK_G18_Manny");
    if(Definition==TEXT("ue_pit_viper2011"))return TEXT("/Game/Weapons/PitViper2011/Integrated20261002/Single/SK_PitViper2011_Manny");
    if(Definition==TEXT("ue_dan_wesson715"))return TEXT("/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny");
    return TEXT("/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny");
}
inline FString Animation(const FString& Definition,FString Role)
{
    if(Role.StartsWith(TEXT("quickcombat")))Role=Role.EndsWith(TEXT("_empty"))?TEXT("quickcombat_empty"):TEXT("quickcombat");
    if(Definition==TEXT("ue_pit_viper2011"))
    {
        if(Role==TEXT("equip"))Role=TEXT("equip_charge");
        if(Role==TEXT("equip_empty"))Role=TEXT("equip_charge_empty");
        return TEXT("/Game/Weapons/PitViper2011/LeftTwoHand20261020/A_PitViper_LeftTwoHand_")+Role;
    }
    if(Definition==TEXT("ue_dan_wesson715")||Definition==TEXT("ue_rsh12"))
    {
        if(Role==TEXT("equip_empty"))Role=TEXT("equip");
        if(Role==TEXT("quickcombat_empty"))Role=TEXT("quickcombat");
    }
    return FString::Printf(TEXT("/Game/Weapons/PistolLeftTwoHand20261020/%s/A_LeftTwoHand_%s_%s"),Key(Definition),Key(Definition),*Role);
}
inline FString Profile(const FString& Definition,FName Family)
{
    return FString::Printf(TEXT("/Game/Weapons/PistolLeftTwoHand20261020/%s/DA_LeftTwoHand_%s_%s"),
        Key(Definition),Key(Definition),*Family.ToString());
}
}
