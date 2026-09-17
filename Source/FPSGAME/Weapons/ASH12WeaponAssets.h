#pragma once
#include "CoreMinimal.h"

// ASH-12 (12.7x55 mm bullpup). The viewmodel rides the shared Manny arms, so
// this header only carries the rifle's own paths and measured fit numbers.
namespace ASH12WeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_ash12");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/ASH12/Integrated20260917/SK_ASH12_Manny.SK_ASH12_Manny");
    // The accepted rifles put the iron sight at the receiver's rear, so 12 cm of
    // eye relief lands behind the gun. This one's sight is mid-receiver on the
    // carry handle; measured stills (Saved/ASH12SightAudit) show 12 cm showing
    // the gun's rear instead of a sight picture, while 18 cm frames it like the
    // QBZ reference does at 12 cm.
    inline constexpr float ADSRearEyeDistance = 18.f;
    // Rear/front sight markers are measured on the carry-handle rail crown, so
    // the shared optic saddle needs no drop below them.
    inline constexpr float OpticRailDrop = 0.f;
    // Factory flash-hider rear rim behind WPN_SOCKET_Muzzle, in centimetres.
    inline constexpr float MuzzleBackOffset = 6.79f;
    // Measured on the export: a 12.7 mm case leaves a longer trace than 5.56.
    inline constexpr float TracerLengthCM = 4.6f;
    inline FString AnimationPath(const TCHAR* Clip)
    {
        return FString::Printf(TEXT("/Game/Weapons/ASH12/Integrated20260917/Animations/A_ASH12_%s.A_ASH12_%s"), Clip, Clip);
    }
}
