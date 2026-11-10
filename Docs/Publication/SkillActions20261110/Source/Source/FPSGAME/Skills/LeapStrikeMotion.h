#pragma once
#include "CoreMinimal.h"
#include "../Production/WarhammerHeavyMotion.h"

// Real seconds, deliberately independent of weapon speed and haste.
namespace LeapStrike
{
inline constexpr float Charge=.5f, Flight=.75f, Land=Charge+Flight;
inline constexpr float Downstroke=.14f, Planted=.14f, Recover=.44f;
inline constexpr float End=Land+Planted+Recover;
// Standard flight is .75 s. Deep drops extend it under native gravity; Land
// remains an animation coordinate, never a timer that applies airborne damage.
inline constexpr float ArcHeight=150.f, MaxRise=300.f, MaxDrop=20000.f;
inline constexpr float StandardDrop=120.f,MinimumApexClearance=24.f;
inline constexpr float MaxAirTime=12.f, StallTimeout=1.f, FloorClearance=2.4f, TargetTolerance=2.f;
inline constexpr float AimYawLimit=30.f, AimPitchLimit=20.f, PreviewPathInterval=.05f;
inline constexpr const TCHAR* MotionName=TEXT("WarhammerLeapStrike");
inline constexpr const TCHAR* Asset=TEXT("/Game/Weapons/SteelWarhammer20261014/LeapStrikeV2/A_Warhammer_LeapStrikeV2.A_Warhammer_LeapStrikeV2");
inline constexpr float ViewPitch=-38.f;
// Authored contact marker in the continuous animation's camera frame (cm).
inline const FVector ContactHead(131.839383,.788552,-19.432636);
inline float Ease(float U){U=FMath::Clamp(U,0.f,1.f);return U*U*U*(10.f+U*(-15.f+6.f*U));}
inline float StandingHeight(float Half,float Radius,const FVector& Normal)
{return Half+FloorClearance+Radius*(1.f/FMath::Max(.5f,float(Normal.Z))-1.f);}
inline float FallTime(float Distance,float DownSpeed,float Gravity,float TerminalSpeed)
{
    DownSpeed=FMath::Clamp(DownSpeed,0.f,TerminalSpeed);
    const float ToTerminal=(TerminalSpeed-DownSpeed)/Gravity;
    const float TerminalDistance=(DownSpeed+TerminalSpeed)*.5f*ToTerminal;
    return Distance<=TerminalDistance?(FMath::Sqrt(DownSpeed*DownSpeed+2.f*Gravity*Distance)-DownSpeed)/Gravity:
        ToTerminal+(Distance-TerminalDistance)/TerminalSpeed;
}
struct FTrajectory
{
    FVector Velocity=FVector::ZeroVector;
    float Duration=0.f,Gravity=0.f,TerminalSpeed=0.f;
    FVector Position(const FVector& Start,float Time) const
    {
        const float T=FMath::Max(0.f,Time),TerminalTime=(float(Velocity.Z)+TerminalSpeed)/Gravity;
        const float Accelerating=FMath::Min(T,TerminalTime);
        FVector P=Start+Velocity*T;
        P.Z=Start.Z+Velocity.Z*Accelerating-.5f*Gravity*Accelerating*Accelerating-TerminalSpeed*FMath::Max(0.f,T-TerminalTime);
        return P;
    }
};
inline bool SolveTrajectory(const FVector& Start,const FVector& Target,float GravityZ,float TerminalSpeed,FTrajectory& Out)
{
    // Requests describe the supported standing centre; aim the falling capsule
    // at first physical contact, before CharacterMovement restores floor clearance.
    const float G=-GravityZ,DZ=float(Target.Z-Start.Z)-FloorClearance;
    if(Start.ContainsNaN()||Target.ContainsNaN()||!FMath::IsFinite(G)||G<=1.f||!FMath::IsFinite(TerminalSpeed)||TerminalSpeed<=1.f)return false;
    // Solve a .75 s arrival for ordinary terrain. Beyond a 1.2 m drop, retain
    // that launch impulse and keep falling, solving horizontal speed for the
    // actual contact time. Both duration and velocity are continuous at the edge.
    const float NominalDZ=FMath::Max(DZ,-StandardDrop-FloorClearance);
    const float TimedRise=NominalDZ/Flight+.5f*G*Flight;
    // A high ledge / unusually weak gravity must still be reached from above.
    const float SafeRise=FMath::Sqrt(2.f*G*(FMath::Max(0.f,DZ)+MinimumApexClearance));
    // Long falls reduce horizontal speed. Restore the high-roof takeoff arc
    // smoothly so the capsule can clear the departure ledge before descending.
    const float DeepDrop=FMath::Max(0.f,-DZ-StandardDrop-FloorClearance);
    const float DeepRise=FMath::Lerp(TimedRise,FMath::Max(TimedRise,FMath::Sqrt(2.f*G*ArcHeight)),FMath::SmoothStep(0.f,ArcHeight,DeepDrop));
    const float RiseSpeed=FMath::Max(DeepRise,SafeRise),Apex=RiseSpeed*RiseSpeed/(2.f*G);
    const float Descent=FallTime(Apex-DZ,0.f,G,TerminalSpeed);
    Out.Duration=RiseSpeed/G+Descent;Out.Gravity=G;Out.TerminalSpeed=TerminalSpeed;
    if(!FMath::IsFinite(Out.Duration)||Out.Duration>=MaxAirTime-1.f)return false;
    Out.Velocity=(Target-Start)/Out.Duration;Out.Velocity.Z=RiseSpeed;return true;
}
inline FName Clip(float T)
{return T<Charge?TEXT("Uppercut"):T<Land-Downstroke?TEXT("HeavyCharge"):TEXT("HeavyRelease");}
inline float Pose(float T)
{
    if(T<Charge)return Ease(T/Charge); // uppercut's full one-second load only
    if(T<Land-Downstroke)return WarhammerHeavy::ChargeSeconds;
    if(T<Land)return WarhammerHeavy::Contact*FMath::Pow(FMath::Clamp((T-Land+Downstroke)/Downstroke,0.f,1.f),2.f);
    if(T<Land+Planted)return WarhammerHeavy::Contact;
    return FMath::Lerp(WarhammerHeavy::HoldEnd,WarhammerHeavy::Duration,Ease((T-Land-Planted)/Recover));
}
inline float GroundWeight(float T)
{return Ease((T-(Land-Downstroke))/Downstroke)*(1.f-Ease((T-Land-Planted)/Recover));}
}
