#pragma once

#include "CoreMinimal.h"

namespace SmithHammerTiming
{
    // Seconds from committing to a strike (on the server).
    constexpr float Swing = .21f;
    constexpr float Contact = .38f;
    constexpr float End = 1.10f;
    constexpr float AttackInterval = 1.70f;
    // Natural_Slash2 is 76 frame intervals at 60 Hz. The authored marker is
    // on the incoming side. One frame later the head reaches the frontal lane.
    inline float ClipLengthSeconds(bool bClose) { return (bClose ? 72.f : 76.f) / 60.f; }
    constexpr float AuthoredContact = 12.f / 60.f;
    constexpr float HeadRadius = 14.f;
    constexpr float CloseStanceYaw = 55.f;
    struct FHeadKey { FVector Head; FVector Spine; };
    // Equipped steel head centre and spine_01, actor axes in cm from the feet.
    // Frames 10..15 of the unblended strike. The authority needs no rendered bones.
    inline const FHeadKey FrontHeadKeys[] = {
        {{74.21,-84.23,99.00}, {2.98,6.23,75.03}},
        {{100.32,-58.61,99.27}, {2.45,5.10,76.88}},
        {{113.93,-33.57,107.42}, {1.96,3.97,78.72}},
        {{118.42,-8.85,126.74}, {1.78,2.84,80.72}},
        {{114.83,8.00,147.88}, {1.61,1.73,82.72}},
        {{97.71,19.38,177.74}, {1.81,1.00,84.52}}
    };
    // Natural_Slash1 travels across the lead side, inside the long strike's arc.
    inline const FHeadKey CloseHeadKeys[] = {
        {{1.29,22.46,37.41}, {-3.46,-10.02,74.36}},
        {{21.77,-8.02,43.71}, {-2.91,-9.87,76.39}},
        {{28.65,-42.52,62.59}, {-2.31,-9.72,78.42}},
        {{34.95,-61.84,83.23}, {-1.32,-9.58,80.43}},
        {{29.98,-78.94,108.80}, {-.31,-9.47,82.44}},
        {{20.70,-89.09,133.39}, {1.22,-9.50,84.80}}
    };
    inline TConstArrayView<FHeadKey> HeadKeys(bool bClose)
    {
        return bClose ? MakeArrayView(CloseHeadKeys) : MakeArrayView(FrontHeadKeys);
    }
    inline FVector AimAxis(bool bClose)
    {
        return bClose ? FVector::RightVector.RotateAngleAxis(-CloseStanceYaw, FVector::UpVector) : FVector::RightVector;
    }
    constexpr float FirstHeadTime = 10.f / 60.f;
    constexpr float LastHeadTime = 15.f / 60.f;

    inline float SampleClip(float Age, float ContactMarker, float ClipLength)
    {
        if (ClipLength <= 0.f) return 0.f;
        const float Marker = FMath::Clamp((ContactMarker > 0.f ? ContactMarker : AuthoredContact)
            + 1.f / 60.f, 0.f, ClipLength);
        const float LiftRate = Marker / Contact;
        const float ReturnRate = (ClipLength - Marker) / (End - Contact);
        const float ImpactRate = FMath::Min(1.9f * LiftRate, 2.f * ReturnRate);
        // Accelerate into contact, then carry that same velocity through the
        // marker. Ease out during recovery instead of pausing on the hit frame.
        if (Age <= Contact)
            return FMath::CubicInterp(0.f, .35f * Marker, Marker, Contact * ImpactRate,
                FMath::Clamp(Age / Contact, 0.f, 1.f));
        return FMath::CubicInterp(Marker, (End - Contact) * ImpactRate, ClipLength,
            .5f * (ClipLength - Marker), FMath::Clamp((Age - Contact) / (End - Contact), 0.f, 1.f));
    }
}
