#pragma once
#include "AlchemyInteractionAssets.h"

// One action clock for the spoon, liquid column, received volume and return.
namespace AlchemyBottling
{
inline constexpr float DipAt=.65f,LiftAt=1.f,AlignedAt=1.65f;
inline constexpr float FlowStart=1.9f,FlowEnd=3.1f,Ramp=.18f,Flight=.16f;
inline constexpr float StraightenAt=3.28f,ReturnAt=3.5f,RestAt=4.35f;
// Bring dispensing toward the centre of the work view, clear of the pot wall.
inline const FVector BottlePosition(195,-134,116);
inline const FVector Mouth(0,0,9);
inline const FVector Spout(-4.1,0,-18.4);
inline const FVector PourPoint=BottlePosition+Mouth+FVector(0,0,13);
inline float Flow(float T)
{return AlchemyInteraction::Smooth((T-FlowStart)/Ramp)*(1-AlchemyInteraction::Smooth((T-(FlowEnd-Ramp))/Ramp));}
inline float Emitted(float T)
{
    const float X=FMath::Clamp(T-FlowStart,0.f,FlowEnd-FlowStart);
    const float Duration=FlowEnd-FlowStart;
    // Integral of the eased flow envelope. The bottle receives this same
    // volume one flight-time later, instead of filling before the stream lands.
    if(X<Ramp){const float U=X/Ramp;return Ramp*(U*U*U-.5f*U*U*U*U)/(Duration-Ramp);}
    if(X<=Duration-Ramp)return (X-.5f*Ramp)/(Duration-Ramp);
    const float U=(X-(Duration-Ramp))/Ramp;
    return (Duration-1.5f*Ramp+Ramp*(U-U*U*U+.5f*U*U*U*U))/(Duration-Ramp);
}
inline float Received(float T){return Emitted(T-Flight);}
inline float Tilt(float T)
{return AlchemyInteraction::Smooth((T-AlignedAt)/(FlowStart-AlignedAt))*(1-AlchemyInteraction::Smooth((T-StraightenAt)/(ReturnAt-StraightenAt)));}
}
