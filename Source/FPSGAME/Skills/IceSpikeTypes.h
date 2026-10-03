#pragma once
#include "CoreMinimal.h"
#include "IceSpikeTypes.generated.h"

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
USTRUCT()
struct FIceSpikeCast
{
    GENERATED_BODY()
    UPROPERTY() double DamageBase=0; UPROPERTY() double MagicMultiplier=0; UPROPERTY() double MagicContribution=0;
    UPROPERTY() float Damage=0; UPROPERTY() float CriticalChance=0; UPROPERTY() float CriticalDamageBonus=0; UPROPERTY() float MagicPenetration=0; UPROPERTY() float MagicDamageBonus=0;
    UPROPERTY() float ManaCost=30; UPROPERTY() float Cooldown=12; UPROPERTY() float HoverDuration=30; UPROPERTY() float Speed=2400; UPROPERTY() float Range=1200; UPROPERTY() float CastSpeed=1;
    UPROPERTY() float Gravity=400;
    UPROPERTY() int32 Count=2;
    UPROPERTY() int32 CastHasteStacks=0;
    UPROPERTY() float CastHasteDuration=5; UPROPERTY() float ChillDuration=3; UPROPERTY() float ChillSlow=0;
    UPROPERTY() bool bGrantChain=false;
};
struct FIceSpikeRewards
{
    int32 Hits=0, Kills=0, CriticalHits=0, CriticalKills=0;
    TMap<TWeakObjectPtr<AActor>,int64> KillRewards;
};
