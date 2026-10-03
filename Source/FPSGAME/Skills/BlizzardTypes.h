#pragma once
#include "CoreMinimal.h"
#include "BlizzardTypes.generated.h"

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
USTRUCT()
struct FBlizzardCast
{
    GENERATED_BODY()
    UPROPERTY() float Damage=0; UPROPERTY() float RadiusX=0; UPROPERTY() float RadiusY=0; UPROPERTY() float ManaCost=0; UPROPERTY() float Cooldown=0; UPROPERTY() float Range=0; UPROPERTY() float Duration=0;
    UPROPERTY() float TickSeconds=.5f; UPROPERTY() float ChillSeconds=2.5f; UPROPERTY() float ChillSlow=.035f; UPROPERTY() float CastSpeed=1;
    UPROPERTY() float CriticalChance=0; UPROPERTY() float CriticalDamageBonus=0; UPROPERTY() float MagicPenetration=0; UPROPERTY() float MagicDamageBonus=0; UPROPERTY() float CastHasteDuration=5;
    UPROPERTY() int32 ChillStacks=1; UPROPERTY() int32 CastHasteStacks=0;
    UPROPERTY() bool bGrantChain=false; UPROPERTY() bool bRequiresStaff=false;
};
struct FBlizzardRewards
{
    int32 Hits=0,Kills=0,CriticalHits=0,CriticalKills=0;
    bool bMultiHit=false;
};
