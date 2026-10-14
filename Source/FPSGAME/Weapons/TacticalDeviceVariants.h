#pragma once
#include "CoreMinimal.h"

namespace TacticalDeviceVariants
{
inline constexpr const TCHAR* BlessedLaser=TEXT("blessed_laser");
inline constexpr const TCHAR* PrimarySlot=TEXT("tactical");
inline constexpr const TCHAR* SecondarySlot=TEXT("tactical_secondary");
inline bool IsSlot(const FString& Slot) { return Slot==PrimarySlot || Slot==SecondarySlot; }
inline FString IconSlot(const FString& Slot) { return IsSlot(Slot)?FString(PrimarySlot):Slot; }
inline bool IsLaser(const FString& Id) { return Id==TEXT("laser") || Id==BlessedLaser; }
inline int32 LaserStrength(const FString& Id) { return Id==BlessedLaser?2:Id==TEXT("laser")?1:0; }
// One complete laser option wins (including its handling costs). Equal lasers
// deterministically use the original slot; map iteration order never decides.
inline FString ActiveLaserSlot(const FString& Primary,const FString& Secondary)
{
    const int32 A=LaserStrength(Primary),B=LaserStrength(Secondary);
    return B>A?FString(SecondarySlot):A>0?FString(PrimarySlot):FString();
}
inline bool SupportsSecondary(const FString& Definition)
{
    return Definition==TEXT("ue_m4a1") || Definition==TEXT("ue_akm") || Definition==TEXT("ue_qbz191")
        || Definition==TEXT("ue_ash12") || Definition==TEXT("ue_m16a2") || Definition==TEXT("ue_a762")
        || Definition==TEXT("ue_svd") || Definition==TEXT("ue_pkm_lowpoly") || Definition==TEXT("ue_lmg201")
        || Definition==TEXT("ue_hk416");
}
inline FString Super90MeshPath(const FString& Id)
{
    return TEXT("/Game/Weapons/Super90/TacticalBottom20261012/SM_")+Id;
}
// Each side has its own surface-matched bearing. Both use the existing positive
// scale mount transform, including authored emitter and aim-guide sockets.
inline FString FittedMeshPath(const FString& Family,const FString& Id,bool OppositeSide)
{
    if(Family==TEXT("Super90"))return Super90MeshPath(Id);
    return FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/DualFit20261008/%s/SM_%s_%d"),*Family,*Id,OppositeSide?2:1);
}
// Canonical device kind for shared behaviour and legacy fitting paths.
inline FString MeshVariant(const FString& Id) { return Id==BlessedLaser?FString(TEXT("laser")):Id; }
inline FString BlessedMeshPath(const FString& Family)
{
    if(Family==TEXT("Super90"))return Super90MeshPath(BlessedLaser);
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
    if(Definition==TEXT("ue_super90"))return TEXT("Super90");
    return TEXT("M4");
}
}
