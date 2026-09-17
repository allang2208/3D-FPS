#pragma once
#include "CoreMinimal.h"

class ATemperateHillsWorld;

/** Seeded resource identity; never persist a PCG instance index. */
struct FProductionResource
{
    TWeakObjectPtr<ATemperateHillsWorld> World;
    FString Id;
    FString Name;
    FString RequiredTool;
    TMap<FString,int64> Rewards;
    FSoftObjectPath Mesh;
    FTransform Transform;
    FVector Direction = FVector::ForwardVector;
    int32 Layer = -1; // 0 tree, 1 rock, 2 surface soil (not a PCG layer)
    uint32 Seed = 0;
    uint64 CandidateId = 0;
    static constexpr int32 RequiredHits = 3;
    // 0 = default (trees and rocks need three hits). Surface soil digs one 20 cm
    // layer per swing, so it asks for one.
    int32 HitsRequired = 0;
    int32 HitsNeeded() const { return HitsRequired > 0 ? HitsRequired : RequiredHits; }
};
