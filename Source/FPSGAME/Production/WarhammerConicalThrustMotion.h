#pragma once
#include "CoreMinimal.h"

// Conical seat: retain the V7 grip/pose, author the rhythm on one action clock.
// A confirmed contact pauses that clock; the impact camera keeps its own age.
namespace WarhammerConicalThrust
{
    inline constexpr float Length=.74f;
    inline constexpr float Prepare=.205f;
    inline constexpr float Contact=.265f;
    inline constexpr float Follow=.320f;
    inline constexpr float Entry=.06f;
    inline constexpr float HitStopSeconds=.038f;
    inline constexpr float QueryRadiusCM=32.f;
    inline constexpr const TCHAR* Asset=TEXT("/Game/Weapons/SteelWarhammer20261014/QuickCombatLeftWristV7/A_Warhammer_QuickCombat.A_Warhammer_QuickCombat");

    inline float SourceSeconds(float Age)
    {
        // Continuous endpoint rates: gather, squeeze, burst, follow-through,
        // unload, then brake into idle. Retiming the whole pose preserves both
        // native grips; .15 source seconds remains the exact damage pose.
        const auto Segment=[Age](float T0,float T1,float S0,float S1,float R0,float R1)
        {
            const float Span=T1-T0;
            return FMath::CubicInterp(S0,R0*Span,S1,R1*Span,
                FMath::Clamp((Age-T0)/Span,0.f,1.f));
        };
        if(Age<=.115f)return Segment(0.f,.115f,0.f,.065f,0.f,.50f);
        if(Age<=Prepare)return Segment(.115f,Prepare,.065f,.09f,.50f,.08f);
        if(Age<=.238f)return Segment(Prepare,.238f,.09f,.103f,.08f,1.15f);
        if(Age<=Contact)return Segment(.238f,Contact,.103f,.15f,1.15f,1.15f);
        if(Age<=Follow)return Segment(Contact,Follow,.15f,.175f,1.15f,.04f);
        if(Age<=.490f)return Segment(Follow,.490f,.175f,.33f,.04f,1.10f);
        if(Age<=.620f)return Segment(.490f,.620f,.33f,.46f,1.10f,.45f);
        return Segment(.620f,Length,.46f,.5f,.45f,0.f);
    }

    inline float Ease(float Begin,float End,float Age)
    {
        const float U=FMath::Clamp((Age-Begin)/(End-Begin),0.f,1.f);
        return U*U*U*(10.f+U*(-15.f+6.f*U));
    }

    inline FVector CameraWeights(float Age)
    {
        const float Load=Ease(.015f,Prepare,Age)*(1.f-Ease(Prepare,Contact,Age));
        const float Drive=Ease(Prepare,Contact,Age)*(1.f-Ease(Follow,.510f,Age));
        const float Return=Ease(Follow,.440f,Age)*(1.f-Ease(.440f,Length,Age));
        return FVector(Load,Drive,Return);
    }

    inline void Camera(float Age,FVector& Location,FRotator& Rotation)
    {
        const FVector W=CameraWeights(Age);
        Location=FVector(-2.6f,.4f,.45f)*W.X+FVector(4.1f,-.2f,-.55f)*W.Y+FVector(-1.1f,.18f,.15f)*W.Z;
        Rotation=FRotator(1.8f,-.25f,-.65f)*W.X+FRotator(-4.4f,.30f,.80f)*W.Y+FRotator(.70f,-.12f,-.22f)*W.Z;
    }

    inline float CameraFOV(float Age)
    {
        const FVector W=CameraWeights(Age);
        return -.9f*W.X+2.5f*W.Y-.35f*W.Z;
    }

    inline void ImpactCamera(float Age,float Strength,FVector& Location,FRotator& Rotation)
    {
        if(Age<0.f||Age>=.22f||Strength<=0.f)return;
        // One resisted shove with a small damped rattle; zero at contact and
        // at the tail avoids a position jump or a lasting camera offset.
        const float Onset=Ease(0.f,.008f,Age);
        const float Fade=1.f-Ease(.13f,.22f,Age);
        const float Kick=Onset*FMath::Exp(-22.f*Age)*FMath::Cos(34.f*Age)*Fade*Strength;
        const float Rattle=Onset*FMath::Exp(-28.f*Age)*FMath::Sin(105.f*Age)*Fade*Strength;
        Location+=FVector(-5.6f,.25f,.35f)*Kick+FVector(0.f,.23f,-.16f)*Rattle;
        Rotation+=FRotator(-5.8f,.45f,.65f)*Kick+FRotator(.42f,-.28f,.32f)*Rattle;
    }
}
