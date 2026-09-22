#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

// SVD (Dragunov, 7.62x54R, semiautomatic). The viewmodel rides the shared Manny arms
// (/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton), so this header carries only the
// rifle's own paths and the numbers measured on the exported mesh.
//
// UNIT CONVENTION (same as A762WeaponAssets/AKMSovietCalibration): the points handed to
// FPSGAMECharacter's sight calibration go through the accumulated WPN_root transform, whose
// FBX root carries the 100 cm scale - so they are BONE-LOCAL METRES with Blender's axes
// (X lateral, +Y toward the muzzle, +Z up), not centimetres. The measurements below were
// taken in that same mesh space (Receipts/weapon_space.json reports them in cm; they are
// divided by 100 here).
namespace SVDWeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_svd");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/SVDDragunov20260922/Viewmodel/SK_SVD_Manny.SK_SVD_Manny");
    inline constexpr const TCHAR* ItemAmmoId = TEXT("ammo_pkm_762x54r");

    inline bool Matches(const USkeletalMeshComponent* Mesh)
    {
        return Mesh && Mesh->GetSkeletalMeshAsset()
            && Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/SVDDragunov20260922/"));
    }

    // PSO-1 optical axis, measured from the eleven lens discs of SM_SVD_ScopeLens:
    // the ocular surface the eye sits behind, and the objective end, both on the tube axis.
    // The shared WPN_RearSight/WPN_FrontSight bones sit at the M4's iron sights, so the SVD
    // supplies its own pair - the same arrangement the AKM uses (AKMSoviet::Rear/Front).
    inline const FVector SightRear(0.0186f, -0.3893f, 0.0942f);
    inline const FVector SightFront(0.0186f, -0.0889f, 0.0942f);

    // Eye relief of the real PSO-1 is 68 mm, so the camera sits ~7 cm behind the ocular.
    // (M4/QBZ iron sights use 12; ASH-12 needed 18 because its sight sits mid-receiver.)
    inline constexpr float ADSRearEyeDistance = 7.f;

    // The shared WPN_SOCKET_Muzzle is placed for the M4's length, so on the 1.225 m SVD the
    // real muzzle sits 70.25 cm further forward and 7.59 cm lower than that socket. Muzzle FX
    // therefore cannot reuse the M4's 4.84 cm back-offset; this is the measured delta from
    // the shared socket in bone-local metres. NOT WIRED YET.
    inline const FVector MuzzleFromSharedSocket(0.0438f, 0.7025f, -0.0759f);

    // 7.62x54R leaves a longer trace than 5.56; ASH-12's 12.7 mm reads 4.6 cm.
    inline constexpr float TracerLengthCM = 4.0f;

    // Trigger finger check on the AKM idle pose: the animated right index tip lands 1.49 cm
    // from the SVD trigger centre while the palm sits on the grip, so the grip-based
    // alignment holds without an extra weapon offset.
    inline constexpr float TriggerFingerResidualCM = 1.49f;

    // The SVD is semiautomatic. The project's trigger path only single-shots pistols, so the
    // weapon asks for the same treatment through this flag (see FPSGAMECharacter's
    // bSingleShotTrigger); without it a held trigger would run the rifle like an AKM.
    inline constexpr bool bSingleShotTrigger = true;

    // Reload / charge markers are NOT set yet: they come from authored animations, which this
    // weapon does not have (see Docs/Weapons/svd-import-20260922.md).
}
