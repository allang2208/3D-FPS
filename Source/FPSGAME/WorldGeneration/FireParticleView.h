#pragma once

#include "CoreMinimal.h"
#include "ConvexVolume.h"

class UNiagaraComponent;
class UWorld;

enum class EFireParticleDetail : uint8 { Off, Simple, Full };

// All burning fixtures in a world share the same local viewport projections.
struct FFireParticleViews
{
    double NearestDistanceSquared(UWorld& World, const FVector& Position);
    EFireParticleDetail Classify(UWorld& World, const FVector& Source, float Radius, float VerticalOffset,
        float FullRange, float MaxRange, const UNiagaraComponent* Effect, bool bWasFull);

private:
    struct FView
    {
        FVector Eye;
        FConvexVolume Frustum;
        bool bHasProjection = false;
    };
    TArray<FView, TInlineAllocator<2>> Views;
    double RefreshAt = -1.;
    void Refresh(UWorld& World);
};
