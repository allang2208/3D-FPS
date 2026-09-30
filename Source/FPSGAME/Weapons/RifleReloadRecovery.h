#pragma once
#include "CoreMinimal.h"

// Recovery presentation only. ReloadSourceTime continues to own animation,
// mechanical contacts and gameplay; no independent recovery clock is added.
namespace RifleReloadRecovery
{
    // QBZ191 normal magazine/drum: seated at frame 95, hand releases at 98,
    // family grip return ends at 126 (60 fps source). Empty has a later charge.
    constexpr float QBZ191NormalReturnSeconds = 28.f / 60.f;

    inline float ReturnSeconds(bool bPKM, bool bEmpty)
    {
        // PKM: start after the cover latch (5.72) or manual push/release
        // (5.82/5.835), overlapping the existing hand return through 6.27.
        if (bPKM) return bEmpty ? .72f : .74f;
        // SVD: normal starts once the support hand has returned (frame 298).
        // Empty overlaps the exterior regrip, after the frame-350 bolt close;
        // the former last-54-frame linear slide lagged behind that motion.
        return bEmpty ? 123.f / 120.f : 102.f / 120.f;
    }

    inline float RemainingWeight(float SourceTime, float SourceEnd, float Window)
    {
        const float T = FMath::Clamp((SourceTime - (SourceEnd - Window)) / Window, 0.f, 1.f);
        // Same zero-velocity/zero-acceleration endpoints as quick-melee recover.
        // Evaluate directly: filtering this weight adds a second return to idle.
        return 1.f - T*T*T*(10.f + T*(-15.f + 6.f*T));
    }
}
