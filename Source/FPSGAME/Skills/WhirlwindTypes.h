#pragma once
#include "CoreMinimal.h"

/** Original game-dev whirlwind formulas use K (not K-1), K=1..20. */
struct FWhirlwindTuning
{
    float DamageBase=1.5f,DamagePerLevel=.1f;
    float CooldownBase=10.f,CooldownReduction=.2f;
    float StaminaBase=20.f,StaminaPerLevel=1.f;
    float RadiusBase=120.f,RadiusPerLevel=5.f,MeleeRadiusBonus=80.f,UnitsToCM=1.5f;
    float Knockback=250.f,StunSeconds=2.5f;
    float ReadySeconds=.5f,SpinSeconds=.8f,RecoverSeconds=.52f;
    float TurnDegrees=-720.f,HitStopSeconds=.045f,HitStopBudget=.135f,MotionBlur=.65f;
};

struct FWhirlwindCast
{
    float DamageMultiplier=1.6f,Damage=0.f,CooldownSeconds=9.8f,StaminaCost=21.f;
    float RadiusCM=307.5f,KnockbackCM=375.f,StunSeconds=2.5f;
};
