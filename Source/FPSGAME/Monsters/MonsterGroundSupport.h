#pragma once
#include "CoreMinimal.h"
#include "CollisionQueryParams.h"
#include "Engine/HitResult.h"

class AActor;
class UWorld;
class USkeletalMeshComponent;

/** Reusable scratch buffer for one game-thread contact-sampling batch. */
class FMonsterGroundProbe
{
public:
    explicit FMonsterGroundProbe(const AActor* Owner);
    bool Trace(UWorld* World, const FVector& Start, const FVector& End,
        const FVector& Up, float MinimumNormalDot, FHitResult& Hit);
private:
    FCollisionQueryParams Query;
    FCollisionObjectQueryParams Objects;
    TArray<FHitResult> Hits;
};

namespace MonsterGroundSupport
{
    float QueryInterval(const USkeletalMeshComponent* Mesh, float VisibleInterval = .05f);
    bool FitPlane(TConstArrayView<FVector> Points, const FVector& Pivot, float TiltDegrees,
        float& Height, FQuat& Tilt);
}
