#pragma once
#include "CoreMinimal.h"

// Authored release seconds, independent of ordinary weapon attack speed.
namespace RuneSwordChixiaoRhythm
{
    constexpr float FirstStart=0.f;
    constexpr float FirstEnd=.075f;
    constexpr float FirstFollowEnd=.12f;
    constexpr float SecondStart=.18f;
    constexpr float SecondEnd=.30f;
    constexpr float FollowEnd=.38f;
    constexpr float End=1.f;
    constexpr float SampleRate=240.f;
    inline bool IsContact(float Time)
    {
        return (Time>=FirstStart&&Time<=FirstEnd)||(Time>=SecondStart&&Time<=SecondEnd);
    }
}
