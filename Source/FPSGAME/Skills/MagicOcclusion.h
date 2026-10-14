#pragma once
#include "CoreMinimal.h"
#include "CollisionQueryParams.h"

class AActor;
class UPrimitiveComponent;
class UWorld;

/** Damage propagation / spell sight only. Physical projectiles, ground and
 *  ceiling probes retain their own collision rules. */
namespace MagicOcclusion
{
using FBodySamples=TArray<FVector,TInlineAllocator<6>>;
FPSGAME_API bool IsOpenBarrier(const UPrimitiveComponent* Component);
FPSGAME_API void BodySamples(const AActor* Target,const FVector& From,FBodySamples& Out);
FPSGAME_API bool TraceBlocker(UWorld* World,const FVector& Start,const FVector& End,
    const FCollisionQueryParams& Query,FHitResult& Hit,const AActor* RangedSource=nullptr);
FPSGAME_API bool HasExposure(UWorld* World,const AActor* Target,const FVector& From,
    const FCollisionQueryParams& Query,const AActor* RangedSource=nullptr);
}
