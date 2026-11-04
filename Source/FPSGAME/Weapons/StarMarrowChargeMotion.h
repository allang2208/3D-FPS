#pragma once
#include "CoreMinimal.h"

/** Seconds match A_StarMarrow_Charge at 120 Hz. Camera motion is cosmetic, never aim/control rotation. */
namespace StarMarrowChargeMotion
{
    inline constexpr float Duration=2.2f;
    inline constexpr float Release=1.64f;
    inline float Ease(float A,float B,float T)
    {
        const float X=FMath::Clamp((T-A)/(B-A),0.f,1.f);
        return X*X*X*(10.f+X*(-15.f+6.f*X));
    }

    // Generated with RhythmV4/rhythm.py. X=elapsed, Y=reference phase,
    // Z=monotone phase derivative. Pose baking uses the identical Hermite curve.
    inline float ReferenceTime(float T)
    {
        static const FVector Keys[]={
            {0.00000000f,0.00000000f,0.54162313f},
            {0.22000000f,0.12000000f,0.55005269f},
            {0.58000000f,0.32000000f,0.59055118f},
            {0.82000000f,0.47000000f,0.35298013f},
            {1.40000000f,0.60000000f,0.35346151f},
            {1.57000000f,0.70000000f,0.61814366f},
            {1.64000000f,0.74500000f,0.72080606f},
            {1.82000000f,0.90000000f,0.78616583f},
            {2.10000000f,1.10000000f,0.76243544f},
            {2.50000000f,1.43000000f,0.86504854f},
            {2.70000000f,1.61000000f,0.90000000f},
            {2.80000000f,1.70000000f,0.90000000f}};
        T=FMath::Clamp(T,0.f,Duration);
        int32 I=0;
        while(I<UE_ARRAY_COUNT(Keys)-2 && T>Keys[I+1].X)++I;
        const float Span=Keys[I+1].X-Keys[I].X;
        return FMath::CubicInterp(Keys[I].Y,Keys[I].Z*Span,
            Keys[I+1].Y,Keys[I+1].Z*Span,(T-Keys[I].X)/Span);
    }
    inline float Tension(float T)
    {
        const float Envelope=Ease(.62f,1.08f,T)*(1.f-Ease(1.45f,1.64f,T));
        const float Age=T-.62f;
        return Envelope*(FMath::Sin(2.f*PI*8.f*Age)+.24f*FMath::Sin(2.f*PI*11.5f*Age));
    }
    inline float Recoil(float T,float Start,float Hz,float Decay,float End)
    {
        const float Age=FMath::Max(0.f,T-Start);
        return FMath::Sin(Age*2.f*PI*Hz)*FMath::Exp(-Decay*Age)*(1.f-Ease(End-.12f,End,T));
    }
    inline void Camera(float T,FVector& Location,FRotator& Rotation)
    {
        if(T<=0.f||T>=Duration)return;
        // Fixed-background tracking of BV1hCJFzQEyR 59.4-61.1 s, sampled at
        // 0.1 s. Remove aim drift, then carry the wipe pressure into the lift.
        // These are camera-space pitch/yaw/roll, not independent random noise.
        static const FVector Keys[]={
            {0.f,0.f,0.f},{.931f,-1.052f,.150f},{1.356f,-1.342f,.596f},
            {1.432f,-1.334f,1.143f},{1.286f,-.691f,-.910f},{1.189f,-.250f,-1.351f},
            {1.241f,.370f,-.803f},{1.231f,.423f,.916f},{.383f,.262f,1.157f},
            {1.073f,-.473f,.087f},{2.122f,-1.377f,-.418f},{2.437f,-1.729f,.516f},
            {1.815f,-1.375f,1.542f},{.822f,-.687f,1.785f},{.195f,-.385f,.464f},
            {.291f,-.217f,-.131f},{.053f,.005f,-.016f},{0.f,0.f,0.f}};
        const float Phase=ReferenceTime(T);
        const float Frame=Phase*10.f;
        const int32 I=FMath::Clamp(FMath::FloorToInt(Frame),0,UE_ARRAY_COUNT(Keys)-2);
        const FVector Before=Keys[FMath::Max(0,I-1)];
        const FVector After=Keys[FMath::Min(int32(UE_ARRAY_COUNT(Keys))-1,I+2)];
        const FVector Value=FMath::CubicInterp(Keys[I],(Keys[I+1]-Before)*.5f,
            Keys[I+1],(After-Keys[I])*.5f,Frame-I);
        // V7 returns directly to idle from 1.8 to 2.2 seconds. Keep the
        // accepted charge/release camera, then settle in the same short window.
        const float ReturnWeight=1.f-Ease(1.8f,Duration,T);
        const float Envelope=Ease(0.f,.14f,Phase)*ReturnWeight;
        Rotation+=FRotator(Value.X,Value.Y,Value.Z)*Envelope;
        // Carry the same blade tension and short release into the viewpoint;
        // the free left hand has no copy of this oscillation in its pose.
        const float Load=Tension(T);
        const float Impact=Recoil(T,Release,6.5f,13.f,1.96f);
        Rotation+=FRotator(.14f*Load+.55f*Impact,
            .045f*Load,.10f*Load-.25f*Impact)*ReturnWeight;
        // Perspective displacement is already represented by the tracked
        // angular curve. A second translation kick would double the impact.
        (void)Location;
    }
}
