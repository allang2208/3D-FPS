#pragma once
#include "CoreMinimal.h"

// One shared camera impulse at the damage-query frame for every quick-melee
// weapon. CameraMotionScale is applied by the character after this sample.
namespace QuickCombatImpactShake
{
    constexpr float Duration = .38f;

    inline void Add(float Age, FVector& Location, FRotator& Rotation)
    {
        if(Age<0.f||Age>=Duration)return;
        const float Envelope=1.f-FMath::SmoothStep(.18f,Duration,Age);
        // Cosine starts at full impulse on the query frame, then recoils in the
        // opposite direction. A lighter, faster vibration rides the main kick.
        const float Kick=FMath::Exp(-9.f*Age)*FMath::Cos(44.f*Age)*Envelope;
        const float Rattle=FMath::Exp(-16.f*Age)*FMath::Sin(90.f*Age)*Envelope;
        Location+=FVector(-20.f,3.f,-4.f)*Kick+FVector(0.f,1.2f,.8f)*Rattle;
        Rotation+=FRotator(-26.f,9.f,8.f)*Kick+FRotator(3.f,-2.f,2.f)*Rattle;
    }
}
