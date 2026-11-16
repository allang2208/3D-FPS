#pragma once
#include "Animation/AnimSequence.h"

namespace FPSBodyAnimation
{
// One phase means one left/right step pair, not one whole animation asset.
// Both player bodies and humanoid enemies use the same contact convention.
struct FStrideTiming
{
    float Length=1.f;
    float RootSpeed=0.f;
    TArray<float> Left,Right;
    explicit FStrideTiming(const UAnimSequence* Clip,const UAnimSequence* PhaseReference=nullptr)
    {
        if(!Clip)return;
        Length=FMath::Max(Clip->GetPlayLength(),SMALL_NUMBER);
        const FVector Start=Clip->ExtractRootTrackTransform(FAnimExtractContext(0.,false),nullptr).GetTranslation();
        const FVector End=Clip->ExtractRootTrackTransform(FAnimExtractContext(double(Length),false),nullptr).GetTranslation();
        RootSpeed=float((End-Start).Size2D())/Length;
        // Derived diagonals may omit markers while retaining their donor's feet.
        const UAnimSequence* Source=Clip->AuthoredSyncMarkers.IsEmpty()&&PhaseReference?PhaseReference:Clip;
        const float Scale=Length/FMath::Max(Source->GetPlayLength(),SMALL_NUMBER);
        for(const auto& Marker:Source->AuthoredSyncMarkers)
        {
            if(Marker.MarkerName==TEXT("L"))Left.Add(Marker.Time*Scale);
            else if(Marker.MarkerName==TEXT("R"))Right.Add(Marker.Time*Scale);
        }
        Left.Sort();Right.Sort();
    }
    float Duration() const {return Length/FMath::Max(Left.Num(),1);}
    float Speed(float Fallback) const {return RootSpeed>1.f?RootSpeed:Fallback;}
    float Distance(float Fallback) const {return Speed(Fallback)*Duration();}
    float Sample(float Cycles) const
    {
        if(Left.IsEmpty()||Right.IsEmpty())return FMath::Fmod(Cycles,1.f)*Length;
        const int32 Cycle=FMath::FloorToInt(Cycles)%Left.Num();
        const float Start=Left[Cycle];
        const float End=Cycle+1<Left.Num()?Left[Cycle+1]:Left[0]+Length;
        float Middle=(Start+End)*.5f;
        for(const float Contact:Right)
        {
            const float Time=Contact>Start?Contact:Contact+Length;
            if(Time>Start&&Time<End){Middle=Time;break;}
        }
        const float Phase=FMath::Frac(Cycles);
        const float Time=Phase<.5f?FMath::Lerp(Start,Middle,Phase*2.f):FMath::Lerp(Middle,End,(Phase-.5f)*2.f);
        return FMath::Fmod(Time,Length);
    }
};
}
