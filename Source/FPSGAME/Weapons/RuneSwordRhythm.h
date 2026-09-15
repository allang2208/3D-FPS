#pragma once
#include "CoreMinimal.h"

// Authored by SourceAssets/RuneSword20260913/CompactRecoveryV8/write_timing_header.py.
// Resamples the accepted V6 trajectory; keep camera and baked poses on this clock.
namespace RuneSwordRhythm
{
    inline constexpr float WindupEnd=0.65f;
    inline constexpr float ContactStart=0.85f;
    inline constexpr float ContactEnd=0.965f;
    inline constexpr float FollowEnd=1.115f;
    inline constexpr float UnloadEnd=1.14f;
    inline constexpr float ReturnCorner=1.44f;
    inline constexpr float AttackEnd=1.775f;
    struct FTimeKey { float Time, Source, Slope; };
    inline constexpr FTimeKey WindupKeys[]={
        {0.0f,0.0f,0.0f},
        {0.08f,0.02f,0.341240876f},
        {0.22f,0.105f,0.692741711f},
        {0.38f,0.235f,0.78f},
        {0.54f,0.355f,0.519971469f},
        {0.65f,0.4f,0.0f},
    };
    inline float Hermite(float U,float StartSlope,float EndSlope)
    {
        U=FMath::Clamp(U,0.f,1.f);
        return (U*U*U-2*U*U+U)*StartSlope+(-2*U*U*U+3*U*U)+(U*U*U-U*U)*EndSlope;
    }
    inline float SourceTime(float T)
    {
        if(T<=0.f)return 0.f;
        if(T<WindupEnd)
        {
            for(int32 I=0;I<UE_ARRAY_COUNT(WindupKeys)-1;++I)
            {
                const auto& A=WindupKeys[I];const auto& B=WindupKeys[I+1];
                if(T<=B.Time)
                {
                    const float Span=B.Time-A.Time,Distance=B.Source-A.Source;
                    return A.Source+Distance*Hermite((T-A.Time)/Span,A.Slope*Span/Distance,B.Slope*Span/Distance);
                }
            }
        }
        if(T<=ContactStart)return .40f+.50f*(T-WindupEnd)/(ContactStart-WindupEnd);
        if(T<=ContactEnd)return .90f+(T-ContactStart);
        if(T<=FollowEnd)return 1.015f+.10f*Hermite((T-ContactEnd)/(FollowEnd-ContactEnd),1.5f,0.f);
        if(T<=UnloadEnd)return 1.115f;
        if(T<=ReturnCorner)return 1.115f+.225f*Hermite((T-UnloadEnd)/(ReturnCorner-UnloadEnd),.55f,1.1f);
        if(T<AttackEnd)return 1.34f+.31f*Hermite((T-ReturnCorner)/(AttackEnd-ReturnCorner),1.35f,0.f);
        return 1.65f;
    }
}
