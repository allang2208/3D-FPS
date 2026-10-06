#pragma once
#include "CoreMinimal.h"

namespace TacticalDeviceVariants
{
inline constexpr const TCHAR* BlessedLaser=TEXT("blessed_laser");
inline bool IsLaser(const FString& Id) { return Id==TEXT("laser") || Id==BlessedLaser; }
// Canonical device kind for shared behaviour and legacy fitting paths.
inline FString MeshVariant(const FString& Id) { return Id==BlessedLaser?FString(TEXT("laser")):Id; }
inline FString BlessedMeshPath(const FString& Family)
{
    return TEXT("/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Models/SM_BlessedLaser_")+Family;
}
inline FString FamilyForDefinition(const FString& Definition)
{
    if(Definition==TEXT("ue_akm"))return TEXT("AKM");
    if(Definition==TEXT("ue_qbz191"))return TEXT("QBZ191");
    if(Definition==TEXT("ue_m1911"))return TEXT("M1911");
    if(Definition==TEXT("ue_g18"))return TEXT("G18");
    if(Definition==TEXT("ue_pit_viper2011"))return TEXT("PitViper2011");
    if(Definition==TEXT("ue_dan_wesson715"))return TEXT("DanWesson715");
    if(Definition==TEXT("ue_rsh12"))return TEXT("RSH12");
    if(Definition==TEXT("ue_ash12"))return TEXT("ASH12");
    if(Definition==TEXT("ue_m16a2"))return TEXT("M16");
    if(Definition==TEXT("ue_a762"))return TEXT("A762");
    if(Definition==TEXT("ue_svd"))return TEXT("SVD");
    if(Definition==TEXT("ue_pkm_lowpoly"))return TEXT("PKM");
    if(Definition==TEXT("ue_lmg201"))return TEXT("LMG201");
    if(Definition==TEXT("ue_hk416"))return TEXT("HK416");
    return TEXT("M4");
}
}
