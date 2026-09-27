#pragma once
#include "CoreMinimal.h"

// Authoring reads these same seconds. Runtime scales them to the loaded clip.
namespace BowQuickCombatMotion
{
    constexpr float Length = .90f;
    constexpr float Grip = .14f;
    constexpr float Cock = .22f;
    constexpr float Contact = .32f;
    constexpr float Follow = .44f;
    constexpr float LetGo = .62f;
    constexpr float GripSeparationCM = 30.f;
    constexpr float StrikeLocalZCM = .8f + GripSeparationCM * .5f;
    constexpr float QueryRadiusCM = 28.f;

    // Keep the fitted hand/weapon poses in source seconds. Runtime remaps the
    // shared pose, hit and skill-bar clock, without changing grip geometry.
    constexpr float ReachRate = 1.4f;
    constexpr float CockRate = 1.5f;
    constexpr float StrikeRate = 2.f;
    constexpr float FollowRate = 1.5f;
    constexpr float RecoveryRate = 1.6f;
    constexpr float HitStopSeconds = .035f;
    constexpr float ImpactTimeScale = 1.25f;
    constexpr float AxialImpactScale = .55f;
    constexpr float PitchImpactScale = .44f;

    inline float PlaybackSeconds(float SourceSeconds,float SourceLength)
    {
        const float Scale=FMath::Max(.05f,SourceLength)/Length;
        const float Ends[]={Grip,Cock,Contact,Follow,Length};
        const float Rates[]={ReachRate,CockRate,StrikeRate,FollowRate,RecoveryRate};
        float Start=0.f,Seconds=0.f;
        for(int32 I=0;I<UE_ARRAY_COUNT(Ends);++I)
        {
            const float End=Ends[I]*Scale;
            Seconds+=FMath::Clamp(SourceSeconds-Start,0.f,End-Start)/Rates[I];
            Start=End;
        }
        return Seconds;
    }

    inline float SourceSeconds(float PlaybackTime,float SourceLength)
    {
        const float Scale=FMath::Max(.05f,SourceLength)/Length;
        const float Ends[]={Grip,Cock,Contact,Follow,Length};
        const float Rates[]={ReachRate,CockRate,StrikeRate,FollowRate,RecoveryRate};
        float Start=0.f,Remaining=FMath::Max(0.f,PlaybackTime);
        for(int32 I=0;I<UE_ARRAY_COUNT(Ends);++I)
        {
            const float End=Ends[I]*Scale;
            const float Span=(End-Start)/Rates[I];
            if(Remaining<Span)return Start+Remaining*Rates[I];
            Remaining-=Span;
            Start=End;
        }
        return SourceLength;
    }

    constexpr const TCHAR* Asset = TEXT("/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat.A_Bow_QuickCombat");
}
