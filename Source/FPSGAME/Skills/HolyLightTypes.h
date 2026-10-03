#pragma once
#include "CoreMinimal.h"
#include "HolyLightTypes.generated.h"

struct FHolyLightTuning
{
    double AmountBase=5,AmountPerLevel=5,MagicBase=.25,MagicPerLevel=.25;
    double IntelligenceBase=1,IntelligencePerLevel=.5,WisdomBase=1,WisdomPerLevel=.5;
    float ManaCost=30,Cooldown=10,CooldownStepReduction=1,Range=600,AimRadius=200,UnitsToCM=1.5f;
    int32 CooldownLevelStep=5,HitExperience=5,KillExperience=10;
    float ZombieMultiplier=2,Duration=2,Fade=.4f,TopWidth=60,BottomWidth=110,Height=1400,DissolveRatio=.28f;
};
USTRUCT()
struct FHolyLightCast
{
    GENERATED_BODY()
    UPROPERTY() double AmountBase=0; UPROPERTY() double MagicMultiplier=0; UPROPERTY() double IntelligenceMultiplier=0; UPROPERTY() double WisdomMultiplier=0;
    UPROPERTY() float Damage=0; UPROPERTY() float Healing=0; UPROPERTY() float ManaCost=30; UPROPERTY() float Cooldown=10; UPROPERTY() float Range=900; UPROPERTY() float AimRadius=300; UPROPERTY() float ZombieMultiplier=2;
    UPROPERTY() float Duration=2; UPROPERTY() float Fade=.4f; UPROPERTY() float TopWidth=90; UPROPERTY() float BottomWidth=165; UPROPERTY() float Height=2100; UPROPERTY() float DissolveRatio=.28f;
    UPROPERTY() float CriticalChance=0; UPROPERTY() float CriticalDamageBonus=0; UPROPERTY() float MagicPenetration=0; UPROPERTY() float MagicDamageBonus=0; UPROPERTY() float CastSpeed=1;
    UPROPERTY() int32 RenewalStacks=0; UPROPERTY() int32 HealHasteStacks=0; UPROPERTY() int32 CastHasteStacks=0;
    UPROPERTY() float RenewalSeconds=3; UPROPERTY() float HealHasteSeconds=5; UPROPERTY() float CastHasteDuration=5;
    UPROPERTY() bool bGrantChain=false;
};
struct FHolyLightRewards
{
    int32 Hits=0,Kills=0,CriticalHits=0,CriticalKills=0;
    TMap<TWeakObjectPtr<AActor>,int64> KillRewards;
};
