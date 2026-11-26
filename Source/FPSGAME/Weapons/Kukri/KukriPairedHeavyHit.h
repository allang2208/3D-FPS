#pragma once
#include "../../Skills/ColdSteelSkillTypes.h"
#include "Engine/HitResult.h"

// Only contacts that actually landed enter a paired heavy settlement.
struct FKukriHeavyContact
{
    FHitResult Hit;
    FVector Direction=FVector::ZeroVector;
    float Damage=0.f;
    FColdSteelSkillShot Shot;
};

struct FKukriPairedHeavyHit
{
    FKukriHeavyContact Second;
    float Applied[2]={0.f,0.f};
    bool Critical[2]={false,false};
};

struct FKukriHeavyContacts
{
    FKukriHeavyContact Blades[2];
    uint8 Mask=0;
    bool bContactPresented=false;
};
