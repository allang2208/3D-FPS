#pragma once
#include "CoreMinimal.h"

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

struct FFireMagicCast
{
    FName Skill=TEXT("meteor");
    float Damage=0,AuraDamage=0,MagicAttack=0,Radius=0,AuraRadius=0,ManaCost=0,Cooldown=0,Duration=0,Range=0;
    float FallSeconds=.65f,TickSeconds=.5f,StunSeconds=0,BurnSeconds=0,BurnMultiplier=0,AuraBurnSeconds=0,AuraBurnMultiplier=0;
    float CriticalChance=0,CriticalDamageBonus=0,MagicPenetration=0,MagicDamageBonus=0,CastSpeed=1;
    int32 BurnStacks=0,AuraBurnStacks=0,CastHasteStacks=0;
    float CastHasteDuration=5;
    bool bGrantChain=false,bRequiresStaff=false;
};

/** Skill training is aggregated until the field / buff ends; character kills are immediate. */
struct FFireMagicRewards
{
    int32 Hits=0,Kills=0,CriticalHits=0,CriticalKills=0;
    bool bMultiHit=false;
};
