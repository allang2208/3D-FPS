#pragma once
#include "CoreMinimal.h"

namespace MeteorGround
{
/** Sight is required when locking. Release rechecks the same ground/range,
 *  allowing the caster to move behind cover after the point was accepted. */
FPSGAME_API bool Validate(APawn* Caster,float Range,FVector& Point,FVector& Normal,bool bRequireSight,FString& Failure);
}
