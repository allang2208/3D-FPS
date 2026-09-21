#pragma once
#include "CoreMinimal.h"

/** game-dev dashAttack 基础下劈；不包含火焰／多段突刺变体。 */
struct FDashAttackTuning
{
    float DamageBase=1.75f, DamagePerLevel=.05f;
    float ReadySeconds=1.f, ReadyReductionPerLevel=.03f, StaminaCost=20.f;
    // 旧突进参数槽位保留热更新布局；当前下劈不产生前冲或回弹。
    float Distance=0.f, SpeedMultiplier=0.f, BounceRatio=0.f, UnitsToCM=1.5f;
    float RangeBase=6.f, RangePerLevel=6.f, RangeFlat=55.f;
    float KnockbackBonus=188.f, KnockbackPerLevel=6.f, ArcDegrees=60.f;
};

struct FDashAttackCast
{
    float Damage=0.f, DamageMultiplier=1.8f, ReadySeconds=1.f, StaminaCost=20.f;
    float DistanceCM=0.f, BounceRatio=0.f, RangeCM=0.f, RangeBonusCM=100.5f;
    float KnockbackCM=0.f, KnockbackBonusCM=291.f, ArcDegrees=60.f;
};
