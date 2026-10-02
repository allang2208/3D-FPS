#pragma once
#include "CoreMinimal.h"
#include "../../UI/ColdSteelStatusModel.h"

namespace UnarmedPunch
{
    // The combo nibble's reserved 8 means a normal fist only with no item declaration.
    inline constexpr uint8 AttackMeta=0x08;
    inline constexpr float BaseDamage=8.f, ReachCM=90.f, QueryRadiusCM=14.f;
    inline float Damage(const UColdSteelStatusModel* Profile)
    {return FMath::Max(0.f,BaseDamage+(Profile?float(Profile->Derived(TEXT("atk"))):0.f));}
}
