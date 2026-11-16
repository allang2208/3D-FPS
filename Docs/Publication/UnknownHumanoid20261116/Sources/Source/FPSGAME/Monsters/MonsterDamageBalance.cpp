#include "MonsterDamageBalance.h"
#include "../Skills/FireballTypes.h"
#include "../Skills/IceSpikeTypes.h"
#include "../Skills/IceWallTypes.h"
#include "../Skills/BlizzardTypes.h"
#include "../Skills/LightningTypes.h"
#include "../Skills/HolyLightTypes.h"
#include "../Skills/FireMagicTypes.h"
#include "../Skills/ElectricMagicTypes.h"
#include "../Skills/ElementalArrowTypes.h"
#include "../Skills/MagicArrowRainTypes.h"
#include "../Skills/IlluminationArrowTypes.h"

namespace
{
    using MonsterDamageBalance::Limit;
    using UnknownDamageBalance::Tier;
    // Fold the real equipment multiplier into the copied payload before balancing.
    // Critical damage is separate and at most +15% for hostile spells.
    template<class T> float Magic(T& C)
    {
        const float Factor=FMath::Max(0.f,1.f+C.MagicDamageBonus)*.45f;
        C.MagicDamageBonus=0.f;
        C.CriticalDamageBonus=FMath::Clamp(C.CriticalDamageBonus,0.f,.15f);
        C.MagicPenetration=FMath::Clamp(C.MagicPenetration,0.f,.15f);
        return Factor;
    }
    void Lightning(int32 Level,FLightningCast& C,float Ceiling,float Overload)
    {
        const float Factor=Magic(C);
        C.Damage=Limit(C.Damage*Factor,Ceiling);
        C.OverloadDamage=Limit(C.OverloadDamage*Factor,Overload);
        C.ElectricBonusPerStack=FMath::Min(C.ElectricBonusPerStack,.02f);
        C.OverloadStacks=FMath::Min(C.OverloadStacks,5);
    }
    float Ticks(float Duration,float Interval)
    {return FMath::Max(1.f,FMath::CeilToFloat(Duration/FMath::Max(.05f,Interval)));}
}

float UnknownDamageBalance::Tier(int32 Level,float At10,float At20,float At30)
{
    const float L=FMath::Clamp(float(Level),10.f,30.f);
    return L<=20.f?FMath::Lerp(At10,At20,(L-10.f)/10.f):FMath::Lerp(At20,At30,(L-20.f)/10.f);
}
float UnknownDamageBalance::Weapon(float Raw,FName Type,bool Gun,bool Automatic,int32 Level,float Interval,int32 Contacts)
{
    float Ceiling=Tier(Level,54,66,78);
    if(Gun)
    {
        Ceiling=Automatic?Tier(Level,14,18,22):Type==TEXT("sniper")?Tier(Level,65,80,95):
            Type==TEXT("shotgun")?Tier(Level,50,62,74):Tier(Level,26,34,42);
        // A shell's ceiling is shared by all pellets. Every trigger type also
        // shares a time budget (including very fast semi-auto shotguns).
        // The existing 20% / 33% accuracy stays intact.
        const float DPS=Automatic?Tier(Level,100,125,150):Tier(Level,110,140,170);
        Ceiling=FMath::Min(Ceiling,DPS*FMath::Max(.01f,Interval));
    }
    else if(Type==TEXT("bow"))Ceiling=Tier(Level,35,45,55);
    else Ceiling=FMath::Min(Ceiling,Tier(Level,40,50,60)*FMath::Max(.05f,Interval)/FMath::Max(1,Contacts));
    return Limit(Raw*.55f,Ceiling);
}
float UnknownDamageBalance::Piercing(float Raw,int32 Level)
{return Limit(Raw,Tier(Level,70,85,100));}
void UnknownDamageBalance::Tune(int32 Level,FFireballCast& C)
{
    C.Damage=Limit(C.Damage*Magic(C),Tier(Level,48,60,72));
    const float Burn=Tier(Level,2,3,4);
    C.BurnMagicAttack=FMath::Min(C.BurnMagicAttack,Burn/FMath::Max(.01f,C.BurnMultiplier));
    C.SpecBurnMagicAttack=FMath::Min(C.SpecBurnMagicAttack,Burn/FMath::Max(.01f,C.SpecBurnMultiplier));
    C.SpecBurnStacks=FMath::Min(C.SpecBurnStacks,1);
}
void UnknownDamageBalance::Tune(int32 Level,FIceSpikeCast& C)
{
    // Every shard can hit the same victim: this is a volley budget, not per shard.
    C.Damage=Limit(C.Damage*Magic(C)*FMath::Max(1,C.Count),Tier(Level,48,60,72))/FMath::Max(1,C.Count);
}
void UnknownDamageBalance::Tune(int32 Level,FIceWallCast& C)
{C.Damage=Limit(C.Damage*.45f,Tier(Level,28,36,44));}
void UnknownDamageBalance::Tune(int32 Level,FBlizzardCast& C)
{C.Damage=Limit(C.Damage*Magic(C),Tier(Level,10,13,16)*C.TickSeconds);}
void UnknownDamageBalance::Tune(int32 Level,FLightningCast& C)
{Lightning(Level,C,Tier(Level,44,54,64),Tier(Level,12,16,20));}
void UnknownDamageBalance::Tune(int32 Level,FHolyLightCast& C)
{C.Damage=Limit(C.Damage*Magic(C),Tier(Level,36,46,56));}
void UnknownDamageBalance::Tune(int32 Level,FFireMagicCast& C)
{
    const float Factor=Magic(C);
    if(C.Skill==TEXT("dragonBreath"))
        C.Damage=Limit(C.Damage*Factor,Tier(Level,84,108,132)/Ticks(C.Duration,C.TickSeconds));
    else C.Damage=Limit(C.Damage*Factor,C.Skill==TEXT("flameArmor")?Tier(Level,16,20,24):Tier(Level,72,86,100));
    const float DPS=C.Skill==TEXT("flameArmor")?Tier(Level,6,8,10):Tier(Level,5,7,9);
    C.AuraDamage=Limit(C.AuraDamage*Factor,DPS*C.TickSeconds);
    const float BurnMultiplier=FMath::Max3(C.BurnMultiplier,C.AuraBurnMultiplier,C.PendantBurnMultiplier);
    C.MagicAttack=FMath::Min(C.MagicAttack,Tier(Level,2,3,4)/FMath::Max(.01f,BurnMultiplier));
    C.BurnStacks=FMath::Min(C.BurnStacks,1);C.AuraBurnStacks=FMath::Min(C.AuraBurnStacks,1);
}
void UnknownDamageBalance::Tune(int32 Level,FElectricMagicCast& C,bool Lance)
{
    if(Lance)
    {
        C.StackDamage=FMath::Min(C.StackDamage,.03f);
        // Before overload there can be four stacks. Reserve for a full charge
        // and five stacks, so the last-moment stack change cannot bypass tuning.
        const float FullCharge=FMath::Max(1.f,C.ChargeBonus)*(1.f+5.f*C.StackDamage);
        Lightning(Level,C.Hit,Tier(Level,72,88,104)/FullCharge,Tier(Level,12,16,20));
    }
    else Lightning(Level,C.Hit,Tier(Level,12,16,20)*C.StrikeSeconds,Tier(Level,8,10,12));
}
void UnknownDamageBalance::Tune(int32 Level,FElementalArrowCast& C)
{
    // Elemental impact is additional to the physical arrow, once per target.
    if(C.Element==EArrowElement::Fire)
    {Tune(Level,C.Fire);C.Fire.Damage=Limit(C.Fire.Damage,Tier(Level,18,24,30));}
    else if(C.Element==EArrowElement::Ice)
    {C.Ice.Damage=Limit(C.Ice.Damage*Magic(C.Ice),Tier(Level,16,22,28));}
    else if(C.Element==EArrowElement::Lightning)
        Lightning(Level,C.Lightning,Tier(Level,18,24,30),Tier(Level,8,10,12));
}
void UnknownDamageBalance::Tune(int32 Level,FMagicArrowRainCast& C)
{
    C.Damage=Limit(C.Damage*FMath::Max(0.f,1.f+C.MagicDamageBonus)*.45f,Tier(Level,58,72,86));
    C.MagicDamageBonus=0.f;C.CriticalDamageBonus=FMath::Clamp(C.CriticalDamageBonus,0.f,.15f);
}
void UnknownDamageBalance::Tune(int32 Level,FIlluminationArrowCast& C)
{C.DamageBonus=FMath::Min(C.DamageBonus,Tier(Level,.05f,.06f,.07f));}
