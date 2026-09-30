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
    // 「三次有效命中」只作为标定参考存活：树木/岩块的 StrikeDamage 折算、旧档命中数
    // （1..3）到生命比例的读档换算都以它为基准。命中数结算已于 2026-09-30 退役——
    // 树木与岩块走 MaxHealth 生命值口径，表土走「一挥一层」的固定挖掘。
    /**
     * 生命值上限（2026-09-25 树木，2026-09-30 岩块统一）。>0 走生命值口径：一次挥砍按
     * 伤害扣血，归零才倒下/破碎（树木 `ProductionTreeHealth::MaxHealth`，岩块 RockMaxHealth）；
     * 表土保持 0 ＝ 固定挖掘，一挥一层。
     */
    double MaxHealth = 0;
    /**
     * 树桩目标（2026-09-28）：被砍倒的树留下的桩，有自己的生命（StumpMaxHealth），
     * 劈尽掉一块木材且不再生倒树；与幼树生长互不影响。解析/结算/掉落据此分流。
     */
    bool bStump = false;
};
