#pragma once
#include "CollisionQueryParams.h"

// The rider and their mount occupy the same attack origin. Other combatants
// still see this horse through the ordinary world collision channels.
struct FFPSAttackQuery : FCollisionQueryParams
{
    FFPSAttackQuery(FName Tag,const TStatId& Stat,bool Complex,const AActor* Attacker);
};
