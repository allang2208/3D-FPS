#pragma once
#include "CoreMinimal.h"

struct FFireballTuning
{
    float MagicBase=8.5f, MagicPerLevel=.5f;
    float UnitsToCM=1.5f, RadiusBase=80, RadiusPerLevel=5, Speed=1600, Range=1200;
    float RadiusScale=1.65f;
    float ManaCost=50, ManaCostPerLevel=2, Cooldown=12, MinimumCooldown=8, HoverDuration=30;
    int32 HitExperience=8, MultiHitExperience=20, MultiKillExperience=20;
};

// One immutable cast: later level-ups and equipment/attribute changes do not alter it.
struct FFireballCast
{
    float CriticalChance=0, CriticalDamageBonus=0, MagicPenetration=0, MagicDamageBonus=0;
    // Radius is the single world-space extent shared by damage and impact presentation.
    float Damage=0, Radius=0, Speed=0, Range=0, MagicMultiplier=0;
    float ManaCost=50, Cooldown=12, HoverDuration=30;
};
