#pragma once
#include "CoreMinimal.h"

namespace RingChainSweepMotion
{
    inline const FName Charge(TEXT("RingChainSweepCharge"));
    inline const FName Release(TEXT("RingChainSweepRelease"));
    // Both phases use the same FromReady take. Hold its right-hand windup
    // at frame 24/120, with twelve authored frames left before contact.
    constexpr float Chamber=.20f;
    inline bool IsPhase(FName Clip){return Clip==Charge||Clip==Release;}
}
