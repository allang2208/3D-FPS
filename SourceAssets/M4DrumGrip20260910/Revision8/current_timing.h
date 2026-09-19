#pragma once
#include "CoreMinimal.h"

// Fractions refer to the previous drum duration. Only insertion runs at 1.5x;
// the empty-reload wind-up hold (old source frames 111..125) is removed.
// Shared by gameplay, mechanical cues and displayed gunsmith durations.
namespace M4DrumReloadTiming
{
struct FKey { float SourceFrame; float RuntimeFraction; };
inline constexpr FKey Normal[] = {
    {0.000000000f, 0.000000000f},
    {25.200000000f, 0.130000000f},
    {47.880000000f, 0.360000000f},
    {50.000000000f, 0.382433862f},
    {70.560000000f, 0.527477954f},
    {90.720000000f, 0.674144621f},
    {95.000000000f, 0.689713404f},
    {110.880000000f, 0.776360229f},
    {126.000000000f, 0.846360229f}
};
inline constexpr FKey Empty[] = {
    {0.000000000f, 0.000000000f},
    {14.000000000f, 0.056172840f},
    {24.000000000f, 0.096296296f},
    // Spend the recovered time reaching for the new drum, out of view.
    {34.000000000f, 0.328961147f},
    {43.000000000f, 0.399948801f},
    {61.560000000f, 0.497543680f},
    {80.000000000f, 0.598723378f},
    // Seat -> release -> lift -> strike is one continuous 0.45 s motion.
    {88.000000000f, 0.611421791f},
    {104.000000000f, 0.655866237f},
    {111.000000000f, 0.677030259f},
    {116.000000000f, 0.693961477f},
    {128.560000000f, 0.747263946f},
    {148.000000000f, 0.817263946f}
};
inline constexpr float NormalDurationScale = 0.846360229f;
inline constexpr float EmptyDurationScale = 0.817263946f;
inline float DurationScale(bool bEmpty) { return bEmpty ? EmptyDurationScale : NormalDurationScale; }
inline float PreviousRuntimeFraction(float SourceFraction)
{
    constexpr float Source[] = {0,.20f,.38f,.56f,.72f,.88f,1};
    constexpr float Runtime[] = {0,.13f,.36f,.60f,.82f,.93f,1};
    for (int32 I=1; I<7; ++I)
        if (SourceFraction<=Source[I])
            return FMath::Lerp(Runtime[I-1],Runtime[I],(SourceFraction-Source[I-1])/(Source[I]-Source[I-1]));
    return 1.0f;
}
template <SIZE_T N>
inline float Evaluate(const FKey (&Keys)[N],float Fraction,float Scale)
{
    const float T=FMath::Clamp(Fraction,0.0f,1.0f)*Scale;
    for (SIZE_T I=1; I<N; ++I)
        if (T<=Keys[I].RuntimeFraction)
            return FMath::Lerp(Keys[I-1].SourceFrame,Keys[I].SourceFrame,
                (T-Keys[I-1].RuntimeFraction)/(Keys[I].RuntimeFraction-Keys[I-1].RuntimeFraction))/60.0f;
    return Keys[N-1].SourceFrame/60.0f;
}
inline float SourceSeconds(float Fraction,bool bEmpty)
{
    if(!bEmpty)return Evaluate(Normal,Fraction,NormalDurationScale);
    // Monotone Hermite interpolation keeps playback speed continuous at the
    // landmarks, without overshooting a contact or reversing source time.
    constexpr SIZE_T N=sizeof(Empty)/sizeof(Empty[0]);
    const auto Slope=[](SIZE_T I){return (Empty[I+1].SourceFrame-Empty[I].SourceFrame)/(Empty[I+1].RuntimeFraction-Empty[I].RuntimeFraction);};
    const auto Tangent=[&](SIZE_T I){
        if(I==0)return Slope(0);
        if(I==N-1)return Slope(N-2);
        const float A=Empty[I].RuntimeFraction-Empty[I-1].RuntimeFraction;
        const float B=Empty[I+1].RuntimeFraction-Empty[I].RuntimeFraction;
        return 3.f*(A+B)/((2.f*B+A)/Slope(I-1)+(B+2.f*A)/Slope(I));
    };
    const float T=FMath::Clamp(Fraction,0.f,1.f)*EmptyDurationScale;
    for(SIZE_T I=1;I<N;++I)if(T<=Empty[I].RuntimeFraction){
        const float H=Empty[I].RuntimeFraction-Empty[I-1].RuntimeFraction;
        const float U=(T-Empty[I-1].RuntimeFraction)/H,U2=U*U,U3=U2*U;
        return ((2*U3-3*U2+1)*Empty[I-1].SourceFrame+(U3-2*U2+U)*H*Tangent(I-1)
            +(-2*U3+3*U2)*Empty[I].SourceFrame+(U3-U2)*H*Tangent(I))/60.f;
    }
    return Empty[N-1].SourceFrame/60.f;
}
}
