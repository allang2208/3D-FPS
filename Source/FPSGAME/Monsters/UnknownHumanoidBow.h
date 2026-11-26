#pragma once
#include "../Weapons/Bow/BowStats.h"
#include "../Skills/ColdSteelSkillTypes.h"
class UStaticMesh;

enum class EUnknownArrow : uint8 { Normal, Piercing, Fire, Ice, Lightning, Rain, Illumination };
struct FUnknownArchery
{
    ColdSteelBow::FStats Stats;
    FElementalArrowCast Elements[3];
    FMagicArrowRainCast Rain;
    FIlluminationArrowCast Illumination;
    FColdSteelSkillShot Shot;
    EUnknownArrow Selected=EUnknownArrow::Normal, Previous=EUnknownArrow::Normal;
    double Available[7]={};
    double SwitchAfter=0,RetreatAfter=0;
    double SafeSince=-1;
    bool bRetreatFailed=false;
    float Gravity=520.f,LaunchSpeed=9800.f;
    float Mana=0.f, MaxMana=0.f, ManaRegen=0.f, ElementHoldMana=0.f;
    float ReleaseMana=0.f, HoldMana=0.f;
    double DrawAccountedAt=0.;
    FString Ammo;
    TSoftObjectPtr<UStaticMesh> ArrowMesh;
    float ArrowLength=76.f,ArrowRadius=.3f;
    bool bPerfectPending=false;
};
