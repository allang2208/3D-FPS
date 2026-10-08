#pragma once
#include "CoreMinimal.h"

namespace BoundCongregateTentacleTiming
{
inline constexpr float PreviousStrikeSeconds=.62f;

struct FReleaseSample { float Phase,Rate; };

inline FReleaseSample Release(float Elapsed,float Duration)
{
    const float U=FMath::Clamp(Elapsed/FMath::Max(.001f,Duration),0.f,1.f);
    if(U<=0.f)return {0.f,0.f};
    if(U>=1.f)return {1.f,0.f};
    // Normalized time / recorded-pose phase / phase velocity. The middle
    // segment delivers the stroke; only a short terminal segment settles it.
    float T0=0.f,T1=.14f,P0=0.f,P1=.06f,V0=0.f,V1=.9f;
    if(U>=.8f){T0=.8f;T1=1.f;P0=.94f;P1=1.f;V0=.65f;V1=0.f;}
    else if(U>=.14f){T0=.14f;T1=.8f;P0=.06f;P1=.94f;V0=.9f;V1=.65f;}
    const float Span=T1-T0,S=(U-T0)/Span,S2=S*S,S3=S2*S;
    const float Phase=(2*S3-3*S2+1)*P0+(S3-2*S2+S)*Span*V0+
        (-2*S3+3*S2)*P1+(S3-S2)*Span*V1;
    const float Rate=((6*S2-6*S)*P0+(-6*S2+6*S)*P1)/Span+
        (3*S2-4*S+1)*V0+(3*S2-2*S)*V1;
    return {Phase,Rate};
}

inline float RecoveryPhase(float Elapsed,float Duration)
{
    return FMath::SmoothStep(0.f,1.f,Elapsed/FMath::Max(.001f,Duration));
}
}
