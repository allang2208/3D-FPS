#pragma once
#include "CoreMinimal.h"
#include "Super90WeaponAssets.h"

namespace Super90Spread
{
inline float ConeRadians(int32 Projectiles,bool Aiming,float PelletMultiplier=1.f)
{
    return Projectiles>1?FMath::DegreesToRadians(Super90WeaponAssets::PelletConeDegrees)
        *(Aiming?Super90WeaponAssets::ADSPelletSpreadScale:1.f)*PelletMultiplier:0.f;
}
// Hip aim is a square distribution. Enclose its corners and the additional
// pellet cone, so the ring is a real boundary for both buckshot and slugs.
inline float RingTangent(float HipTangent,int32 Projectiles,float PelletMultiplier=1.f)
{
    return FMath::Tan(FMath::Atan(FMath::Sqrt(2.f)*HipTangent)+ConeRadians(Projectiles,false,PelletMultiplier));
}
// Divide the fan into one band per projectile. Jitter within each band keeps
// its horizontal coverage while avoiding the same stamped pattern every shot.
// The caller owns the RNG so local prediction and authority consume the same seed.
inline FVector HorizontalFan(const FVector& Center,float HalfAngle,int32 Index,int32 Count,float Jitter)
{
    if(Count<=1)return Center;
    const float Offset=2.f*(Index+.5f+(Jitter-.5f)*.65f)/Count-1.f;
    const FVector Right=FRotationMatrix(Center.Rotation()).GetUnitAxis(EAxis::Y);
    return (Center+Right*FMath::Tan(Offset*HalfAngle)).GetSafeNormal();
}
inline FVector2D FanRingTangents(float HipTangent,int32 Projectiles,float PelletMultiplier=1.f)
{
    if(Projectiles<=1)return FVector2D(RingTangent(HipTangent,Projectiles,PelletMultiplier));
    // Enclose the horizontal fan plus the independent square hip-aim error.
    return FVector2D(FMath::Sqrt(2.f)*FMath::Tan(FMath::Atan(HipTangent)+ConeRadians(Projectiles,false,PelletMultiplier)),
        FMath::Sqrt(2.f)*HipTangent);
}
inline int32 Seed(uint32 Sequence){return int32(Sequence*196314165u+907633515u);}
}
