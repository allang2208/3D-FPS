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
    // 0 = default (rocks need three hits; surface soil digs one 20 cm layer per
    // swing, so it asks for one). Trees no longer use this: they resolve through
    // MaxHealth below and keep RequiredHits only as the calibrated reference.
    int32 HitsRequired = 0;
    int32 HitsNeeded() const { return HitsRequired > 0 ? HitsRequired : RequiredHits; }
    /**
     * 生命值上限（2026-09-25）。>0 走生命值口径：一次挥砍按伤害扣血，归零才倒下。
     * 当前只有树木填它（`ProductionTreeHealth::MaxHealth`）；岩块与表土保持 0 ＝ 命中数口径。
     */
    double MaxHealth = 0;
};
