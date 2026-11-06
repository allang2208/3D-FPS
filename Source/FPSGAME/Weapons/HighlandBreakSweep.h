#pragma once
#include "CoreMinimal.h"
#include "GunsmithSystem.h"
#include "../UI/ColdSteelInventoryTypes.h"

namespace HighlandBreakSweep
{
    inline const FName Clip(TEXT("HighlandBreakSweep"));
    constexpr uint8 AttackMeta = 0x09;
    constexpr float Contact = .30f;
    constexpr float Release = .47f;
    constexpr float PlaybackRate = 2.f;
    constexpr float ImpactStrength = 1.9f;
    constexpr float HitPauseSeconds = .060f;
    constexpr float Window = 4.f;
    constexpr float HeavyToughness = 1.5f;
    constexpr float PhysicalScale = 1.6f;
    constexpr float ArcDegrees = 180.f;
    constexpr float LaunchOutCMPerSecond = 500.f;
    constexpr float LaunchUpCMPerSecond = 420.f;
    constexpr float LaunchControlSeconds = .65f;
    inline FSoftObjectPath RiftPath(bool bLongGrip)
    {
        return FSoftObjectPath(bLongGrip?
            TEXT("/Game/Weapons/HighlandClaymore20260922/BreakSweep20261104/SM_Highland_SweepRift_LongGrip.SM_Highland_SweepRift_LongGrip"):
            TEXT("/Game/Weapons/HighlandClaymore20260922/BreakSweep20261104/SM_Highland_SweepRift_Standard.SM_Highland_SweepRift_Standard"));
    }
    inline float Radius(float SlashReach) { return SlashReach*1.25f; }
    inline bool Installed(const UGunsmithSystem* Gunsmith,const FColdSteelItem* Item)
    {
        return Item && Item->Definition==TEXT("ue_highland_claymore") && Gunsmith &&
            Gunsmith->Installed(*Item).FindRef(TEXT("blade_1"))==TEXT("highland_broadblade");
    }
    inline float Angle(float T)
    {
        const float U=FMath::Clamp((T-Contact)/(Release-Contact),0.f,1.f);
        // Enter and leave the contact sector with momentum; braking happens
        // outside the damage window, matching the reference-led authored cut.
        const float W=(-2.f*U*U*U+3.f*U*U)+.60f*(U*U*U-2.f*U*U+U)+.68f*(U*U*U-U*U);
        return FMath::Lerp(ArcDegrees*.5f,-ArcDegrees*.5f,W);
    }
}
