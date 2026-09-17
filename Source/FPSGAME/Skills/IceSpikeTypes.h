#pragma once
#include "CoreMinimal.h"

struct FIceSpikeTuning
{
    // Magic attack only, like the fireball: no independent intelligence multiplier.
    // Roughly 30% below the original magic+intelligence formula: fixed terms *0.7 and the
    // magic coefficient *0.7/0.6, because the old expression also scaled with intelligence.
    double DamageBase=21, DamagePerLevel=3.5, MagicBase=1.4, MagicPerLevel=.2917;
    int32 CountBase=2, CountLevelStep=5, HitExperience=4, KillExperience=12, MultiHitExperience=10, MultiKillExperience=10;
    float Cooldown=12, MinimumCooldown=8, ManaCost=30, ManaCostPerLevel=2, HoverDuration=30, Speed=1600, Range=800, UnitsToCM=1.5f;
    /** Downward acceleration of the flying shards, cm/s². 0 keeps the old straight shot. */
    float Gravity=400;
};
struct FIceSpikeCast
{
    double DamageBase=0, MagicMultiplier=0, MagicContribution=0;
    float Damage=0, CriticalChance=0, CriticalDamageBonus=0, MagicPenetration=0, MagicDamageBonus=0;
    float ManaCost=30, Cooldown=12, HoverDuration=30, Speed=2400, Range=1200, CastSpeed=1;
    float Gravity=400;
    int32 Count=2;
    int32 CastHasteStacks=0;
    float CastHasteDuration=5,ChillDuration=3,ChillSlow=0;
    bool bGrantChain=false;
};
struct FIceSpikeRewards
{
    int32 Hits=0, Kills=0, CriticalHits=0, CriticalKills=0;
    TMap<TWeakObjectPtr<AActor>,int64> KillRewards;
};
