#pragma once
#include "CoreMinimal.h"

// Matches the ImpactV2 overhead asset. Output is camera-local cm/degrees, before
// the existing sword multiplier and the player's shared camera comfort scale.
namespace RuneSwordOverheadFeel
{
    inline constexpr float ReleaseStart=1.11f;
    inline constexpr float ImpactTime=1.31f;
    inline constexpr float ArrestEnd=1.39f;
    inline constexpr float End=2.60f;

    inline void Camera(float Time,bool Confirmed,float HitAge,float HitStrength,FVector& Location,FRotator& Rotation)
    {
        const FVector Load(-4.f,0.f,2.f),Follow(7.f,0.f,-6.5f);
        const FRotator Raised(4.5f,0.f,0.f),Down(-12.5f,0.f,0.f);
        if(Time<=ReleaseStart)
        {
            const float Gather=FMath::SmoothStep(0.f,.60f,Time);
            Location=Load*Gather;Rotation=Raised*Gather;
        }
        else if(Time<=ImpactTime)
        {
            const float U=FMath::Clamp((Time-ReleaseStart)/(ImpactTime-ReleaseStart),0.f,1.f);
            const float Fall=FMath::Pow(U,2.15f);
            Location=FMath::Lerp(Load,Follow,Fall);Rotation=FMath::Lerp(Raised,Down,Fall);
        }
        else
        {
            const float Weight=Time<=ArrestEnd?1.f:(Time<=1.85f?
                FMath::Lerp(1.f,.12f,FMath::SmoothStep(ArrestEnd,1.85f,Time)):
                .12f*(1.f-FMath::SmoothStep(1.85f,End,Time)));
            Location=Follow*Weight;Rotation=Down*Weight;
            // One downward arrest, followed by a short, rapidly decaying vibration.
            const float Age=Time-ImpactTime;
            if(Age<.16f)
            {
                const float Pulse=FMath::Square(FMath::Sin(PI*FMath::Clamp(Age/.11f,0.f,1.f)));
                const float Rattle=FMath::Sin(Age*105.f)*FMath::Exp(-24.f*Age)*(1.f-FMath::SmoothStep(0.f,.16f,Age));
                Location.Z-=2.f*Pulse;Rotation.Pitch-=3.2f*Pulse;
                Rotation.Pitch+=1.7f*Rattle;Rotation.Roll+=.55f*Rattle;
            }
        }
        if(Confirmed && HitAge<.28f)
        {
            const float Punch=FMath::SmoothStep(0.f,.028f,HitAge)*(1.f-FMath::SmoothStep(.028f,.23f,HitAge));
            const float Rattle=FMath::Sin(HitAge*115.f)*FMath::Exp(-21.f*HitAge)*(1.f-FMath::SmoothStep(0.f,.28f,HitAge));
            Location+=FVector(-4.f,0.f,-3.f)*Punch*HitStrength;
            Rotation.Pitch+=(-5.f*Punch+2.3f*Rattle)*HitStrength;
            Rotation.Roll+=.7f*Rattle*HitStrength;
        }
    }
}
