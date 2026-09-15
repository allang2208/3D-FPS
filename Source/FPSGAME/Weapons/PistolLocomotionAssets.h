#pragma once
#include "CoreMinimal.h"

namespace PistolLocomotionAssets
{
    inline FString AnimationPath(bool bRevolver, bool bEmpty = false)
    {
        const TCHAR* Family = bRevolver ? TEXT("DW715") : TEXT("M1911");
        const TCHAR* Kind = bEmpty && !bRevolver ? TEXT("sprint_empty") : TEXT("sprint");
        return FString::Printf(TEXT("/Game/Weapons/PistolLocomotion20260914/%s/Animations/A_%s_%s.A_%s_%s"),
            Family, Family, Kind, Family, Kind);
    }
}
