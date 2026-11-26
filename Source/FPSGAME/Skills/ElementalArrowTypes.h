#pragma once
#include "CoreMinimal.h"
#include "../Combat/CombatChill.h"
#include "FireballTypes.h"
#include "IceSpikeTypes.h"
#include "LightningTypes.h"
#include "ElementalArrowTypes.generated.h"

UENUM()
enum class EArrowElement : uint8 { None, Fire, Ice, Lightning };

struct FElementalArrowTuning
{
    float FireDamageMultiplier=1.5f,IceDamageMultiplier=1.25f,LightningDamageMultiplier=1.25f;
    float FireGrowth=.05f,FireLateGrowth=.08f,ControlGrowth=.05f,ControlLateGrowth=.08f;
    int32 GrowthChangeLevel=10;
    float ManaCostMultiplier=1.5f,ManaPerSecond=3.f;
    float RadiusMultiplier=2.f;
    float ChillSeconds=5.f,ChillSlow=CombatChill::SlowPerStack,StunSeconds=1.5f;
};

// Authority-only, captured on release. The physical bow snapshot remains independent.
struct FElementalArrowCast
{
    EArrowElement Element=EArrowElement::None;
    FFireballCast Fire;
    FIceSpikeCast Ice;
    FLightningCast Lightning;
    float Radius=0, ManaCost=0, Cooldown=0;
    TSharedPtr<struct FEclipseBowShot> EclipseShot;
};

namespace ElementalArrow
{
inline float ManaCost(const FElementalArrowTuning& T,float SpellCost)
{return FMath::CeilToFloat(SpellCost*T.ManaCostMultiplier);}
inline float DamageMultiplier(const FElementalArrowTuning& T,EArrowElement E,int32 Level)
{
    const int32 K=FMath::Clamp(Level,1,20)-1;
    const int32 Early=FMath::Min(K,T.GrowthChangeLevel-1),Late=K-Early;
    if(E==EArrowElement::Fire)return T.FireDamageMultiplier+Early*T.FireGrowth+Late*T.FireLateGrowth;
    if(E==EArrowElement::Ice||E==EArrowElement::Lightning)
        return (E==EArrowElement::Ice?T.IceDamageMultiplier:T.LightningDamageMultiplier)+Early*T.ControlGrowth+Late*T.ControlLateGrowth;
    return 1.f;
}
inline bool IsElement(EArrowElement E){return E>=EArrowElement::Fire&&E<=EArrowElement::Lightning;}
inline FName Spell(EArrowElement E){if(E==EArrowElement::Fire)return TEXT("fireball");if(E==EArrowElement::Ice)return TEXT("iceSpike");if(E==EArrowElement::Lightning)return TEXT("lightningStrike");return NAME_None;}
inline const TCHAR* Name(EArrowElement E){return E==EArrowElement::Fire?TEXT("火焰箭"):E==EArrowElement::Ice?TEXT("寒冰箭"):TEXT("闪电箭");}
inline FString Icon(EArrowElement E){return E==EArrowElement::Fire?TEXT("Skills/elemental_arrow_fire.png"):E==EArrowElement::Ice?TEXT("Skills/elemental_arrow_ice.png"):TEXT("Skills/elemental_arrow_lightning.png");}
inline FLinearColor Color(EArrowElement E){return E==EArrowElement::Fire?FLinearColor(1,.25f,.035f):E==EArrowElement::Ice?FLinearColor(.25f,.8f,1):FLinearColor(.55f,.3f,1);}
inline constexpr float HoldSeconds=.30f, ChillSeconds=5.f, ChillSlow=CombatChill::SlowPerStack, StunSeconds=1.5f;
    inline constexpr const TCHAR* Flame=TEXT("/Game/Skills/ElementalArrow20261109/WarmFireV2/NS_ElementalArrowFire.NS_ElementalArrowFire");
inline constexpr const TCHAR* Mist=TEXT("/Game/Skills/ElementalArrow20261109/ColdMistV2/NS_ArrowColdMist.NS_ArrowColdMist");
inline constexpr const TCHAR* IceImpact=TEXT("/Game/Skills/ElementalArrow20261109/ColdMistV2/NS_ArrowColdBurst.NS_ArrowColdBurst");
inline constexpr const TCHAR* IceSound=TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact");
inline constexpr const TCHAR* Chain=TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain");
inline constexpr const TCHAR* Blade=TEXT("/Game/Weapons/ElectrifiedMelee/NS_ElectrifiedBlade.NS_ElectrifiedBlade");
inline constexpr const TCHAR* Explosion=TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic.NS_FireballImpactRealistic");
inline constexpr const TCHAR* Wave=TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/M_FireballHeatShockwave.M_FireballHeatShockwave");
inline constexpr const TCHAR* FireSound=TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/S_FireballImpactLayered.S_FireballImpactLayered");
inline TArray<FSoftObjectPath> Assets(){TArray<FSoftObjectPath> R;for(const auto* P:{Flame,Mist,IceImpact,IceSound,Chain,Blade,Explosion,Wave,FireSound})R.Emplace(P);return R;}
}
