#pragma once
#include "CoreMinimal.h"
namespace FireMagic
{
FPSGAME_API TArray<AActor*> GroundTargets(APawn* Shooter,const FVector& Center,const FVector& Normal,float Radius);
/** Ground / ceiling traces ignore living bodies, but retain world geometry. */
FPSGAME_API bool TraceSurface(APawn* Shooter,const FVector& Start,const FVector& End,FHitResult& Hit);
}
