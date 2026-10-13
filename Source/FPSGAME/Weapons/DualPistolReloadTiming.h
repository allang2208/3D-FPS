#pragma once
#include "CoreMinimal.h"
#include "DanWesson715WeaponAssets.h"

namespace DualPistolReloadTiming
{
    // Runtime source seconds -> authored source seconds. Retiming the whole rig
    // preserves the palm/grip, fingers and mechanism's authored relationships.
    // Positive Hermite slopes keep forward-only cue/transaction crossings.
    struct FKey { float Time, Source, Slope; };
    inline constexpr FKey Pistol[] = {
        {0.f,0.f,1.f}, {.19f,.11f,.45f}, {.29f,.33f,2.f},
        {.36f,.41f,.45f}, {.52f,.46f,.5f}, {.72f,.72f,1.f}
    };
    inline constexpr FKey Revolver[] = {
        {0.f,0.f,1.f}, {.22f,.14f,.5f}, {.32f,.34f,2.f},
        {.40f,.48f,.5f}, {.54f,.55f,.5f}, {.76f,.76f,1.f}
    };
    inline TConstArrayView<FKey> Keys(bool bRevolver)
    { return bRevolver ? MakeArrayView(Revolver) : MakeArrayView(Pistol); }
    inline float ClockScale(bool bRevolver, bool bSpeedloader)
    {
        return bRevolver && bSpeedloader
            ? DanWesson715WeaponAssets::EmptyReload / DanWesson715WeaponAssets::NormalReload : 1.f;
    }
    inline float Sample(float Time, TConstArrayView<FKey> Curve)
    {
        if(Time<=0.f)return 0.f;
        for(int32 I=1;I<Curve.Num();++I)
        {
            const auto& A=Curve[I-1];const auto& B=Curve[I];
            if(Time>B.Time)continue;
            const float Span=B.Time-A.Time;
            return FMath::CubicInterp(A.Source,A.Slope*Span,B.Source,B.Slope*Span,(Time-A.Time)/Span);
        }
        // End position and slope are identity: loading, closing, total duration
        // and the existing +33% dual-wield cost stay on their original clock.
        return Time;
    }
    inline float SourceTime(float LinearSource, bool bRevolver, bool bSpeedloader)
    {
        const float Scale=ClockScale(bRevolver,bSpeedloader);
        return Sample(LinearSource/Scale,Keys(bRevolver))*Scale;
    }
    inline float LinearSourceTime(float Source, bool bRevolver, bool bSpeedloader)
    {
        const float Scale=ClockScale(bRevolver,bSpeedloader);
        const auto Curve=Keys(bRevolver);
        const float Target=Source/Scale;
        if(Target<=0.f)return 0.f;
        if(Target>=Curve.Last().Source)return Source;
        float Low=0.f,High=Curve.Last().Time;
        for(int32 I=0;I<16;++I)
        {
            const float Mid=(Low+High)*.5f;
            if(Sample(Mid,Curve)<Target)Low=Mid;else High=Mid;
        }
        return (Low+High)*.5f*Scale;
    }
}
