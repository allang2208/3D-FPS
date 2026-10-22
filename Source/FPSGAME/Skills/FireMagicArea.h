#pragma once
#include "CoreMinimal.h"
namespace FireMagic
{
inline constexpr float GroundBand=100.f;
FPSGAME_API FVector GroundPoint(const AActor* Target,float* BodyRadius=nullptr);
FPSGAME_API TArray<AActor*> GroundTargets(APawn* Shooter,const FVector& Center,const FVector& Normal,float Radius);
/** Ground / ceiling traces retain rails; area sight may pass open barriers. */
FPSGAME_API bool TraceSurface(APawn* Shooter,const FVector& Start,const FVector& End,FHitResult& Hit,bool bAreaSight=false);
}
