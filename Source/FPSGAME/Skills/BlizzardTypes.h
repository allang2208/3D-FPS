#pragma once
#include "CoreMinimal.h"

/** game-dev's level terms use L, while stepped cooldown/duration use (L-1)/19. */
struct FBlizzardTuning
{
    float DamageBase=5,DamagePerLevel=2,MagicBase=.12f,MagicPerLevel=.02f;
    float IntelligenceBase=.12f,IntelligencePerLevel=.02f;
    float RadiusXBase=200,RadiusXPerLevel=8,RadiusYBase=124,RadiusYPerLevel=5;
    float ManaCost=150,Cooldown=40,CooldownReduction=5,Range=650,UnitsToCM=1.5f;
    float Duration=5,DurationGrowth=5,TickSeconds=.5f,ChillSeconds=2.5f,ChillSlow=.035f;
    int32 ChillStacks=1,HitExperience=1,KillExperience=6,MultiHitExperience=5,MultiKillExperience=10;
    bool bRequiresStaff=false;
};
struct FBlizzardCast
{
    float Damage=0,RadiusX=0,RadiusY=0,ManaCost=0,Cooldown=0,Range=0,Duration=0;
    float TickSeconds=.5f,ChillSeconds=2.5f,ChillSlow=.035f,CastSpeed=1;
    float CriticalChance=0,CriticalDamageBonus=0,MagicPenetration=0,MagicDamageBonus=0,CastHasteDuration=5;
    int32 ChillStacks=1,CastHasteStacks=0;
    bool bGrantChain=false,bRequiresStaff=false;
};
struct FBlizzardRewards
{
    int32 Hits=0,Kills=0,CriticalHits=0,CriticalKills=0;
    bool bMultiHit=false;
};
