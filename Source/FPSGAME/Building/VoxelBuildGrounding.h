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
        // 审计 P3b：Sample() 固定跑 5 条竖直探针（中心 + 四角），所以内联容量取 5 时
        // 只要 5 条探针命中 5 个不同组件就已满，第 6 个不同表面（地形分块边界、
        // 探针同时打到墙与地）就会溢出到堆分配。ResolveGroundPlacement 会一次构造
        // 最多 25 个 FFootprint（5×5 刷子），即潜在 25 次堆分配 @20Hz。提到 8。
        TArray<TWeakObjectPtr<UPrimitiveComponent>,TInlineAllocator<8>> Surfaces;
        bool Contains(const UPrimitiveComponent* Component) const;
    };

    FCollisionQueryParams Query(UWorld* World,const AActor* Ignore);
    bool IsSurface(const FHitResult& Hit);
    // Query the rendered terrain's collision triangles, not the continuous
    // terrain generator: their interpolated heights are not interchangeable.
    bool Sample(UWorld* World,FVector Min,double Top,double Bottom,
        const FCollisionQueryParams& Params,FFootprint& Out,const FHitResult* Reference=nullptr);
}
