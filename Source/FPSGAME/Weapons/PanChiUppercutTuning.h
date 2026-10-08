#pragma once
#include "CoreMinimal.h"

class UWorld;
class AActor;
struct FHitResult;

namespace PanChiUppercut
{
    inline constexpr float ForwardCM=300.f;
    inline constexpr float LaunchLiftCM=12.f;
    inline constexpr float CircleRadiusCM=220.f;
    inline constexpr float DragonLengthCM=640.f;
    inline constexpr float DragonWidthScale=1.7f;
    inline constexpr float DragonSeconds=1.5f;
    inline constexpr float DragonFadeStart=1.2f;
    inline constexpr float CircleSeconds=DragonSeconds;
    inline constexpr float CircleFadeStart=1.05f;
    // Ignore bodies when locating scenery; the circle never projects onto them.
    bool TraceSurface(UWorld* World,AActor* Owner,const FVector& Start,const FVector& End,FHitResult& Hit);
}
