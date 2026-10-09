// Measured from the active meshes and compressed fire poses, 2026-10-09.
// Source: Tools/Weapons/CasingPorts20261009/calibration.json
#pragma once
#include "CoreMinimal.h"

namespace CasingPortCalibration
{
struct FPort
{
    const TCHAR* MeshPathFragment;
    FVector RootCentimetres;
    const TCHAR* Anchor;
    float OutwardSide;
};
// The native rig carries a 100x weapon root. Positions below are physical cm.
// Left-hand pistols retain the unmirrored gun, including its ejection side.
inline const FPort Ports[] =
{
    {TEXT("SK_M4_FoldingSights_HK416"), FVector(-2.214491, 10.534923, 7.704488), TEXT("WPN_root"), 1.0f}, // m4
    {TEXT("/Weapons/HK416/"), FVector(-2.003803, 11.034250, 8.092675), TEXT("WPN_root"), 1.0f}, // hk416
    {TEXT("/Weapons/QBZ191/"), FVector(-2.036330, 13.507045, 7.250817), TEXT("WPN_root"), 1.0f}, // qbz191
    {TEXT("/Weapons/A762/"), FVector(-2.104001, 10.120000, 6.640000), TEXT("WPN_root"), 1.0f}, // a762
    {TEXT("/Weapons/AKMIntegration/"), FVector(-1.655246, 11.994928, 7.048167), TEXT("WPN_root"), 1.0f}, // akm
    {TEXT("/Weapons/ASH12/"), FVector(-2.008546, -17.346387, 6.950923), TEXT("WPN_root"), 1.0f}, // ash12
    {TEXT("/Weapons/M16A2/"), FVector(-2.000000, 12.901771, 10.118269), TEXT("WPN_root"), 1.0f}, // m16a2
    {TEXT("/Weapons/SVDDragunov20260922/"), FVector(-2.009651, 13.632129, 4.519658), TEXT("WPN_root"), 1.0f}, // svd
    {TEXT("/Weapons/PKMLowpoly20260922/"), FVector(3.238324, 13.093769, 5.786007), TEXT("WPN_root"), -1.0f}, // pkm_lowpoly
    {TEXT("/Weapons/LMG201/"), FVector(2.990207, 13.632977, 4.607988), TEXT("WPN_root"), -1.0f}, // lmg201
    {TEXT("/M1911/"), FVector(-1.300001, 3.600209, 3.472080), TEXT("WPN_Slide"), 1.0f}, // m1911
    {TEXT("/Weapons/G18/"), FVector(-1.450005, 3.648187, 3.222249), TEXT("WPN_Slide"), 1.0f}, // g18
    {TEXT("/Weapons/PitViper2011/"), FVector(-1.250005, 2.497448, 2.973445), TEXT("WPN_Slide"), 1.0f}, // pit_viper2011
    {TEXT("/Weapons/Super90/"), FVector(2.250000, -1.300557, 2.240414), TEXT("WPN_root"), 1.0f}, // super90
};

inline const FPort* Find(const FString& MeshPath)
{
    for (const FPort& Port : Ports)
        if (MeshPath.Contains(Port.MeshPathFragment)) return &Port;
    return nullptr;
}
}
