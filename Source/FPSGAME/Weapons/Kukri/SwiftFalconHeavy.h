#pragma once
#include "CoreMinimal.h"

struct FColdSteelItem;
struct FWeaponDamageParts;
class UColdSteelStatusModel;
namespace SwiftFalconHeavy
{
    void ScalePhysicalDamage(FWeaponDamageParts& Panel);
    inline const FName Charge(TEXT("FalconCharge")),DualCharge(TEXT("FalconDualCharge"));
    inline const FName Release(TEXT("FalconRelease")),DualRelease(TEXT("FalconDualRelease"));
    inline constexpr float ChopTrail=.16f;
    inline constexpr float ChopIn=.19f,ChopOut=.31f,ChopAt=.24f;
    // These are the 60 Hz release keys in author_pull_r4.py.
    inline constexpr float LowPoseAt=20.f/60.f,Hook=40.f/60.f,PullTrail=41.f/60.f;
    inline constexpr float PullIn=42.f/60.f,PullAt=45.f/60.f,PullPeak=49.f/60.f,PullOut=PullPeak;
    inline constexpr float BrakeEnd=55.f/60.f,Settled=68.f/60.f,Length=96.f/60.f;
    inline float PlaybackRate(float T,float AttackRate)
    {
        return T>=LowPoseAt-UE_KINDA_SMALL_NUMBER && T<PullTrail-UE_KINDA_SMALL_NUMBER ? 1.f : AttackRate;
    }
    inline float PlaybackSeconds(float T,float AttackRate)
    {
        const float LowHold=FMath::Clamp(T-LowPoseAt,0.f,PullTrail-LowPoseAt);
        return LowHold+(T-LowHold)/AttackRate;
    }
    inline float FleshStop(bool Pull,bool Dual){return (Pull?.115f:.120f)+(Dual?.015f:0.f);}
    inline float ContactStrength(bool Pull,bool Dual){return (Pull?1.55f:1.4f)*(Dual?1.08f:1.f);}
    inline float ContactPulse(float Age)
    {
        if(Age<0.f)return 0.f;
        const float Hit=FMath::SmoothStep(0.f,.012f,Age)*(1.f-FMath::SmoothStep(.012f,.15f,Age));
        const float Settle=FMath::SmoothStep(.10f,.15f,Age)*(1.f-FMath::SmoothStep(.15f,.23f,Age));
        return Hit-.12f*Settle;
    }
    inline void ReleaseCamera(float T,FVector& Location,FRotator& Rotation,float& Fov)
    {
        const float Chop=FMath::SmoothStep(.03f,ChopAt,T)*(1.f-FMath::SmoothStep(PullTrail,PullPeak,T));
        const float Drive=FMath::SmoothStep(PullTrail,PullPeak,T);
        const float Pull=Drive*(1.f-FMath::SmoothStep(BrakeEnd,Length,T));
        const float ExtraTravel=Drive*(1.f-FMath::SmoothStep(BrakeEnd,Settled,T));
        const float Lift=1.f-FMath::SmoothStep(0.f,.19f,T);
        Rotation.Pitch+=2.f*Lift-4.f*Chop+2.6f*Pull+1.4f*ExtraTravel;
        Location.X+=1.5f*Chop-3.1f*Pull-1.6f*ExtraTravel;Location.Z+=.45f*Pull;
        Fov+=Chop-.65f*Lift-.8f*Pull-.3f*ExtraTravel;
    }
    bool Eligible(const FColdSteelItem* Main,const UColdSteelStatusModel* Profile,bool Both);
    float ReleaseRate(const FColdSteelItem& Main,const FColdSteelItem* Off,const UColdSteelStatusModel* Profile);
    inline void ChargeCamera(float T,FRotator& Rotation,float& Fov)
    {
        const float Lift=FMath::SmoothStep(0.f,.62f,T);
        Rotation=FRotator(2.f*Lift,0.f,0.f);Fov=-.65f*Lift;
    }
}
