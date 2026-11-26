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
    constexpr float HitStopSeconds = .045f;

    inline float SourceRate(float Time,float SourceLength)
    {
        const float T=Time*Length/FMath::Max(.05f,SourceLength);
        return T<Grip?ReachRate:T<Cock?CockRate:T<Contact?StrikeRate:T<Follow?FollowRate:RecoveryRate;
    }

    inline float RecoilCM(float ImpactAge)
    {
        const float T=ImpactAge-HitStopSeconds;
        if(T<=0.f||T>=.16f)return 0.f;
        // The authored free follow-through advances about 2 cm. Counter it
        // with 5 cm of whole-pose recoil, then rejoin the existing recovery.
        return -5.f*FMath::SmoothStep(0.f,.045f,T)*(1.f-FMath::SmoothStep(.055f,.16f,T));
    }

    inline void ImpactCamera(float Age,float Strength,FVector& Location,FRotator& Rotation)
    {
        if(Age<0.f||Age>=.18f||Strength<=0.f)return;
        const float Stop=(1.f-FMath::Exp(-Age/.004f))*FMath::Exp(-Age/.038f);
        const float Settle=.24f*FMath::Exp(-FMath::Square((Age-.075f)/.03f));
        const float Fade=1.f-FMath::SmoothStep(.12f,.18f,Age);
        const float Drive=(Stop-Settle)*Fade*Strength;
        Location+=FVector(-8.f,.25f,.45f)*Drive;
        Rotation+=FRotator(-4.5f,.28f,.40f)*Drive;
    }

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
