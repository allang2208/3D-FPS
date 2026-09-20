#pragma once
#include "CoreMinimal.h"

namespace M16WeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_m16a2");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny.SK_M16_Manny");
    inline constexpr const TCHAR* FireSoundPath = TEXT("/Game/Weapons/M16A2/OriginalAudio20260920/S_M16_OriginalFire.S_M16_OriginalFire");
    // The factory part's rear bore centre, already authored into the M16 rig.
    // The legacy firing marker is 5.89 mm above this axis; it is not a mount.
    inline constexpr const TCHAR* MuzzleMountBone = TEXT("WPN_M16Muzzle");
    inline constexpr const TCHAR* MuzzleMaterialSlot = TEXT("M_M16_Flash_Hider");
    inline constexpr float FactoryMuzzleLengthCM = 4.109337f;
    // Empty reload's 60 Hz source clock, shared with the authored handle travel.
    inline constexpr float MagazineOut = 21.f / 60.f;
    inline constexpr float MagazineInsert = 54.f / 60.f;
    inline constexpr float MagazineSeat = 80.f / 60.f;
    inline constexpr float ChargePull = 125.f / 60.f;
    inline constexpr float ChargeRelease = 139.f / 60.f;
    inline FString AnimationPath(const TCHAR* Clip)
    {
        return FString::Printf(TEXT("/Game/Weapons/M16A2/Gameplay20260919/Animations/A_M16_%s.A_M16_%s"), Clip, Clip);
    }
}
