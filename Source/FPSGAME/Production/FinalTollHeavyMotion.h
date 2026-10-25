#pragma once
#include "CoreMinimal.h"

// Complete native Slash1 and Uppercut tracks, joined only between strokes.
// The charge uses Slash1's own windup so release starts at the same pose.
// Weapon attack-speed modifiers do not compress this martial release clock.
namespace FinalTollHeavy
{
    inline constexpr float FirstContact=.10f,SecondStart=.24f,SecondContact=.42f,FollowEnd=.54f,Duration=1.25f;
    inline constexpr const TCHAR* Asset=TEXT("/Game/Weapons/RuneboundWarhammer20261022/FinalTollDirectReuseV5/A_FinalToll_DirectReuseV5.A_FinalToll_DirectReuseV5");
    inline float ChargeSource(float Fraction)
    {
        return .84f*FMath::SmoothStep(0.f,1.f,Fraction);
    }
}
