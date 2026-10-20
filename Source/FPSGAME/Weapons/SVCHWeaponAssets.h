#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

// Shared SVD source clocks plus SVCh-specific surface contacts. The shared
// animations retain their original markers; SVCh landmarks are supplied below.
// Authoring: SourceAssets/SVCHReplacement20261018/RealSights20261019/calibration.json.
namespace SVCHWeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_svch");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/SVCH/Replacement20261018/RealSights20261019/SK_SVCH_RealFoldingSights.SK_SVCH_RealFoldingSights");
    inline constexpr const TCHAR* Root = TEXT("/Game/Weapons/SVCH/Replacement20261018/RealSights20261019");
    inline constexpr const TCHAR* ProfilePath = TEXT("/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip.DA_SVCH_ElbowFitGrip");
    inline constexpr const TCHAR* ItemAmmoId = TEXT("ammo_pkm_762x54r");
    // Retain the accepted iron-sight eye distance with the new measured pair.
    inline constexpr float ADSRearEyeDistance = 10.f;
    inline constexpr float SightHeightAboveRailCM = 3.1f;
    inline constexpr float OpticAlongCM = 9.918044f; // Same absolute optic mount; measured rear iron moved onto the rail.
    inline constexpr float Magnification = 1.f;
    inline constexpr bool bSingleShotTrigger = true;
    inline constexpr int32 FireVariantCount = 1;
    // Mechanical clock, in source seconds of the shared rifle clips.
    inline constexpr float MagazineOut = 52.f / 120.f;
    inline constexpr float MagazineInsert = 220.f / 120.f;
    inline constexpr float MagazineSeat = 240.f / 120.f;
    inline constexpr float ChargeStart = 268.f / 120.f;
    inline constexpr float ChargePull = 310.f / 120.f;
    inline constexpr float ChargeRelease = 350.f / 120.f;
    inline constexpr float EquipPull = 64.f / 120.f;
    inline constexpr float EquipRelease = 100.f / 120.f;
    // The charging handle is on the left of the receiver; the ejection port is
    // on the right. Measured stroke of the straight-pull bolt.
    inline constexpr float ChargingHandleTravelCM = 7.72f;

    // Invert the SAVED UE component bind, which includes FBX's Y reflection and
    // 100x root scale. Inverting Blender's rest directly shifted the sight pair
    // by 28.75 cm. Physical gun-up also differs from bone-local Z by 5 degrees.
    inline const FVector RearSight(-0.014102353522f, 0.015072240813f, 0.126623457005f);
    inline const FVector FrontSight(-0.014103224794f, 0.476702295842f, 0.126623986066f);
    inline const FVector MuzzlePoint(-0.008399854f, 0.672519303f, 0.061431614f);
    inline const FVector EjectPort(-0.023118249f, 0.152813100f, 0.063992882f);
    inline const FVector SightUp(-0.087155794f, -0.000001406f, 0.996194694f);
    // Current replacement stock's rear 2.5 cm surface band, in saved root units.
    // Shared by the world-body shoulder hold and the quick-melee contact probe.
    inline const FVector StockContact(-0.006067879f, -0.216416583f, 0.028199226f);

    inline bool Matches(const USkeletalMeshComponent* Mesh)
    {
        return Mesh && Mesh->GetSkeletalMeshAsset()
            && Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/SVCH/"));
    }
    inline void FactorySights(USkeletalMeshComponent* Mesh, bool Visible)
    {
        if (!Matches(Mesh)) return;
        const auto* Asset = Mesh->GetSkeletalMeshAsset();
        const auto* Render = Asset->GetResourceForRendering();
        if (!Render) return;
        for (int32 L = 0; L < Render->LODRenderData.Num(); ++L)
            for (int32 S = 0; S < Render->LODRenderData[L].RenderSections.Num(); ++S)
            {
                const int32 M = Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if (Asset->GetMaterials().IsValidIndex(M) && Asset->GetMaterials()[M].MaterialSlotName == TEXT("SVCH_New_FactorySights"))
                    Mesh->ShowMaterialSection(M, S, Visible, L);
            }
    }
    // The weapon supplies its own sight pair because the shared WPN_* sight
    // bones sit at the M4 positions; same approach as AKMSoviet and SVD.
    inline FString AnimationPath(const TCHAR* Clip)
    {
        return FString::Printf(
            TEXT("/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_%s.A_SVD_%s"), Clip, Clip);
    }
}
