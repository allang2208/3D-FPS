#pragma once

#include "CoreMinimal.h"

/**
 * Player knockdown (2026-11-14): fall on the back, lie, get up. One clock for the first-person camera and the
 * two-handed sword arms clip A_RuneSword_Knockdown (2.60 s, SourceAssets/PlayerKnockdown20261114).
 * Reference: Kubold FPP Two Handed Sword (YouTube NTrzxPIXer4) file 133.35-135.95 s.
 *   0.00-0.10 hit, 0.10-0.62 fall back, 0.62 ground impact, 0.62-1.05 lie, 1.05-1.50 sit up,
 *   1.50-2.30 kneel and stand, 2.30-2.60 settle.
 */
namespace PlayerKnockdownMotion
{
inline constexpr float Duration=2.60f;
inline constexpr float Impact=.62f;
/** Eye height above the floor while lying on the back (fallback camera without the full-body eye track). */
inline constexpr float LyingEyeCm=26.f;
inline constexpr float MinFloorClearanceCm=14.f;

/**
 * V2 full body (SourceAssets/PlayerKnockdown20261114/FullBody): player_body.json "clips"/"Knockdown" is the world
 * body clip and "furniture_camera_tracks"/"Knockdown" its authored eye path in body-mesh space. The body lands with
 * the head ~0.9 m behind the capsule and gets up where it lies, so the capsule itself does not move.
 */
inline const TCHAR* const BodyClipRole=TEXT("Knockdown");
inline constexpr float BodyBlendIn=.08f;
inline constexpr float BodyBlendOut=.30f;
/** Camera position: layered eye -> authored head eye during the hit, back to the layered eye while standing. */
inline constexpr float EyeBlendIn=.18f;
inline constexpr float EyeReturnStart=1.95f;
inline constexpr float EyeReturnEnd=2.55f;

inline float BodyWeight(float T)
{
    return FMath::SmoothStep(0.f,BodyBlendIn,T)*(1.f-FMath::SmoothStep(Duration-BodyBlendOut,Duration,T));
}
inline float EyeTrackWeight(float T)
{
    return FMath::SmoothStep(0.f,EyeBlendIn,T)*(1.f-FMath::SmoothStep(EyeReturnStart,EyeReturnEnd,T));
}

/**
 * Generic first-person weapon handling (every weapon without its own knockdown clip; the two-handed sword keeps
 * A_RuneSword_Knockdown): the hit knocks arms and weapon down out of the frame, they stay out while lying and
 * come back up while standing. Camera-component space: X forward, Y right, Z up.
 */
/** Death during a knockdown: before the body has settled it keeps falling to the lying frame; while rising it sinks
 *  back to that frame at real speed; from DeathStandingFrom on (almost upright) the normal standing death plays. */
inline constexpr float DeathLieSeconds=1.00f;
inline constexpr float DeathStandingFrom=1.95f;
/** A knockdown received in the air starts on landing; after this long without ground it is dropped. */
inline constexpr float LandingWait=4.f;

inline constexpr float ViewmodelDropEnd=.24f;
inline constexpr float ViewmodelReturnStart=1.95f;
inline constexpr float ViewmodelReturnEnd=2.50f;
inline FTransform ViewmodelDrop(float T)
{
    const float Out=FMath::Clamp(T/ViewmodelDropEnd,0.f,1.f);
    const float Down=(1.f-FMath::Square(1.f-Out))   // leaves fast with the blow
        *(1.f-FMath::SmoothStep(ViewmodelReturnStart,ViewmodelReturnEnd,T));
    return FTransform(FRotator(-38.f*Down,6.f*Down,18.f*Down),FVector(-12.f,5.f,-50.f)*Down);
}

/** Auto: monotone cubic through the key (no stop, no overshoot). In: arrive at speed (impact). Out: leave at speed. */
enum class ETangent : uint8 { Auto, In, Out };

/** Value at this key = V + BaseWeight * Base. */
struct FKey { float T; float V; float BaseWeight; ETangent Tangent; };

template<int32 N>
float Track(const FKey (&Keys)[N],float T,float Base)
{
    const auto Y=[&](int32 I){return Keys[I].V+Keys[I].BaseWeight*Base;};
    if(T<=Keys[0].T)return Y(0);
    if(T>=Keys[N-1].T)return Y(N-1);
    int32 I=0;
    while(I<N-2&&T>Keys[I+1].T)++I;
    const auto Secant=[&](int32 K){return (Y(K+1)-Y(K))/FMath::Max(1e-4f,Keys[K+1].T-Keys[K].T);};
    // Fritsch-Carlson slope at an interior key; zero at the clip ends and at turning points.
    const auto Slope=[&](int32 K)
    {
        if(K<=0||K>=N-1)return 0.f;
        const float A=Secant(K-1),B=Secant(K);
        if(A*B<=0.f)return 0.f;
        const float H0=Keys[K].T-Keys[K-1].T,H1=Keys[K+1].T-Keys[K].T;
        const float W1=2.f*H1+H0,W2=H1+2.f*H0;
        return (W1+W2)/(W1/A+W2/B);
    };
    const float H=Keys[I+1].T-Keys[I].T;
    const float M0=Keys[I].Tangent==ETangent::Out?2.f*Secant(I):Slope(I);
    const float M1=Keys[I+1].Tangent==ETangent::In?2.f*Secant(I):Slope(I+1);
    const float S=(T-Keys[I].T)/FMath::Max(1e-4f,H),S2=S*S,S3=S2*S;
    return (2.f*S3-3.f*S2+1.f)*Y(I)+(S3-2.f*S2+S)*H*M0+(-2.f*S3+3.f*S2)*Y(I+1)+(S3-S2)*H*M1;
}

struct FCameraSample
{
    float EyeHeightCm=0.f;  // above the floor
    float BackCm=0.f;       // along the view yaw, negative = behind
    float SideCm=0.f;       // along view right
    float Pitch=0.f;        // final view pitch (degrees)
    float YawAdd=0.f;
    float Roll=0.f;
};

/** BaseEyeCm: the layered camera's eye height above the floor this frame; BasePitch: the aim pitch. */
inline FCameraSample Camera(float T,float BaseEyeCm,float BasePitch)
{
    constexpr ETangent A=ETangent::Auto,In=ETangent::In;
    static constexpr FKey Height[]={
        {0.f,0.f,1.f,A},{.10f,-2.f,1.f,A},{Impact,LyingEyeCm,0.f,In},{.70f,LyingEyeCm+4.f,0.f,A},
        {.82f,LyingEyeCm,0.f,A},{1.05f,LyingEyeCm+1.f,0.f,A},{1.50f,76.f,0.f,A},{1.85f,112.f,0.f,A},
        {2.30f,0.f,1.f,A},{Duration,0.f,1.f,A}};
    static constexpr FKey Pitch[]={
        {0.f,0.f,1.f,A},{.07f,-5.f,1.f,A},{.16f,0.f,1.f,A},{.30f,8.f,.5f,A},{.52f,44.f,0.f,A},
        {Impact,60.f,0.f,In},{.68f,64.f,0.f,A},{.85f,55.f,0.f,A},{1.05f,52.f,0.f,A},{1.50f,-14.f,0.f,A},
        {1.85f,-9.f,.3f,A},{2.30f,0.f,1.f,A},{Duration,0.f,1.f,A}};
    // Fallback only, relative to the layered eye (56 cm ahead of the capsule): the head lands ~0.9 m behind it.
    static constexpr FKey Back[]={
        {0.f,0.f,0.f,A},{.10f,-6.f,0.f,A},{Impact,-147.f,0.f,In},{1.05f,-147.f,0.f,A},{1.50f,-80.f,0.f,A},
        {1.85f,-30.f,0.f,A},{2.30f,0.f,0.f,A},{Duration,0.f,0.f,A}};
    static constexpr FKey Side[]={
        {0.f,0.f,0.f,A},{Impact,5.f,0.f,A},{1.05f,5.f,0.f,A},{1.85f,0.f,0.f,A},{Duration,0.f,0.f,A}};
    static constexpr FKey Roll[]={
        {0.f,0.f,0.f,A},{.10f,3.f,0.f,A},{.45f,9.f,0.f,A},{Impact,5.f,0.f,A},{.80f,3.f,0.f,A},
        {1.05f,2.f,0.f,A},{1.45f,-5.f,0.f,A},{1.85f,-2.f,0.f,A},{2.40f,0.f,0.f,A},{Duration,0.f,0.f,A}};
    static constexpr FKey Yaw[]={
        {0.f,0.f,0.f,A},{.45f,-4.f,0.f,A},{1.05f,-3.f,0.f,A},{1.60f,3.f,0.f,A},{2.40f,0.f,0.f,A},
        {Duration,0.f,0.f,A}};
    FCameraSample S;
    S.EyeHeightCm=Track(Height,T,BaseEyeCm);
    S.Pitch=Track(Pitch,T,BasePitch);
    S.BackCm=Track(Back,T,0.f);S.SideCm=Track(Side,T,0.f);
    S.Roll=Track(Roll,T,0.f);S.YawAdd=Track(Yaw,T,0.f);
    // Ground impact: a short damped shake on the same clock as the arms' impact key.
    const float Since=T-Impact;
    if(Since>=0.f&&Since<.32f)
    {
        const float Amp=FMath::Exp(-Since/.08f);
        S.Pitch+=2.2f*Amp*FMath::Sin(UE_TWO_PI*14.f*Since);
        S.EyeHeightCm+=1.2f*Amp*FMath::Sin(UE_TWO_PI*11.f*Since+1.f);
        S.Roll+=1.4f*Amp*FMath::Sin(UE_TWO_PI*9.f*Since+2.f);
    }
    return S;
}
}
