#pragma once
#include "CoreMinimal.h"

struct FIceSpikeTuning
{
    double DamageBase=30, DamagePerLevel=5, MagicBase=1.2, MagicPerLevel=.25, IntBase=1.2, IntPerLevel=.25;
    int32 CountBase=2, CountLevelStep=5, HitExperience=4, KillExperience=12, MultiHitExperience=10, MultiKillExperience=10;
    float Cooldown=10, ManaCost=30, HoverDuration=30, Speed=1600, Range=800, UnitsToCM=1.5f;
};
struct FIceSpikeCast
{
    double DamageBase=0, MagicMultiplier=0, IntMultiplier=0, MagicContribution=0, IntContribution=0;
    float Damage=0, CriticalChance=0, CriticalDamageBonus=0, MagicPenetration=0, MagicDamageBonus=0;
    float ManaCost=30, Cooldown=10, HoverDuration=30, Speed=2400, Range=1200, CastSpeed=1;
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
