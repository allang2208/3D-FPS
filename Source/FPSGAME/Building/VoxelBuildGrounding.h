#pragma once

#include "CoreMinimal.h"
#include "CollisionQueryParams.h"

class UWorld;
class AActor;
class UPrimitiveComponent;
struct FHitResult;

namespace VoxelGrounding
{
    constexpr double ContactToleranceCm=.5;
    constexpr double AnchorProbeRiseCm=40.5;
    constexpr double MinimumNormalZ=.7071067811865476; // 45 degrees.
    constexpr int32 MaxFoundationLayers=6;

    struct FFootprint
    {
        double Low=TNumericLimits<double>::Max();
        double High=TNumericLimits<double>::Lowest();
        TArray<TWeakObjectPtr<UPrimitiveComponent>,TInlineAllocator<5>> Surfaces;
        bool Contains(const UPrimitiveComponent* Component) const;
    };

    FCollisionQueryParams Query(UWorld* World,const AActor* Ignore);
    bool IsSurface(const FHitResult& Hit);
    // Query the rendered terrain's collision triangles, not the continuous
    // terrain generator: their interpolated heights are not interchangeable.
    bool Sample(UWorld* World,FVector Min,double Top,double Bottom,
        const FCollisionQueryParams& Params,FFootprint& Out,const FHitResult* Reference=nullptr);
}
