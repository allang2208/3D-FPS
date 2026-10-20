#pragma once
#include "CoreMinimal.h"
#include "../Weapons/SVCHWeaponAssets.h"

// Generated from saved stock surfaces by read_stock_contacts.py.
// WPN_root units (including the native FBX 100x scale), not wrist centimetres.
namespace FPSBodyRifleStock
{
inline const FVector* Find(const FString& Mesh)
{
    if(Mesh==SVCHWeaponAssets::MeshPath)return &SVCHWeaponAssets::StockContact;
    static const FVector Stock0(0.0008034199,-0.2941002867,-0.0117000861);
    if(Mesh==TEXT("/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative.SK_AKM_MannyNative"))return &Stock0;
    static const FVector Stock1(-0.0000327822,-0.2410488809,0.0241449107);
    if(Mesh==TEXT("/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416"))return &Stock1;
    static const FVector Stock2(0.0005566303,-0.2134929431,0.0290855213);
    if(Mesh==TEXT("/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny.SK_QBZ191_Manny"))return &Stock2;
    static const FVector Stock3(-0.0000384494,-0.2684736883,0.0320686189);
    if(Mesh==TEXT("/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny.SK_HK416_Manny"))return &Stock3;
    static const FVector Stock4(0.0032886810,-0.4581960469,0.0238314121);
    if(Mesh==TEXT("/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface.SK_ASH12_Surface"))return &Stock4;
    static const FVector Stock5(0.0002206065,-0.3274466648,0.0351930975);
    if(Mesh==TEXT("/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny.SK_M16_Manny"))return &Stock5;
    static const FVector Stock6(0.0005609117,-0.3258066926,0.0179999788);
    if(Mesh==TEXT("/Game/Weapons/A762/Integrated20260920/SK_A762_Manny.SK_A762_Manny"))return &Stock6;
    static const FVector Stock7(0.0000388854,-0.3480299390,-0.0154545373);
    if(Mesh==TEXT("/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock.SK_SVD_ModularStock"))return &Stock7;
    static const FVector Stock8(0.0008022252,-0.3358733326,-0.0079286860);
    if(Mesh==TEXT("/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10.SK_LMG201_Cover10"))return &Stock8;
    static const FVector Stock9(-0.0000338962,-0.3587398376,0.0272986952);
    if(Mesh==TEXT("/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular.SK_PKM_Manny_Modular"))return &Stock9;
    // Installed M870 buttpad, measured by M870ThirdPersonAim20261018/read_geometry.py.
    // Its native root has scale 100, matching the units of the existing table.
    static const FVector StockM870(.0000000381,.0697706106,.5068294271);
    if(Mesh==TEXT("/Game/Weapons/M870/Tactical20261015/SK_M870_V7.SK_M870_V7"))return &StockM870;
    return nullptr;
}
}
