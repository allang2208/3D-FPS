#pragma once
#include "CoreMinimal.h"
#include "Engine/HitResult.h"

class AActor;
class ACharacter;
class UWorld;

namespace MeleeSmallTargets
{
    // Query assistance only: never changes aim, movement, pose or target selection state.
    inline constexpr float LowReachCM=120.f;
    inline constexpr float LowArcDegrees=60.f;
    inline constexpr float MaxFloorDifferenceCM=45.f;
    inline constexpr int32 MaxCoverCandidates=16;

    TArray<FHitResult> QueryLowSector(UWorld* World,ACharacter* Owner,const FTransform& Aim,
        float Reach,const TSet<TWeakObjectPtr<AActor>>& AlreadyHit,
        bool bCleave=true,float ArcDegrees=LowArcDegrees);

    // Keeps the existing Pawn trace for ordinary targets. Pawn object queries also
    // see small hands whose movement capsules intentionally ignore the Pawn channel.
    bool QueryQuickContact(UWorld* World,ACharacter* Owner,const FTransform& Aim,
        const FVector& Start,float Reach,float Radius,FHitResult& OutHit);

    // Same sweep and low-sector fallback as quick contact, but bodies do not stop a cleave.
    TArray<FHitResult> QueryQuickAreaContacts(UWorld* World,ACharacter* Owner,const FTransform& Aim,
        const FVector& Start,float Reach,float Radius);
}
