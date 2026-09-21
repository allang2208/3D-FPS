#pragma once
#include "CoreMinimal.h"

// World-122 lightning: keep the original formula; 1 source unit = 1.5 cm.
struct FLightningTuning
{
    double DamageBase=20, DamagePerLevel=10, MagicBase=1.15, MagicPerLevel=.25, IntelligenceBase=1, IntelligencePerLevel=.25;
    float ManaCost=30, Cooldown=12, AimRadius=200, Range=600, ChainRange=200, UnitsToCM=1.5f;
    float ChainDecay=.1f, StunBase=.75f, StunPerLevel=.02f, Duration=.5f, Fade=.25f, Jitter=.09f;
    int32 CountBase=1, CountLevelStep=5, Segments=10, ElectrifyStacks=1;
    float ElectrifyDuration=4, ElectricBonusPerStack=.03f;
    int32 OverloadStacks=5;
    float OverloadStun=1.2f, OverloadRange=150, OverloadBase=20, OverloadMagic=1.2f, OverloadIntelligence=1.2f;
    int32 HitExperience=4, KillExperience=10, MultiHitExperience=10, MultiKillExperience=10;
};
struct FLightningCast
{
    double DamageBase=0, MagicMultiplier=0, IntelligenceMultiplier=0;
    float Damage=0, OverloadDamage=0, ManaCost=30, Cooldown=12, Range=900, AimRadius=300, ChainRange=300;
    float ChainDecay=.1f, StunSeconds=.75f, Duration=.5f, Fade=.25f, Jitter=.09f;
    float CriticalChance=0, CriticalDamageBonus=0, MagicPenetration=0, MagicDamageBonus=0, CastSpeed=1;
    int32 Count=1, Segments=10, ElectrifyStacks=1, OverloadStacks=5, CastHasteStacks=0;
    float ElectrifyDuration=4, ElectricBonusPerStack=.03f, OverloadStun=1.2f, OverloadRange=225, CastHasteDuration=5;
    bool bGrantChain=false;
};
struct FLightningRewards
{
    int32 Hits=0, Kills=0, CriticalHits=0, CriticalKills=0;
    TMap<TWeakObjectPtr<AActor>,int64> KillRewards;
};
