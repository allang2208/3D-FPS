#pragma once
#include "CoreMinimal.h"
#include "LightningTypes.generated.h"

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
USTRUCT()
struct FLightningCast
{
    GENERATED_BODY()
    UPROPERTY() double DamageBase=0; UPROPERTY() double MagicMultiplier=0; UPROPERTY() double IntelligenceMultiplier=0;
    UPROPERTY() float Damage=0; UPROPERTY() float OverloadDamage=0; UPROPERTY() float ManaCost=30; UPROPERTY() float Cooldown=12; UPROPERTY() float Range=900; UPROPERTY() float AimRadius=300; UPROPERTY() float ChainRange=300;
    UPROPERTY() float ChainDecay=.1f; UPROPERTY() float StunSeconds=.75f; UPROPERTY() float Duration=.5f; UPROPERTY() float Fade=.25f; UPROPERTY() float Jitter=.09f;
    UPROPERTY() float CriticalChance=0; UPROPERTY() float CriticalDamageBonus=0; UPROPERTY() float MagicPenetration=0; UPROPERTY() float MagicDamageBonus=0; UPROPERTY() float CastSpeed=1;
    UPROPERTY() int32 Count=1; UPROPERTY() int32 Segments=10; UPROPERTY() int32 ElectrifyStacks=1; UPROPERTY() int32 OverloadStacks=5; UPROPERTY() int32 CastHasteStacks=0;
    UPROPERTY() float ElectrifyDuration=4; UPROPERTY() float ElectricBonusPerStack=.03f; UPROPERTY() float OverloadStun=1.2f; UPROPERTY() float OverloadRange=225; UPROPERTY() float CastHasteDuration=5;
    UPROPERTY() bool bGrantChain=false;
    UPROPERTY() float StunExtensionSeconds=0;
};
struct FLightningRewards
{
    int32 Hits=0, Kills=0, CriticalHits=0, CriticalKills=0;
    TMap<TWeakObjectPtr<AActor>,int64> KillRewards;
};
