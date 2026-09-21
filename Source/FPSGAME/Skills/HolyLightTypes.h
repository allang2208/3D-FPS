#pragma once
#include "CoreMinimal.h"

struct FHolyLightTuning
{
    double AmountBase=5,AmountPerLevel=5,MagicBase=.25,MagicPerLevel=.25;
    double IntelligenceBase=1,IntelligencePerLevel=.5,WisdomBase=1,WisdomPerLevel=.5;
    float ManaCost=30,Cooldown=10,CooldownStepReduction=1,Range=600,AimRadius=200,UnitsToCM=1.5f;
    int32 CooldownLevelStep=5,HitExperience=5,KillExperience=10;
    float ZombieMultiplier=2,Duration=2,Fade=.4f,TopWidth=60,BottomWidth=110,Height=1400,DissolveRatio=.28f;
};
struct FHolyLightCast
{
    double AmountBase=0,MagicMultiplier=0,IntelligenceMultiplier=0,WisdomMultiplier=0;
    float Damage=0,Healing=0,ManaCost=30,Cooldown=10,Range=900,AimRadius=300,ZombieMultiplier=2;
    float Duration=2,Fade=.4f,TopWidth=90,BottomWidth=165,Height=2100,DissolveRatio=.28f;
    float CriticalChance=0,CriticalDamageBonus=0,MagicPenetration=0,MagicDamageBonus=0,CastSpeed=1;
    int32 RenewalStacks=0,HealHasteStacks=0,CastHasteStacks=0;
    float RenewalSeconds=3,HealHasteSeconds=5,CastHasteDuration=5;
    bool bGrantChain=false;
};
struct FHolyLightRewards
{
    int32 Hits=0,Kills=0,CriticalHits=0,CriticalKills=0;
    TMap<TWeakObjectPtr<AActor>,int64> KillRewards;
};
