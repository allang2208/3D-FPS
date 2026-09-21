#pragma once

#include "CoreMinimal.h"
#include "../Skills/WhirlwindTypes.h"

// Whirlwind V5 presentation. Phase is also the damage sweep's angular clock;
// camera lean/impact never feed back into controller yaw or attack geometry.
namespace WhirlwindFeel
{
inline float Ease(float U)
{
    U=FMath::Clamp(U,0.f,1.f);
    return U*U*U*(U*(U*6.f-15.f)+10.f);
}

inline float SpinTime(float Time,const FWhirlwindTuning& T)
{
    return FMath::Clamp((Time-T.ReadySeconds)/T.SpinSeconds,0.f,1.f);
}

// Short smooth acceleration, sustained sweep, deliberate braking. Integrating
// smoothstep velocity keeps both boundaries still and the two turns connected.
constexpr float Acceleration=.12f,Braking=.18f;
constexpr float SpeedArea=1.f-.5f*(Acceleration+Braking);
inline float RampArea(float U) { return U*U*U-.5f*U*U*U*U; }
inline float Phase(float Time,const FWhirlwindTuning& T)
{
    const float U=SpinTime(Time,T);
    if(U<Acceleration)return Acceleration*RampArea(U/Acceleration)/SpeedArea;
    if(U>1.f-Braking)return 1.f-Braking*RampArea((1.f-U)/Braking)/SpeedArea;
    return (U-.5f*Acceleration)/SpeedArea;
}
inline float Speed(float Time,const FWhirlwindTuning& T)
{
    const float U=SpinTime(Time,T);
    return FMath::SmoothStep(0.f,Acceleration,U)*(1.f-FMath::SmoothStep(1.f-Braking,1.f,U));
}

inline void Camera(float Time,const FWhirlwindTuning& T,float ImpactAge,float ImpactStrength,
    FVector& Location,FRotator& Rotation)
{
    const float Direction=T.TurnDegrees<0.f?-1.f:1.f;
    const float SpinEnd=T.ReadySeconds+T.SpinSeconds;
    const float Recover=Ease((Time-SpinEnd)/T.RecoverSeconds);
    const float Load=Ease(Time/(T.ReadySeconds*.68f));
    const float Release=Ease((Time-T.ReadySeconds*.68f)/(T.ReadySeconds*.32f+T.SpinSeconds*.12f));
    // Body loads against the sweep, leans into the extended blade, then plants.
    const float Coil=Load*(1.f-Release);
    const float Carry=Release*(1.f-Recover);
    const float Fast=Speed(Time,T);
    Location=FVector(-3.f*Coil+1.8f*Carry,-Direction*(1.6f*Coil-1.2f*Carry),-1.8f*Coil-1.1f*Carry);
    Rotation=FRotator(1.2f*Coil-.65f*Carry,0.f,-Direction*1.4f*Coil+Direction*(1.8f*Carry+.7f*Fast));
    // A single plant after the rotation. This is recovery, not another hit.
    const float PlantU=FMath::Clamp((Time-SpinEnd)/(T.RecoverSeconds*.40f),0.f,1.f);
    const float Plant=FMath::Square(FMath::Sin(PI*PlantU));
    Location.Z-=1.6f*Plant;
    Rotation.Pitch+=.9f*Plant;
    Rotation.Roll-=Direction*.65f*Plant;

    // Immediate directional resistance at confirmed contact, held with the
    // animation during hitstop, followed by a short recoil and release.
    if(ImpactAge<.16f)
    {
        const float Envelope=1.f-Ease(ImpactAge/.16f);
        const float Kick=FMath::Exp(-24.f*ImpactAge)*FMath::Cos(38.f*ImpactAge)*Envelope*ImpactStrength;
        Location+=FVector(-2.4f,-Direction*1.1f,.55f)*Kick;
        Rotation+=FRotator(1.45f,0.f,-Direction*1.2f)*Kick;
    }
}
}
