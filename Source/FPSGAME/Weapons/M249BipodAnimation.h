#pragma once
#include "M24Bipod.h"

// M24's reversible hand-action phases, fitted to the M249 native skeleton.
// Geometry remains in M249Bipod.h so mesh regeneration cannot erase this contract.
namespace M249BipodAnimation
{
inline constexpr const TCHAR* Profile=TEXT("/Game/Weapons/M249/Bipod/DA_M249_Bipod");
inline constexpr const TCHAR* SupportProfile=TEXT("/Game/Weapons/M249/Bipod/DA_M249_SupportGrip");
inline constexpr float Duration=.90f;
inline float LegWeight(float Phase)
{
    // M249Bipod::LegRotation applies the smoothstep exactly once.
    return FMath::Clamp((Phase*M24Bipod::Duration-M24Bipod::GripContact)
        /(M24Bipod::PullComplete-M24Bipod::GripContact),0.f,1.f);
}
}
