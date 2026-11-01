#pragma once
#include "CoreMinimal.h"

// M24 stock-neck regrip and strike. Keep pose/contact on the authored clock.
namespace M24QuickMeleeMotion
{
constexpr float Length=.9f;
constexpr float Release=.05f;
constexpr float Cock=.15f;
constexpr float Contact=.25f;
constexpr float Follow=.325f;
// Uses the same damped contact impulse as other rifles, after hit confirmation.
constexpr float ImpactScale=.34f;

inline void Camera(float SourceAge,float ClipLength,FVector& Location,FRotator& Rotation)
{
    const float Time=FMath::Clamp(SourceAge/FMath::Max(.01f,ClipLength)*Length,0.f,Length);
    constexpr float Times[]={0.f,Release,Cock,Contact,Follow,.50f,Length};
    const FVector Positions[]={FVector::ZeroVector,FVector(-.25f,.15f,.12f),FVector(-1.f,.38f,.45f),
        FVector(1.5f,-.5f,-.7f),FVector(.2f,-.15f,-.18f),FVector(-.32f,.08f,.15f),FVector::ZeroVector};
    const FRotator Rotations[]={FRotator::ZeroRotator,FRotator(.15f,-.2f,-.2f),FRotator(.7f,-1.1f,-.8f),
        FRotator(-1.6f,.8f,1.05f),FRotator(-.3f,.24f,.3f),FRotator(.2f,-.1f,-.13f),FRotator::ZeroRotator};
    int32 I=0;while(I<UE_ARRAY_COUNT(Times)-2&&Time>Times[I+1])++I;
    const float T=(Time-Times[I])/(Times[I+1]-Times[I]);
    const float Weight=T*T*T*(10.f+T*(-15.f+6.f*T));
    Location=FMath::Lerp(Positions[I],Positions[I+1],Weight);
    Rotation=FMath::Lerp(Rotations[I],Rotations[I+1],Weight);
}
}
