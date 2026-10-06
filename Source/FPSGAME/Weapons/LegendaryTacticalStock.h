#pragma once
#include "CoreMinimal.h"

// All fitted meshes use physical centimetres in WPN_root space. The approved
// body is shared; each asset carries its own retained receiver interface.
namespace LegendaryTacticalStock
{
inline constexpr const TCHAR* Part=TEXT("legendary_adjustable_tactical_stock");
inline FString Family(const FString& Definition)
{
    if(Definition==TEXT("ue_m4a1"))return TEXT("M4");
    if(Definition==TEXT("ue_akm"))return TEXT("AKM");
    if(Definition==TEXT("ue_qbz191"))return TEXT("QBZ191");
    if(Definition==TEXT("ue_m16a2"))return TEXT("M16");
    if(Definition==TEXT("ue_a762"))return TEXT("A762");
    if(Definition==TEXT("ue_svd"))return TEXT("SVD");
    if(Definition==TEXT("ue_pkm_lowpoly"))return TEXT("PKM");
    if(Definition==TEXT("ue_lmg201"))return TEXT("LMG201");
    if(Definition==TEXT("ue_hk416"))return TEXT("HK416");
    return FString();
}
inline bool Supports(const FString& Definition){return !Family(Definition).IsEmpty();}
inline FString MeshPath(const FString& Definition)
{
    const FString Key=Family(Definition);
    return Key.IsEmpty()?FString():TEXT("/Game/Weapons/LegendaryStock20261006/Fitted/SM_TacticalStock_")+Key;
}
}
