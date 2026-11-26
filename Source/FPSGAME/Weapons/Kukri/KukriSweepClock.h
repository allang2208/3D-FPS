#pragma once
#include "KukriAttackTiming.h"

namespace KukriAttackTiming
{
// Absolute clock for an ordinary first sweep (including the bow AI's pair).
// Integrate the player's StageTempo/DualSweepTempo once, not once per actor or
// animation tick. Explicit contact knots keep authority and observers on the
// same impact, including the fixed real-time stop at each blade's strike.
class FSweepClock
{
    TArray<FVector2f> Samples; // author seconds, elapsed seconds at rate 1
    bool bDual;
    float Lookup(float Value,bool Inverse) const
    {
        const int32 Axis=Inverse?1:0;
        int32 Lo=0,Hi=Samples.Num()-1;
        while(Hi-Lo>1)
        {
            const int32 Mid=(Lo+Hi)/2;
            if(Samples[Mid][Axis]<Value)Lo=Mid;else Hi=Mid;
        }
        const float Alpha=FMath::Clamp((Value-Samples[Lo][Axis])/
            FMath::Max(SMALL_NUMBER,Samples[Hi][Axis]-Samples[Lo][Axis]),0.f,1.f);
        return FMath::Lerp(Samples[Lo][1-Axis],Samples[Hi][1-Axis],Alpha);
    }
    explicit FSweepClock(bool Dual):bDual(Dual)
    {
        Samples.Emplace(0.f,0.f);
        const float End=AuthorLength(),Offset=KukriRhythm::DualSweepOffset(0);
        for(float T=0.f;T<End;)
        {
            float Next=FMath::Min(End,T+1.f/240.f);
            for(float Boundary:{ContactAuthor(0),bDual?Offset:End,bDual?ContactAuthor(1):End})
                if(T<Boundary&&Next>Boundary)Next=Boundary;
            const float Mid=(T+Next)*.5f;
            const float Tempo=bDual?KukriRhythm::DualSweepTempo(0,Mid):KukriRhythm::StageTempo(0,Mid);
            Samples.Emplace(Next,Samples.Last().Y+(Next-T)/Tempo);
            T=Next;
        }
    }
public:
    static const FSweepClock& Get(bool Dual)
    {
        static const FSweepClock Single(false),Pair(true);
        return Dual?Pair:Single;
    }
    float AuthorLength() const {return KukriRhythm::AttackSeconds+(bDual?KukriRhythm::DualSweepOffset(0):0.f);}
    float ContactAuthor(int32 Hand) const {return KukriRhythm::Strikes[0].At+Hand*KukriRhythm::DualSweepOffset(0);}
    float Stop() const {return KukriRhythm::Strikes[0].MissStop;}
    int32 Contacts() const {return bDual?2:1;}
    float ContactSeconds(int32 Hand,float Rate) const {return Lookup(ContactAuthor(Hand),false)/Rate+Hand*Stop();}
    float Duration(float Rate) const {return Samples.Last().Y/Rate+Contacts()*Stop();}
    float RateForDuration(float Seconds) const {return Samples.Last().Y/FMath::Max(.001f,Seconds-Contacts()*Stop());}
    float AuthorSeconds(float Seconds,float Rate) const
    {
        float Moving=Seconds;
        for(int32 Hand=0;Hand<Contacts();++Hand)
        {
            const float Hit=ContactSeconds(Hand,Rate);
            if(Seconds<Hit)break;
            if(Seconds<Hit+Stop())return ContactAuthor(Hand);
            Moving-=Stop();
        }
        return Lookup(FMath::Max(0.f,Moving)*Rate,true);
    }
};
}
