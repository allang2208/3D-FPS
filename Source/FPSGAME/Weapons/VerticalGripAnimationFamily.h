#pragma once
#include "CoreMinimal.h"

// Upright underbarrel grips share the authored hand/arm motion family.
// Contact profiles retain model fit while using the same nine-clip source.
namespace VerticalGripAnimationFamily
{
    enum class EContactProfile : uint8 { Vertical, Prism };

    inline FString M4ClipPath(EContactProfile Profile, const TCHAR* Clip)
    {
        const bool bPrism = Profile == EContactProfile::Prism;
        return FString::Printf(TEXT("%s/A_M4_%s_%s"),
            bPrism ? TEXT("/Game/Weapons/M4VREGripExtensions/Prism") : TEXT("/Game/Weapons/M4VerticalGripVRENatural/Vertical"),
            bPrism ? TEXT("Prism") : TEXT("Vertical"), Clip);
    }
}
