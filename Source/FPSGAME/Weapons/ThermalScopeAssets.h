#pragma once
#include "CoreMinimal.h"

namespace ThermalScopeAssets
{
inline constexpr const TCHAR* Id=TEXT("thermal_scope");
inline constexpr const TCHAR* Material=TEXT("/Game/Weapons/ThermalScope20261006/Runtime/M_ThermalScene.M_ThermalScene");
inline FString Family(const FString& D)
{
    if(D==TEXT("ue_hk416"))return TEXT("HK416");
    if(D==TEXT("ue_m16a2"))return TEXT("M16");
    if(D==TEXT("ue_m1911"))return TEXT("M1911");
    if(D==TEXT("ue_g18"))return TEXT("G18");
    if(D==TEXT("ue_pit_viper2011"))return TEXT("PitViper");
    if(D==TEXT("ue_dan_wesson715"))return TEXT("DW715");
    return TEXT("Common");
}
inline FString MeshPath(const FString& D)
{return TEXT("/Game/Weapons/ThermalScope20261006/Runtime/SM_Thermal_")+Family(D);}
inline FString SelectorPath(const FString& D)
{return TEXT("/Game/Weapons/ThermalScope20261006/Runtime/SM_ThermalSelector_")+Family(D);}
}
