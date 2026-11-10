#pragma once
#include "CoreMinimal.h"

// Shared executor / world-body clock. The first cut accelerates without moving
// its authored contact marker or letting remote presentation run through hitstop.
namespace ChainSlashMotion
{
inline constexpr float FirstCutStart=.18f,FirstCutEnd=.36f,FirstCutAdvance=.12f;
inline float SourceTime(float Playback)
{return Playback+FirstCutAdvance*FMath::SmoothStep(FirstCutStart,FirstCutEnd,Playback);}
inline float PlaybackTime(float Source)
{
    if(Source<=FirstCutStart)return Source;
    if(Source>=FirstCutEnd+FirstCutAdvance)return Source-FirstCutAdvance;
    float Low=FirstCutStart,High=FirstCutEnd;
    for(int32 I=0;I<20;++I)
    {const float Mid=(Low+High)*.5f;if(SourceTime(Mid)<Source)Low=Mid;else High=Mid;}
    return (Low+High)*.5f;
}
inline float SourceRate(float Source)
{
    const float U=FMath::Clamp((PlaybackTime(Source)-FirstCutStart)/(FirstCutEnd-FirstCutStart),0.f,1.f);
    return 1.f+FirstCutAdvance*6.f*U*(1.f-U)/(FirstCutEnd-FirstCutStart);
}
struct FPhase {int32 Cut=0;float Start=0.f,End=0.f,Contact=0.f;};
inline FPhase Phase(float Source,float Length,TConstArrayView<float> Contacts)
{
    FPhase P;P.End=Length;
    for(int32 I=0;I<Contacts.Num();++I)
    {
        P.Cut=I;P.Contact=Contacts[I];
        P.End=I+1<Contacts.Num()?(Contacts[I]+Contacts[I+1])*.5f:Length;
        if(Source<P.End||I+1==Contacts.Num())break;
        P.Start=P.End;
    }
    return P;
}
inline FName Variant(int32 Cut)
{
    static const FName Names[]={TEXT("ChainSlash1"),TEXT("ChainSlash2"),TEXT("ChainSlash3"),TEXT("ChainSlash4")};
    return Names[FMath::Clamp(Cut,0,3)];
}
inline bool IsVariant(FName Name)
{return Name==Variant(0)||Name==Variant(1)||Name==Variant(2)||Name==Variant(3);}
}
