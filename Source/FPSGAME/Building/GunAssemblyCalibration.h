#pragma once
#include "CoreMinimal.h"

/** Shared timing and geometry for gun calibration, scoring and its HUD. */
namespace GunAssemblyCalibration
{
inline constexpr int32 Version=2,FirstRoundsVersion=1,RoundCount=5;
inline constexpr float FollowSeconds=5.f,ReadySeconds=1.f,RestSeconds=2.f;
inline constexpr float ScoringSeconds=RoundCount*FollowSeconds;
inline constexpr float Duration=ReadySeconds+ScoringSeconds+(RoundCount-1)*RestSeconds;
inline constexpr float BaseRadius=.0235f;

inline float Interval(int32 Rules=Version){return Rules==FirstRoundsVersion?1.f:RestSeconds;}
inline float TotalDuration(int32 Rules=Version){return ReadySeconds+ScoringSeconds+(RoundCount-1)*Interval(Rules);}
inline float Preparation(int32 Index,int32 Rules=Version){return Index==0?ReadySeconds:Interval(Rules);}
inline float RoundStart(int32 Index,int32 Rules=Version){return Index==0?0.f:ReadySeconds+Index*FollowSeconds+(Index-1)*Interval(Rules);}
inline int32 Round(float Time,int32 Rules=Version)
{return FMath::Clamp(FMath::FloorToInt((Time+Interval(Rules)-ReadySeconds)/(FollowSeconds+Interval(Rules))),0,RoundCount-1);}
inline float RoundTime(float Time,int32 Rules=Version)
{const int32 Index=Round(Time,Rules);return FMath::Clamp(Time-RoundStart(Index,Rules),0.f,Preparation(Index,Rules)+FollowSeconds);}
inline bool Following(float Time,int32 Rules=Version)
{return Time<TotalDuration(Rules)&&RoundTime(Time,Rules)>=Preparation(Round(Time,Rules),Rules);}
inline bool Complete(float Time,int32 Rules=Version){return Time>=TotalDuration(Rules);}
inline float PhaseRemaining(float Time,int32 Rules=Version)
{return FMath::Max(0.f,Preparation(Round(Time,Rules),Rules)+(Following(Time,Rules)?FollowSeconds:0.f)-RoundTime(Time,Rules));}
inline float ActiveElapsed(float Time,int32 Rules=Version)
{
    float Result=0;
    for(int32 I=0;I<RoundCount;++I)Result+=FMath::Clamp(Time-RoundStart(I,Rules)-Preparation(I,Rules),0.f,FollowSeconds);
    return Result;
}
inline float UpgradeElapsed(float Time,int32 PreviousRules)
{
    if(Complete(Time,PreviousRules))return Duration;
    const int32 Index=Round(Time,PreviousRules);
    const float Phase=RoundTime(Time,PreviousRules),Before=Preparation(Index,PreviousRules),After=Preparation(Index);
    return RoundStart(Index)+(Phase<Before?Phase/Before*After:After+Phase-Before);
}
inline float ElapsedForActive(float Active)
{
    if(Active<=0.f)return 0.f;
    const int32 Index=FMath::Clamp(FMath::FloorToInt(Active/FollowSeconds),0,RoundCount-1);
    return RoundStart(Index)+Preparation(Index)+FMath::Clamp(Active-Index*FollowSeconds,0.f,FollowSeconds);
}
inline float Radius(float Time,uint32 Seed)
{
    const float Position=FMath::Max(0.f,Time)/.9f;
    const int32 Index=FMath::FloorToInt(Position);
    const auto Sample=[Seed](int32 I)->float
    {
        if(I==0)return 1.f;
        FRandomStream Random(int32(Seed+uint32(I)*196314165u));
        return float(Random.FRandRange(.55f,1.45f));
    };
    return BaseRadius*FMath::Lerp(Sample(Index),Sample(Index+1),FMath::SmoothStep(0.f,1.f,Position-Index));
}
}
