#pragma once
#include "CoreMinimal.h"

// The skill clock is real time; V7 keeps the V6 pose/camera source-time map.
namespace WarhammerQuickCombat
{
    inline constexpr float Length=.72f;
    inline constexpr float Prepare=.22f;
    inline constexpr float Contact=.28f;
    inline constexpr float Follow=.34f;
    inline constexpr float Entry=.06f;
    inline constexpr float QueryRadiusCM=32.f;
    inline constexpr const TCHAR* Asset=TEXT("/Game/Weapons/SteelWarhammer20261014/QuickCombatLeftWristV7/A_Warhammer_QuickCombat.A_Warhammer_QuickCombat");

    inline float SourceSeconds(float Age)
    {
        // Monotone Hermite segments with matching endpoint rates: longer
        // loading, a short accelerating thrust, then continuous unloading.
        // Retiming the whole pose preserves the native hand/shaft relationship.
        const auto Segment=[Age](float T0,float T1,float S0,float S1,float R0,float R1)
        {
            const float Span=T1-T0;
            return FMath::CubicInterp(S0,R0*Span,S1,R1*Span,
                FMath::Clamp((Age-T0)/Span,0.f,1.f));
        };
        if(Age<=Prepare)return Segment(0.f,Prepare,0.f,.09f,.48f,.2f);
        if(Age<=Contact)return Segment(Prepare,Contact,.09f,.15f,.2f,1.2f);
        if(Age<=Follow)return Segment(Contact,Follow,.15f,.175f,1.2f,.2f);
        if(Age<=.54f)return Segment(Follow,.54f,.175f,.33f,.2f,1.f);
        return Segment(.54f,Length,.33f,.5f,1.f,.75f);
    }

    inline void Camera(float Age,FVector& Location,FRotator& Rotation)
    {
        const float Source=SourceSeconds(Age);
        const float Back=FMath::SmoothStep(0.f,.09f,Source)*(1.f-FMath::SmoothStep(.09f,.15f,Source));
        const float Push=FMath::SmoothStep(.09f,.15f,Source)*(1.f-FMath::SmoothStep(.175f,.5f,Source));
        Location=FVector(-.55f*Back+1.80f*Push,0.f,-.25f*Push);
        Rotation=FRotator(.30f*Back-.70f*Push,0.f,0.f);
    }
}
