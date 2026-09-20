#pragma once
#include "CoreMinimal.h"

/** Retiming and local camera offsets for the existing Sightline4 pickaxe clips. */
namespace ProductionPickaxeImpact
{
    inline constexpr float HitStopSeconds=.24f;
    inline constexpr float PryEndSeconds=.42f;
    inline constexpr float ExtractEndSeconds=.51f;
    inline constexpr float HitRecoverSeconds=.80f;

    struct FCameraKey
    {
        float Time;
        FVector Angles; // Pitch, yaw, roll in degrees.
        FVector Position; // Camera-local forward, right, up in cm.
    };

    inline FCameraKey CameraCurve(TConstArrayView<FCameraKey> Keys,float Time)
    {
        if(Time<=Keys[0].Time)return Keys[0];
        for(int32 I=1;I<Keys.Num();++I)
            if(Time<=Keys[I].Time)
            {
                const float Alpha=FMath::SmoothStep(Keys[I-1].Time,Keys[I].Time,Time);
                return {Time,FMath::Lerp(Keys[I-1].Angles,Keys[I].Angles,Alpha),
                    FMath::Lerp(Keys[I-1].Position,Keys[I].Position,Alpha)};
            }
        return Keys.Last();
    }

    inline float SourceHitTime(float Age)
    {
        // Sightline4 is a .44 s source clip representing .56 s of game time.
        // Its first .20 game seconds hold contact; .20-.29 is the authored tug.
        // Keep that exact contact pose through the hold and rigid pry, then
        // resume the original arm animation without changing any grip/joint.
        constexpr float SourceHoldEnd=.44f*.20f/.56f;
        constexpr float SourceTugEnd=.44f*.29f/.56f;
        if(Age<=PryEndSeconds)return 0.f;
        if(Age<=ExtractEndSeconds)
            return FMath::Lerp(SourceHoldEnd,SourceTugEnd,
                (Age-PryEndSeconds)/(ExtractEndSeconds-PryEndSeconds));
        return FMath::Lerp(SourceTugEnd,.44f,FMath::Clamp(
            (Age-ExtractEndSeconds)/(HitRecoverSeconds-ExtractEndSeconds),0.f,1.f));
    }

    inline float PryDegrees(float Age)
    {
        // A single small up/down loosening action, after the true frozen hold.
        // Both hands and the tool receive this together, around their grip.
        static const FVector2D Keys[]={{HitStopSeconds,0.f},{.29f,2.4f},{.355f,-1.6f},{PryEndSeconds,0.f}};
        if(Age<=HitStopSeconds || Age>=PryEndSeconds)return 0.f;
        for(int32 I=1;I<UE_ARRAY_COUNT(Keys);++I)
            if(Age<=Keys[I].X)
            {
                const float U=(Age-Keys[I-1].X)/(Keys[I].X-Keys[I-1].X);
                const float Ease=U*U*U*(10.f-15.f*U+6.f*U*U);
                return FMath::Lerp(Keys[I-1].Y,Keys[I].Y,Ease);
            }
        return 0.f;
    }

    inline void SampleCamera(float Seconds,float ContactSeconds,float SwingSeconds,
        bool bConfirmedHit,float Strength,FVector& Location,FRotator& Rotation)
    {
        static const FCameraKey Swing[]={
            {0.f,{0,0,0},{0,0,0}},
            {.32f,{2.1f,0,.15f},{-.9f,0,.7f}},
            {.47f,{2.4f,0,.15f},{-1.1f,0,.8f}},
            {.54f,{.5f,0,.05f},{-.15f,0,.1f}},
            {.60f,{-1.7f,-.1f,.1f},{.7f,0,-.75f}},
            {.685f,{-2.2f,-.1f,.12f},{.8f,0,-1.0f}},
            {.90f,{-.65f,0,0},{-.1f,0,-.25f}},
            {1.16f,{0,0,0},{0,0,0}}
        };
        // One heavy downward impulse and a monotonic settle. No oscillation,
        // noise or second extraction kick is applied to the camera.
        static const FCameraKey Hit[]={
            {0.f,{-1.7f,-.1f,.1f},{.7f,0,-.75f}},
            {.04f,{-10.5f,-.45f,.7f},{-2.1f,0,-3.4f}},
            {.085f,{-10.5f,-.45f,.7f},{-2.1f,0,-3.4f}},
            {HitStopSeconds,{-5.2f,-.25f,.35f},{-1.1f,0,-1.8f}},
            {PryEndSeconds,{-.9f,0,.05f},{-.15f,0,-.35f}},
            {ExtractEndSeconds,{0,0,0},{0,0,0}},
            {HitRecoverSeconds,{0,0,0},{0,0,0}}
        };
        const float Time=bConfirmedHit?Seconds-ContactSeconds:
            (Seconds<ContactSeconds?.60f*Seconds/ContactSeconds:
                .60f+.56f*(Seconds-ContactSeconds)/(SwingSeconds-ContactSeconds));
        const auto Pose=bConfirmedHit?CameraCurve(Hit,Time):CameraCurve(Swing,Time);
        const float Scale=FMath::Max(0.f,Strength);
        Location=Pose.Position*Scale;
        Rotation=FRotator(Pose.Angles.X,Pose.Angles.Y,Pose.Angles.Z)*Scale;
    }
}
