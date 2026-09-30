#pragma once
#include "CoreMinimal.h"

class AFPSIceWall;
class AActor;

/** Neutral cover interception; callers keep their own attack/contact clocks. */
namespace IceWallCombat
{
    AFPSIceWall* BlockingWall(const AActor* Attacker,const AActor* Target,float Reach,float MinimumFacing=-1.f);
    bool ApplyMelee(AActor* Attacker,const AActor* Target,float Reach,float Damage,float MinimumFacing=.35f);
}
