#pragma once

#include "CoreMinimal.h"
#include "RifleReloadRecovery.h"

// Presentation only: return to the calibrated hip frame inside the authored
// recovery, then hand the pose to the current grip's continuously playing idle.
// All times are source seconds; the owner supplies ReloadSourceTime for drums
// and stat-scaled reloads. No additional action duration or recovery timer.
namespace RifleReloadHandoff
{
    inline bool Supports(const FString& Definition)
    {
        return Definition == TEXT("ue_m4a1") || Definition == TEXT("ue_hk416")
            || Definition == TEXT("ue_qbz191") || Definition == TEXT("ue_m16a2")
            || Definition == TEXT("ue_akm") || Definition == TEXT("ue_a762")
            || Definition == TEXT("ue_ash12") || Definition == TEXT("ue_svd");
    }

    struct FWindow
    {
        float SourceEnd;
        float FramingStart;
        float PoseStart;

        float FramingWeight(float SourceTime) const
        {
            return RifleReloadRecovery::RemainingWeight(SourceTime, SourceEnd,
                FMath::Max(KINDA_SMALL_NUMBER, SourceEnd - FramingStart));
        }

        float PoseWeight(float SourceTime) const
        {
            return RifleReloadRecovery::RemainingWeight(SourceTime, SourceEnd,
                FMath::Max(KINDA_SMALL_NUMBER, SourceEnd - PoseStart));
        }
    };

    // Called only for Supports() rifles. Keep full authored hand motion until
    // the terminal pose handoff; blending the whole return from the last contact
    // would cut across the magazine/receiver instead of following the release arc.
    inline FWindow ForWeapon(const FString& Definition, bool bEmpty, bool bDrum, float SourceEnd)
    {
        float FramingStart;
        float PoseWindow = .12f;
        if (Definition == TEXT("ue_qbz191"))
        {
            // Normal: magazine released at 98/60. Empty: charging-handle
            // release at 151/60; its return continues through frame 164.
            FramingStart = (bEmpty ? 151.f : 98.f) / 60.f;
            PoseWindow = .10f;
        }
        else if (Definition == TEXT("ue_m16a2"))
        {
            // Retain the accepted normal 108..126 / empty 143..162 tails.
            FramingStart = (bEmpty ? 143.f : 108.f) / 60.f;
        }
        else if (Definition == TEXT("ue_akm") || Definition == TEXT("ue_a762"))
        {
            // The drum's normal hand release ends at 278/120; standard-mag
            // release ends earlier. Empty waits beyond bolt closure at 350/120.
            FramingStart = (bEmpty ? 362.f : 278.f) / 120.f;
            PoseWindow = .18f;
        }
        else if (Definition == TEXT("ue_ash12"))
        {
            // Right hand leaves the seated magazine at 1.91; the empty
            // handle closes at 2.65. Keep the source's final .12 s pose handoff.
            FramingStart = bEmpty ? 2.65f : 1.91f;
        }
        else if (Definition == TEXT("ue_svd"))
        {
            // Preserve the existing SVD exterior regrip and its .10 s handoff.
            FramingStart = SourceEnd - RifleReloadRecovery::ReturnSeconds(false, bEmpty);
            PoseWindow = .10f;
        }
        else
        {
            // M4 / HK416: normal release at 98/60. Empty starts after the
            // bolt closure and accepted .17 s impact; drums retain their own
            // 116/60 release and nonlinear source clock (end at 148/60).
            FramingStart = bEmpty ? (bDrum ? 116.f / 60.f : 132.f / 60.f) + .17f : 98.f / 60.f;
        }
        FramingStart = FMath::Clamp(FramingStart, 0.f, SourceEnd);
        return {SourceEnd, FramingStart, FMath::Max(FramingStart, SourceEnd - PoseWindow)};
    }
}
