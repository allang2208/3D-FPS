#pragma once
#include "CoreMinimal.h"

// The existing 30 Hz source retains all mechanical event frame numbers.
// Spend an extra 81 frames on extraction, open-hand release, retrieval and
// controlled insertion, including 15 frames (0.5 s) before the new magazine.
// The pose and all contacts share this clock. Run
// the empty-reload bolt cycle at its original speed. Stats scale this clock.
namespace M24ReloadTiming
{
inline float SourceSeconds(float Phase, float SourceLength)
{
    // Source 29-30 is the off-screen handoff from the discarded magazine to
    // its replacement. Keep it moving slowly through the gap, then resume
    // the existing insertion and empty-reload bolt speeds.
    constexpr float Source[] = {0.f,8.f,18.f,21.f,24.f,27.f,29.f,30.f,34.f,38.f,40.f,44.f,50.f,54.f};
    constexpr float Paced[]  = {0.f,8.f,24.f,34.f,43.f,54.f,60.666667f,79.f,92.f,105.f,111.f,119.f,131.f,135.f};
    constexpr int32 Last = UE_ARRAY_COUNT(Source)-1;
    constexpr float Extra = Paced[Last]-Source[Last];
    const float End=SourceLength*30.f;
    const float Time=FMath::Clamp(Phase,0.f,1.f)*(End+Extra);
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
