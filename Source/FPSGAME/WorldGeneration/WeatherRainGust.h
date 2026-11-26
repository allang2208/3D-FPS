#pragma once

#include "CoreMinimal.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

namespace WeatherRainGust
{
inline double SampleTime(const UWorld& World)
{
    const AGameStateBase* GameState=World.GetGameState();
    return GameState?GameState->GetServerWorldTimeSeconds():World.GetTimeSeconds();
}

// Rain at full intensity. Smoke adds local shear; the forest uses the same
// pulse along the weather manager's horizontal wind bearing.
inline float Magnitude(float Seconds)
{
    return FMath::Max(20.f,60.f+45.f*FMath::Sin(Seconds*.83f+1.3f)+30.f*FMath::Sin(Seconds*1.7f+.4f));
}
}
