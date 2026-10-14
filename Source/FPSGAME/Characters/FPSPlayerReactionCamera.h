#pragma once
#include "CoreMinimal.h"

struct FFPSBodyReactionState;
struct FMinimalViewInfo;

namespace FPSReactionMotion
{
// Exact critically damped response: continuous position and velocity on entry,
// recovery and a stun refresh; no frame-dependent linear lerp or random jumps.
struct FEnvelope
{
    float Value=0.f,Velocity=0.f;
    float Step(float Target,float Delta,float Frequency)
    {
        const float T=FMath::Max(0.f,Delta),X=Value-Target;
        const float B=Velocity+Frequency*X,E=FMath::Exp(-Frequency*T);
        Value=Target+(X+B*T)*E;Velocity=(Velocity-Frequency*B*T)*E;
        return Value;
    }
};
}

/** Owner-view presentation only. No control rotation, aiming or status mutation. */
struct FFPSPlayerReactionCamera
{
    void Apply(const FFPSBodyReactionState& State,float Now,float Delta,float Scale,bool bEnabled,FMinimalViewInfo& View);
private:
    struct FHit
    {
        float StartedAt=-100.f,Strength=0.f,Phase=0.f;
        FVector Direction=FVector::BackwardVector;
    };
    FHit Hits[4];
    uint16 LastHit=0;
    uint8 NextHit=0;
    FPSReactionMotion::FEnvelope Stun;
    float SwayAge=0.f;
};
