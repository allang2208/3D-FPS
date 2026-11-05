#pragma once
#include "M24WeaponAssets.h"
#include "CoreMinimal.h"

// The existing 30 Hz source retains all mechanical event frame numbers.
// Add 63 frames for the paced reach, retrieval and controlled insertion.
// Extraction/release/withdrawal (source 18-29) takes 18 2/3 frames instead of
// 36 2/3: pull decisively and flow straight into release, without a slow hold.
// Retain the requested extra 15 frames (0.5 s) before the new magazine.
// Pose, magazine, audio and contacts share this clock; stats scale it together.
// The insertion and empty-reload bolt cycle retain their existing durations.
namespace M24ReloadTiming
{
inline float PacedBoltTime(float Source,float Begin,float End,float DurationScale)
{
    return Source+FMath::Clamp(Source-Begin,0.f,End-Begin)*(DurationScale-1.f);
}
inline float UnpaceBoltTime(float Time,float Begin,float End,float DurationScale)
{
    return PacedBoltTime(Time,Begin,Begin+(End-Begin)*DurationScale,1.f/DurationScale);
}
constexpr float ExtraMagazineFrames=63.f;
constexpr float EmptySourceFrames=110.f;
inline float EmptyPacedFrames(float End,float DurationScale)
{
    return PacedBoltTime(End+ExtraMagazineFrames,M24WeaponAssets::ChargeLift*30.f+ExtraMagazineFrames,
        M24WeaponAssets::ChargeRelease*30.f+ExtraMagazineFrames,DurationScale);
}
inline float EquipPacedTime(float Source,float DurationScale)
{
    return PacedBoltTime(Source,M24WeaponAssets::BoltLift+3.f/30.f,M24WeaponAssets::EquipBoltClosed,DurationScale);
}
inline float SourceSeconds(float Phase,float SourceLength,float BoltDurationScale=1.f)
{
    // Source 29-30 is the off-screen handoff from the discarded magazine to
    // its replacement. Keep it moving slowly through the gap, then resume
    // the existing insertion and empty-reload bolt speeds.
    constexpr float Source[] = {0.f,8.f,18.f,21.f,24.f,27.f,29.f,30.f,34.f,38.f,40.f,44.f,50.f,54.f};
    constexpr float Paced[]  = {0.f,8.f,24.f,28.5f,32.5f,37.f,42.666667f,61.f,74.f,87.f,93.f,101.f,113.f,117.f};
    constexpr int32 Last = UE_ARRAY_COUNT(Source)-1;
    constexpr float Extra = Paced[Last]-Source[Last];
    const float End=SourceLength*30.f;
    static_assert(Extra==ExtraMagazineFrames);
    const float PacedTime=FMath::Clamp(Phase,0.f,1.f)*EmptyPacedFrames(End,BoltDurationScale);
    const float Time=UnpaceBoltTime(PacedTime,M24WeaponAssets::ChargeLift*30.f+Extra,
        M24WeaponAssets::ChargeRelease*30.f+Extra,BoltDurationScale);
    if(Time>=Paced[Last])return FMath::Min(End,Time-Extra)/30.f;
    int32 I=0;
    while(I<Last-1 && Time>Paced[I+1])++I;
    const auto Slope=[&](int32 K)
    {
        if(K==0 || K==Last)return 1.f;
        const float Before=(Source[K]-Source[K-1])/(Paced[K]-Paced[K-1]);
        const float After=(Source[K+1]-Source[K])/(Paced[K+1]-Paced[K]);
        return 2.f*Before*After/(Before+After);
    };
    const float Span=Paced[I+1]-Paced[I];
    const float T=(Time-Paced[I])/Span;
    return FMath::CubicInterp(Source[I],Span*Slope(I),Source[I+1],Span*Slope(I+1),T)/30.f;
}
}
