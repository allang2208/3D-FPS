#pragma once

#include "CoreMinimal.h"
#include "CollisionQueryParams.h"
#include "CollisionShape.h"
#include "Engine/EngineTypes.h"

class AActor;
class UWorld;

// Combat queries only. Movement, ground support and interaction collision do
// not change. Re-query the original segment after an ally, so cover behind it
// still stops the attack and ally contacts consume no penetration or range.
namespace RangedAttackQuery
{
FPSGAME_API bool IsFriendlyUnit(const AActor* Source, const AActor* Candidate);
FPSGAME_API bool LineTraceSingle(UWorld* World, const AActor* Source, FHitResult& Hit,
    const FVector& Start, const FVector& End, ECollisionChannel Channel, const FCollisionQueryParams& Query);
FPSGAME_API bool LineTraceTest(UWorld* World, const AActor* Source,
    const FVector& Start, const FVector& End, ECollisionChannel Channel, const FCollisionQueryParams& Query);
FPSGAME_API bool SweepSingle(UWorld* World, const AActor* Source, FHitResult& Hit,
    const FVector& Start, const FVector& End, const FQuat& Rotation, ECollisionChannel Channel,
    const FCollisionShape& Shape, const FCollisionQueryParams& Query);
FPSGAME_API bool SweepMulti(UWorld* World, const AActor* Source, TArray<FHitResult>& Hits,
    const FVector& Start, const FVector& End, const FQuat& Rotation, ECollisionChannel Channel,
    const FCollisionShape& Shape, const FCollisionQueryParams& Query);
FPSGAME_API bool SweepObjects(UWorld* World, const AActor* Source, TArray<FHitResult>& Hits,
    const FVector& Start, const FVector& End, const FQuat& Rotation, const FCollisionObjectQueryParams& Objects,
    const FCollisionShape& Shape, const FCollisionQueryParams& Query);
}
