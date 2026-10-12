#pragma once
#include "CoreMinimal.h"
#include "SpellbookAuthoredOpening.h"
#include "SpellbookFocusPolish.h"

namespace SpellbookFocusMotion
{
// Accepted V24 source poses; arm, book and contact events share one clock.
inline constexpr float Detach=.95f, Gather=1.62f, OpenStart=1.28f, OpenDuration=.66f;
inline constexpr float PlaybackRate=SpellbookFocusPolish::PlaybackRate, AuthoredLength=SpellbookFocusPolish::AuthoredLength;
inline constexpr float Ready=1.95f, OpenLength=AuthoredLength/PlaybackRate, ReturnLength=OpenLength;
// Seven leaves retain the approximate per-page pace of the original three.
inline constexpr float PageCycle=16.f*7.f/3.f;
inline constexpr float OpeningAt=1.40f/PlaybackRate;
inline float Ease(float From,float To,float Value)
{
    const float T=FMath::Clamp((Value-From)/FMath::Max(.001f,To-From),0.f,1.f);
    return T*T*T*(T*(T*6.f-15.f)+10.f);
}
inline float SourceTime(float Age)
{
    // Retain the accepted poses but give the entire action a clear beat:
    // turn, settle the closed grip with a small continuing motion, release,
    // sweep and settle. The source clock never freezes at the grip transition.
    // Scale this shared clock only; reading bob and page cycles keep their rate.
    Age*=PlaybackRate;
    if(Age<=0.f)return 0.f;
    if(Age>=AuthoredLength)return Ready;
    const auto& AgeKeys=SpellbookFocusPolish::AgeKeys;
    const auto& SourceKeys=SpellbookFocusPolish::SourceKeys;
    const auto& Rates=SpellbookFocusPolish::Rates;
    int32 A=0;while(A<7&&Age>=AgeKeys[A+1])++A;
    const float Span=AgeKeys[A+1]-AgeKeys[A],T=(Age-AgeKeys[A])/Span;
    const float T2=T*T,T3=T2*T;
    return (2*T3-3*T2+1)*SourceKeys[A]+(T3-2*T2+T)*Span*Rates[A]
        +(-2*T3+3*T2)*SourceKeys[A+1]+(T3-T2)*Span*Rates[A+1];
}
inline float OpeningAlpha(float SourceTime)
{
    return Ease(OpenStart,OpenStart+OpenDuration,SourceTime);
}
inline FTransform OpenBook(const FTransform& Depart,float Age)
{
    // Local book bones own the hinges; the object keeps its release frame.
    FTransform Result=Depart;
    const float Fade=FMath::SmoothStep(OpenLength,OpenLength+.6f,Age);
    Result.AddToTranslation(FVector(.35f*FMath::Sin(Age*1.1f),0,.55f*FMath::Sin(Age*1.5f))*Fade);
    return Result;
}
inline FTransform ReturnBook(const FTransform& From,const FTransform& Contact,float SourceTime)
{
    // Settle the small reading bob while gripping, before returning as a unit.
    FTransform Result;
    Result.Blend(From,Contact,1.f-Ease(Detach,1.25f,SourceTime));
    return Result;
}
}
