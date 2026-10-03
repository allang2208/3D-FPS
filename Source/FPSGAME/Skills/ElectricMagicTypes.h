#pragma once
#include "CoreMinimal.h"
#include "LightningTypes.h"
#include "ElectricMagicTypes.generated.h"

namespace ElectricMagic
{
    inline bool IsSkill(FName Id){return Id==TEXT("stormDomain")||Id==TEXT("thunderLance");}
}
struct FElectricMagicTuning
{
    float DamageBase=25,DamagePerLevel=4,MagicBase=.45f,MagicPerLevel=.05f,IntelligenceBase=.45f,IntelligencePerLevel=.05f;
    float ManaBase=80,ManaGrowth=40,Cooldown=30,CooldownReduction=0,Duration=10,DurationGrowth=3;
    float RadiusBase=220,RadiusPerLevel=8,RangeBase=550,RangePerLevel=0,UnitsToCM=1.5f;
    float StrikeSeconds=.9f,ChainRange=160,ChainDecay=.3f,StunSeconds=.25f;
    int32 ChainExtraBase=1,ChainLevelStep=8,ElectrifyStacks=1;
    float ElectrifySeconds=4,MinCharge=.5f,MaxCharge=2.5f,ChargeBonus=1.3f,StackDamage=.1f;
    float HalfWidth=40,KnockbackBase=50,KnockbackGrowth=100,EndRadius=90;
    // Lance beam lifetime only; stormDomain arcs keep their own hold/fade.
    float BeamHold=.45f,BeamFade=.6f;
    int32 HitExperience=1,KillExperience=6,MultiHitExperience=5,MultiKillExperience=10;
};
USTRUCT()
struct FElectricMagicCast
{
    GENERATED_BODY()
    UPROPERTY() FLightningCast Hit;
    UPROPERTY() float Radius=342; UPROPERTY() float Duration=10; UPROPERTY() float StrikeSeconds=.9f; UPROPERTY() float MinCharge=.5f; UPROPERTY() float MaxCharge=2.5f;
    UPROPERTY() float ChargeBonus=1.3f; UPROPERTY() float StackDamage=.1f; UPROPERTY() float HalfWidth=60; UPROPERTY() float Knockback=75; UPROPERTY() float EndRadius=135;
};
struct FElectricMagicRewards
{
    FLightningRewards Hit;
    bool bMultiHit=false;
};
