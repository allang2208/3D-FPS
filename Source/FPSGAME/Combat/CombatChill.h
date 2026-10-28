#pragma once
#include "CoreMinimal.h"

// All chill sources share these rules; sources still own stacks and duration.
namespace CombatChill
{
inline constexpr float SlowPerStack=.05f;
inline constexpr int32 FreezeThreshold=20;
inline constexpr int32 FreezeCost=10;
inline float MovementMultiplier(int32 Stacks)
{return FMath::Max(.01f,1.f-FMath::Max(0,Stacks)*SlowPerStack);}
}
