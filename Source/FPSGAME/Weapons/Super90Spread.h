#pragma once
#include "CoreMinimal.h"
#include "Super90WeaponAssets.h"

namespace Super90Spread
{
inline float ConeRadians(int32 Projectiles,bool Aiming)
{
    return Projectiles>1?FMath::DegreesToRadians(Super90WeaponAssets::PelletConeDegrees)
        *(Aiming?Super90WeaponAssets::ADSPelletSpreadScale:1.f):0.f;
}
// Hip aim is a square distribution. Enclose its corners and the additional
// pellet cone, so the ring is a real boundary for both buckshot and slugs.
inline float RingTangent(float HipTangent,int32 Projectiles)
{
    return FMath::Tan(FMath::Atan(FMath::Sqrt(2.f)*HipTangent)+ConeRadians(Projectiles,false));
}
inline int32 Seed(uint32 Sequence){return int32(Sequence*196314165u+907633515u);}
}
