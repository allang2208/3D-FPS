#pragma once

#include "CoreMinimal.h"

/** ChargedHeavyV12: charge uses real gameplay seconds; release uses attack speed. */
namespace RuneSwordHeavyRhythm
{
    constexpr float ChargeSeconds=2.f;
    constexpr float ContactStart=0.f;
    constexpr float ContactEnd=.075f;
    constexpr float FollowEnd=.2375f;
    constexpr float ArrestEnd=.2875f;
    constexpr float ReturnCorner=.5875f;
    constexpr float AttackEnd=1.f;
    constexpr float DamageMultiplier=2.f;
    constexpr float SampleRate=480.f;

    // Feed the existing directional camera envelope with the heavy phase clock.
    inline float CameraSourceTime(float T)
    {
        if(T<=ContactEnd)return .90f+.115f*FMath::Clamp(T/ContactEnd,0.f,1.f);
        if(T<=FollowEnd)return FMath::Lerp(1.015f,1.115f,(T-ContactEnd)/(FollowEnd-ContactEnd));
        if(T<=ArrestEnd)return 1.115f;
        if(T<=ReturnCorner)return FMath::Lerp(1.115f,1.34f,(T-ArrestEnd)/(ReturnCorner-ArrestEnd));
        return FMath::Lerp(1.34f,1.65f,FMath::Clamp((T-ReturnCorner)/(AttackEnd-ReturnCorner),0.f,1.f));
    }
}
