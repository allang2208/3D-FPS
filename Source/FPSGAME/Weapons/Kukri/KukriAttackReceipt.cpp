#include "KukriAttackReceipt.h"
#include "KukriAttackTiming.h"

float KukriAttackReceipt::Seconds(int32 Stage,bool Dual,float AuthorTime,float MainRate,float OffhandRate)
{
    if(Dual&&Stage==2)return AuthorTime/KukriAttackTiming::PairedPlayRate(MainRate,OffhandRate);
    float Result=0.f;
    for(float T=0.f;T<AuthorTime;)
    {
        const float Step=FMath::Min(1.f/240.f,AuthorTime-T),Sample=T+.5f*Step;
        const float Rate=Dual&&Sample>=KukriRhythm::DualSweepOffset(Stage)?OffhandRate:MainRate;
        const float Tempo=Dual?KukriRhythm::DualSweepTempo(Stage,Sample):KukriRhythm::StageTempo(Stage,Sample);
        Result+=Step/FMath::Max(.01f,Rate*Tempo);T+=Step;
    }
    return Result;
}

float KukriAttackReceipt::Length(int32 Stage,bool Dual)
{
    return Dual?(Stage==2?KukriRhythm::DualThrustSeconds:
        KukriRhythm::AttackSeconds+KukriRhythm::DualSweepOffset(Stage)):KukriRhythm::Swings[Stage].Length;
}
