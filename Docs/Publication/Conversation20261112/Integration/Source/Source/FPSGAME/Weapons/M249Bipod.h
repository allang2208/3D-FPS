#pragma once
#include "CoreMinimal.h"
// Measured from the current factory meshes. Closed legs fold toward the muzzle.
namespace M249Bipod
{
inline constexpr const TCHAR* Base=TEXT("/Game/Weapons/M249/Bipod/SM_M249_Bipod_Base");
inline constexpr const TCHAR* LegA=TEXT("/Game/Weapons/M249/Bipod/SM_M249_Bipod_LegA");
inline constexpr const TCHAR* LegB=TEXT("/Game/Weapons/M249/Bipod/SM_M249_Bipod_LegB");
inline const FVector Hinge=FVector(0.104412422,42.088184357,0.920630872);
inline const FVector Pivots[]={FVector(0.501539290,42.029293060,0.950084746),FVector(-0.292714447,42.147075653,0.891176999)};
inline const FVector Tips[]={FVector(15.072072983,0.122409821,-20.265741348),FVector(-11.324442863,0.051898956,-22.575149536)};
inline const FVector FoldedTips[]={FVector(2.234328985,25.025917053,-2.567855835),FVector(-1.754580021,25.025917053,-2.916841030)};
inline FQuat LegRotation(int32 I,float OpenWeight)
{
    const FQuat Closed=FQuat::FindBetweenNormals(Tips[I].GetSafeNormal(),FoldedTips[I].GetSafeNormal());
    const float T=FMath::Clamp(OpenWeight,0.f,1.f);
    return FQuat::Slerp(Closed,FQuat::Identity,T*T*(3.f-2.f*T));
}
}
