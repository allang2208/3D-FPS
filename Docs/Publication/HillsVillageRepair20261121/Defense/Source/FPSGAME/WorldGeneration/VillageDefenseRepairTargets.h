#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "VillageDefenseRepairTargets.generated.h"

class AVillageDefenseSection;
class APawn;

// Collapsed pieces have no physics bodies. Keep their original mesh bounds for
// interaction without turning an open breach into a raycast or movement blocker.
UCLASS()
class UVillageDefenseRepairTargets : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    static constexpr float Reach = 250.f;
    void Update(AVillageDefenseSection& Section);
    void Remove(AVillageDefenseSection& Section);
    AVillageDefenseSection* Trace(const APawn& Pawn, const FVector& Eye, const FVector& RayEnd,
        AVillageDefenseSection** Nearby) const;
private:
    struct FPiece
    {
        FBox Bounds;
        FTransform RelativePose;
    };
    struct FBreach
    {
        FBox LocalBounds{ForceInit};
        TArray<FPiece,TInlineAllocator<2>> Pieces;
    };
    TMap<TWeakObjectPtr<AVillageDefenseSection>,FBreach> Breaches;
};
