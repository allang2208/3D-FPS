#pragma once
#include "CoreMinimal.h"
#include "RuneSwordOverheadRhythm.h"

class UGunsmithSystem;
struct FColdSteelItem;

namespace HighlandRidgeThrust
{
    inline const FName Charge(TEXT("HighlandRidgeCharge"));
    inline const FName Release(TEXT("HighlandRidgeRelease"));
    inline const FName Counter(TEXT("HighlandRidgeCounter"));
    inline const FName Finisher(TEXT("HighlandRidgeFinisher"));
    inline const FName Dash(TEXT("HighlandRidgeDash"));
    // Frame 3216 is the shared charge/release pose in the 60 Hz reference.
    // 120 Hz keys: source key 16 is the furthest tip. Key 8 is the new
    // extension, keys 8..44 share that exact complete pose on both grips.
    constexpr float ContactStart=2.f/120.f;
    constexpr float ContactEnd=8.f/120.f;
    constexpr float HoldSeconds=36.f/120.f;
    constexpr float AfterglowSeconds=.55f;
    constexpr float FinisherPlaybackRate=.80f;
    constexpr float CounterLead=40.f/120.f;
    constexpr float ReleaseSeconds=(124.f-8.f+36.f)/120.f;
    constexpr float ReachScale=1.25f;
    constexpr float DashDistanceScale=2.f;
    constexpr float StrikeDamageScale=1.5f;
    constexpr float StrikePenetration=.20f,HeavyPenetration=.80f;
    constexpr float HalfWidthCM=RuneSwordOverheadRhythm::FinisherRectangleHalfWidthCM;
    inline bool IsRelease(FName Clip){return Clip==Release||Clip==Counter||Clip==Finisher||Clip==Dash;}
    inline float LeadFor(FName Clip){return Clip==Release?0.f:CounterLead;}
    // Real hold time keeps the muscle tremor moving after the animation reaches
    // its last key. Both grips get the same rigid presentation transform.
    inline void ChargeStrain(double Age,float Load,FVector& Location,FRotator& Rotation)
    {
        const float Strength=.70f*FMath::SmoothStep(.16f,1.f,Load);
        const double A=FMath::Sin(2.*PI*(5.2*.70)*Age),B=FMath::Sin(2.*PI*(7.1*.70)*Age+.48);
        Location=FVector(-.24*B,.35*A+.09*B,.22*B)*Strength;
        Rotation=FRotator(.32*B,.25*A,.48*A-.11*B)*Strength;
    }
    // Playback/attack speed applies to motion only. Cross either hold boundary
    // in a single tick without losing the remaining time on the other side.
    inline float ToWall(float ClipTime,float Lead,float Rate)
    {
        const float Held=FMath::Clamp(ClipTime-Lead-ContactEnd,0.f,HoldSeconds);
        return (ClipTime-Held)/FMath::Max(.01f,Rate)+Held;
    }
    inline float ToClip(float WallTime,float Lead,float Rate)
    {
        Rate=FMath::Max(.01f,Rate);
        const float Held=FMath::Clamp(WallTime-(Lead+ContactEnd)/Rate,0.f,HoldSeconds);
        return (WallTime-Held)*Rate+Held;
    }
    inline bool IsHeavyMeta(uint8 Meta){return Meta==0x10||Meta==0x15;}
    inline bool IsStrikeMeta(uint8 Meta){return Meta==3||Meta==0x16;}
    inline float AddPenetration(float Base,uint8 Meta)
    {return FMath::Clamp(Base+(IsHeavyMeta(Meta)?HeavyPenetration:StrikePenetration),0.f,1.f);}
    bool Installed(const UGunsmithSystem* Smith,const FColdSteelItem* Item);
}
