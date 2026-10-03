#pragma once
#include "CoreMinimal.h"
#include "FireMagicTypes.generated.h"

namespace FireMagic
{
inline bool IsSkill(FName Id){return Id==TEXT("meteor")||Id==TEXT("flameArmor");}
}

/** Both spells retain game-dev's level K (1..20), not K-1, in damage terms. */
struct FFireMagicTuning
{
    float DamageBase=120,DamagePerLevel=12,MagicBase=2.2f,MagicPerLevel=.4f,IntelligenceBase=2.4f,IntelligencePerLevel=.45f;
    float AuraDamageBase=8,AuraDamagePerLevel=3,AuraMagicBase=.25f,AuraMagicPerLevel=.03f,AuraIntelligenceBase=.25f,AuraIntelligencePerLevel=.03f;
    float RadiusBase=140,RadiusPerLevel=5,AuraRadiusBase=120,AuraRadiusPerLevel=4,UnitsToCM=1.5f;
    float ManaBase=100,ManaGrowth=50,Cooldown=32,CooldownReduction=4,DurationBase=3,DurationGrowth=3;
    float Range=650,FallSeconds=.65f,TickSeconds=.5f,StunSeconds=2,BurnSeconds=3.5f,BurnMultiplier=.5f;
    float AuraBurnSeconds=2.5f,AuraBurnMultiplier=.3f;
    int32 BurnStacks=3,AuraBurnStacks=1,HitExperience=2,KillExperience=10,MultiHitExperience=8,MultiKillExperience=10;
    bool bRequiresStaff=false;
};

USTRUCT()
struct FFireMagicCast
{
    GENERATED_BODY()
    UPROPERTY() FName Skill=TEXT("meteor");
    UPROPERTY() float Damage=0; UPROPERTY() float AuraDamage=0; UPROPERTY() float MagicAttack=0; UPROPERTY() float Radius=0; UPROPERTY() float AuraRadius=0; UPROPERTY() float ManaCost=0; UPROPERTY() float Cooldown=0; UPROPERTY() float Duration=0; UPROPERTY() float Range=0;
    UPROPERTY() float FallSeconds=.65f; UPROPERTY() float TickSeconds=.5f; UPROPERTY() float StunSeconds=0; UPROPERTY() float BurnSeconds=0; UPROPERTY() float BurnMultiplier=0; UPROPERTY() float AuraBurnSeconds=0; UPROPERTY() float AuraBurnMultiplier=0;
    UPROPERTY() float CriticalChance=0; UPROPERTY() float CriticalDamageBonus=0; UPROPERTY() float MagicPenetration=0; UPROPERTY() float MagicDamageBonus=0; UPROPERTY() float CastSpeed=1;
    UPROPERTY() int32 BurnStacks=0; UPROPERTY() int32 AuraBurnStacks=0; UPROPERTY() int32 CastHasteStacks=0;
    UPROPERTY() float CastHasteDuration=5;
    UPROPERTY() bool bGrantChain=false; UPROPERTY() bool bRequiresStaff=false;
};

/** Skill training is aggregated until the field / buff ends; character kills are immediate. */
struct FFireMagicRewards
{
    int32 Hits=0,Kills=0,CriticalHits=0,CriticalKills=0;
    bool bMultiHit=false;
};
