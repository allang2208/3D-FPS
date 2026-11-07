#pragma once
#include "FPSPlayerBodyTypes.h"
#include "Animation/AnimSequence.h"
#include "../Weapons/HighlandRidgeThrust.h"

namespace FPSBodyHighlandMotion
{
inline const FName SweepReady(TEXT("HighlandBreakSweepReady"));
inline bool IsSweep(FName Variant)
{return Variant==TEXT("HighlandBreakSweep")||Variant==SweepReady;}
inline bool IsRidge(const FFPSBodyState& S)
{return S.ActionVariant==HighlandRidgeThrust::Charge||HighlandRidgeThrust::IsRelease(S.ActionVariant);}
inline bool IsDash(const FFPSBodyState& S)
{return S.Family==TEXT("Melee")&&S.Action==EFPSBodyAction::Thrust&&S.ActionVariant==HighlandRidgeThrust::Dash;}

// The ordinary sprint attack supplies only pelvis/legs. Its contact markers
// follow the thrust executor, including the thrust's fixed end-position hold.
inline float DashStrideSample(const FFPSBodyState& S,float P,float ContactPose,float ReleasePose)
{
    const float Hit=FMath::Clamp(S.ContactFraction,.01f,.98f);
    const float Release=FMath::Clamp(S.ReleaseFraction,Hit+.001f,.99f);
    const float Entry=FMath::Clamp(S.ActionEntryFraction,0.f,Hit-.001f);
    const float Recover=FMath::Min(.999f,Release+HighlandRidgeThrust::HoldSeconds/FMath::Max(.001f,S.ActionDuration));
    if(P<=Hit)return FMath::Lerp(0.f,ContactPose,FMath::Clamp((P-Entry)/(Hit-Entry),0.f,1.f));
    if(P<=Release)return FMath::Lerp(ContactPose,ReleasePose,(P-Hit)/(Release-Hit));
    if(P<=Recover)return ReleasePose;
    return FMath::Lerp(ReleasePose,1.f,FMath::Clamp((P-Recover)/(1.f-Recover),0.f,1.f));
}
inline float DashLegWeight(const FFPSBodyState& S,float P)
{
    const float Windup=FMath::Max(.001f,S.ContactFraction-S.ActionEntryFraction);
    const float Plant=FMath::SmoothStep(S.ActionEntryFraction,S.ActionEntryFraction+Windup*.45f,P);
    const float Recover=S.ReleaseFraction+HighlandRidgeThrust::HoldSeconds/FMath::Max(.001f,S.ActionDuration);
    const float Return=FMath::SmoothStep(Recover,Recover+.25f/FMath::Max(.001f,S.ActionDuration),P);
    return Plant*(1.f-Return);
}

// Equipment is already replicated. Select its fitted full-body source on each
// peer when equipment is rebuilt; do not infer grip length from wrist distance.
inline void SelectGrip(TMap<FName,TObjectPtr<UAnimSequence>>& Clips,bool LongGrip)
{
    for(const TCHAR* Role:{TEXT("Melee.FullBody.HighlandBreakSweep"),TEXT("Melee.FullBody.HighlandBreakSweepReady"),TEXT("Melee.FullBody.HighlandRidgeThrust")})
    {
        const FName Source(*(FString(Role)+(LongGrip?TEXT(".LongGrip"):TEXT(".Standard"))));
        if(auto* Sequence=Clips.FindRef(Source).Get())Clips.Add(FName(Role),Sequence);
    }
}

// The one authored take contains ready->loaded, extension, the fixed 0.3 s hold,
// and recovery. Charge and heavy release meet at exactly the same source key.
inline float RidgeSampleSeconds(const FFPSBodyState& S,float Progress,float SourceLength)
{
    const float Lead=HighlandRidgeThrust::CounterLead;
    if(S.ActionVariant==HighlandRidgeThrust::Charge)return Progress*Lead;
    const bool FromCharge=S.ActionVariant==HighlandRidgeThrust::Release;
    const float Offset=FromCharge?Lead:0.f;
    const float ClipDuration=FMath::Max(.001f,SourceLength-Offset);
    const float WallDuration=FMath::Max(.001f,S.ActionDuration);
    const float Rate=(ClipDuration-HighlandRidgeThrust::HoldSeconds)/FMath::Max(.001f,WallDuration-HighlandRidgeThrust::HoldSeconds);
    return Offset+HighlandRidgeThrust::ToClip(Progress*WallDuration,FromCharge?0.f:Lead,Rate);
}
}
