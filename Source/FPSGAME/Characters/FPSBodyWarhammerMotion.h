#pragma once
#include "FPSPlayerBodyTypes.h"

/** Authored hammer body performances. ProductionTool still owns time and hits. */
namespace FPSBodyWarhammerMotion
{
inline bool IsNormalClip(FName Key)
{
    return Key==TEXT("Warhammer.FullBody.Slash1")||Key==TEXT("Warhammer.FullBody.Slash2")||Key==TEXT("Warhammer.FullBody.Slash3");
}
inline bool IsCarry(const FFPSBodyState& S)
{
    return S.Family==TEXT("Tool")&&S.Weapon==TEXT("warhammer")&&
        (S.Action==EFPSBodyAction::None||S.Action==EFPSBodyAction::Inspect);
}
inline FName Clip(const FFPSBodyState& S)
{
    if(S.Family!=TEXT("Tool")||S.Weapon!=TEXT("warhammer")||
        S.Motion==EFPSBodyMotion::Vault||S.Motion==EFPSBodyMotion::Mantle)return NAME_None;
    if(IsCarry(S)&&S.Motion==EFPSBodyMotion::Ground)
        return S.ActionVariant==TEXT("WarhammerSprintReady")?TEXT("Warhammer.FullBody.SprintCarry"):TEXT("Warhammer.FullBody.Carry");
    if(S.Action==EFPSBodyAction::Strike||S.Action==EFPSBodyAction::HeavyStrike||S.Action==EFPSBodyAction::ToolRecover)
    {
        // A hit no longer replaces the donor's follow-through with a separately
        // constructed first-person-style recovery. Keep the complete take.
        if(S.ActionVariant==TEXT("WarhammerSlash1"))return TEXT("Warhammer.FullBody.Slash1");
        if(S.ActionVariant==TEXT("WarhammerSlash2"))return TEXT("Warhammer.FullBody.Slash2");
        if(S.ActionVariant==TEXT("WarhammerSlash3"))return TEXT("Warhammer.FullBody.Slash3");
        if(S.ActionVariant==TEXT("WarhammerSlam"))return TEXT("Warhammer.FullBody.Slam");
        if(S.ActionVariant==TEXT("WarhammerSprintSlam"))return TEXT("Warhammer.FullBody.SprintSlam");
        if(S.ActionVariant==TEXT("WarhammerUppercut"))return TEXT("Warhammer.FullBody.Uppercut");
    }
    if(S.Action==EFPSBodyAction::Charge&&S.ActionVariant==TEXT("WarhammerCharge"))return TEXT("Warhammer.FullBody.Charge");
    if(S.Action==EFPSBodyAction::Charge&&S.ActionVariant==TEXT("WarhammerSprintLift"))return TEXT("Warhammer.FullBody.SprintLift");
    if(S.Action==EFPSBodyAction::Whirlwind)
    {
        if(S.ActionProgress<S.ContactFraction)return TEXT("Warhammer.FullBody.Whirlwind.Start");
        return S.ActionProgress<S.ReleaseFraction?TEXT("Warhammer.FullBody.Whirlwind.Loop"):TEXT("Warhammer.FullBody.Whirlwind.End");
    }
    if(S.Action==EFPSBodyAction::Guard)
    {
        if(S.ActionVariant==TEXT("WarhammerGuardHold"))return TEXT("Warhammer.FullBody.GuardHold");
        if(S.ActionVariant==TEXT("WarhammerGuardExit"))return TEXT("Warhammer.FullBody.GuardExit");
        return TEXT("Warhammer.FullBody.GuardEnter");
    }
    if(S.Action==EFPSBodyAction::GuardHit)return TEXT("Warhammer.FullBody.GuardHit");
    if(S.Action==EFPSBodyAction::GuardBreak)return TEXT("Warhammer.FullBody.GuardBreak");
    if(S.Action==EFPSBodyAction::GunBash&&S.ActionVariant==TEXT("WarhammerHeadThrust"))return TEXT("Warhammer.FullBody.QuickMelee");
    return NAME_None;
}

/** Presentation-only clock for complete donor takes. Gameplay owns all hits. */
struct FDonorPlayback
{
    FName Variant;
    EFPSBodyAction Action=EFPSBodyAction::None;
    float Seconds=0.f,PreviousProgress=0.f,RecoveryFrom=0.f,WindupElapsed=0.f,ReleaseFrom=0.f;
    bool bActive=false,bWindup=false,bSustained=false;

    void Reset(){Variant=NAME_None;Action=EFPSBodyAction::None;Seconds=PreviousProgress=RecoveryFrom=WindupElapsed=ReleaseFrom=0.f;bActive=bWindup=bSustained=false;}

    float Advance(const FFPSBodyState& S,float Delta,float Length,float Contact,float FollowThrough)
    {
        const float P=FMath::Clamp(S.ActionProgress,0.f,1.f);
        bSustained=true;
        if(S.Action==EFPSBodyAction::Whirlwind)
        {
            const float Ready=FMath::Clamp(S.ContactFraction,.01f,.98f);
            const float End=FMath::Clamp(S.ReleaseFraction,Ready+.001f,.99f);
            const float Phase=P<Ready?P/Ready:P<End?(P-Ready)/(End-Ready):(P-End)/(1.f-End);
            Seconds=FMath::Clamp(Phase,0.f,1.f)*Length;
        }
        else if(S.Action==EFPSBodyAction::Guard)
        {
            if(S.ActionVariant==TEXT("WarhammerGuardHold"))
            {
                if(!bActive||Variant!=S.ActionVariant)Seconds=0.f;
                Seconds=FMath::Fmod(Seconds+FMath::Max(0.f,Delta),FMath::Max(.001f,Length));
            }
            else Seconds=(S.ActionVariant==TEXT("WarhammerGuardExit")?1.f-P:P)*Length;
        }
        else if(S.Action==EFPSBodyAction::GuardHit||S.Action==EFPSBodyAction::GuardBreak)Seconds=P*Length;
        else bSustained=false;
        if(bSustained)
        {
            Variant=S.ActionVariant;Action=S.Action;PreviousProgress=P;bActive=true;bWindup=false;
            return Seconds;
        }
        const bool Windup=S.Action==EFPSBodyAction::Charge;
        const bool Release=S.ActionVariant==TEXT("WarhammerSlam")||S.ActionVariant==TEXT("WarhammerSprintSlam");
        const float LoadedTime=FMath::Clamp(Contact*.5f,0.f,Length);
        const float Follow=FMath::Clamp(FollowThrough,Contact,Length);
        const auto Ease=[](float U){U=FMath::Clamp(U,0.f,1.f);return U*U*(3.f-2.f*U);};
        // Keep a little momentum across gather/release/recovery boundaries.
        // Zero velocity at every phase boundary made the body stop repeatedly.
        const auto Gather=[](float U){U=FMath::Clamp(U,0.f,1.f);return U*U*(2.f-U);};
        const auto Drive=[](float U){U=FMath::Clamp(U,0.f,1.f);return U*(.35f+.65f*U);};
        const auto Brake=[](float U){U=FMath::Clamp(U,0.f,1.f);return U*(1.65f-.65f*U);};
        const auto Settle=[](float U){U=FMath::Clamp(U,0.f,1.f);return U*(.35f+U*(2.3f-1.65f*U));};
        const float Hit=FMath::Clamp(S.ContactFraction,.01f,.99f);
        if(Windup)
        {
            if(!bActive||Variant!=S.ActionVariant)WindupElapsed=0.f;
            WindupElapsed+=FMath::Max(0.f,Delta);
            const bool Sprint=S.ActionVariant==TEXT("WarhammerSprintLift");
            const float Lift=Ease(WindupElapsed/(Sprint?.20f:.28f));
            // Continue tightening the existing full-body take during charge,
            // then breathe within a tiny loaded-pose range instead of freezing.
            // Stable neck/head handling still runs after the body pose is sampled.
            const float Breath=Sprint?0.f:.025f*FMath::Sin(WindupElapsed*2.4f)*Ease(WindupElapsed/.6f);
            Seconds=LoadedTime*Lift*(.82f+.18f*Ease(P)+Breath);
        }
        else if(S.Action==EFPSBodyAction::ToolRecover)
        {
            // Hit recovery has a new 0..1 clock, but remains the same donor take.
            // Keep a late confirmed hit from rewinding an already visible stroke.
            if(!bActive||Variant!=S.ActionVariant||Action!=EFPSBodyAction::ToolRecover||P+.2f<PreviousProgress)
                RecoveryFrom=FMath::Clamp(bActive&&Variant==S.ActionVariant?FMath::Max(Seconds,Contact):Contact,Contact,Length);
            const float End=FMath::Clamp(S.ReleaseFraction,.01f,.99f);
            const float Finish=FMath::Max(RecoveryFrom,Follow);
            Seconds=P<End?FMath::Lerp(RecoveryFrom,Finish,Brake(P/End)):
                FMath::Lerp(Finish,Length,Settle((P-End)/(1.f-End)));
        }
        else if(P<Hit)
        {
            // A source's short strike must not be stretched across the entire
            // gameplay windup. Gather first, then accelerate through its original
            // arc in the real release window; contact still lands exactly at Hit.
            const float Entry=FMath::Clamp(S.ActionEntryFraction>0.f?S.ActionEntryFraction:Hit*.75f,.001f,Hit-.001f);
            if(Release)
            {
                if(!bActive||Variant!=S.ActionVariant||P+.2f<PreviousProgress)
                    ReleaseFrom=FMath::Clamp(bWindup?Seconds:LoadedTime,0.f,Contact);
                Seconds=FMath::Lerp(ReleaseFrom,Contact,Drive(P/Hit));
            }
            else Seconds=P<Entry?LoadedTime*Gather(P/Entry):
                FMath::Lerp(LoadedTime,Contact,Drive((P-Entry)/(Hit-Entry)));
        }
        else
        {
            // Momentum and recovery follow the gameplay phase, including attack
            // speed and network progress, instead of advancing at source 1x.
            const float End=FMath::Clamp(S.ReleaseFraction,Hit+.001f,.999f);
            Seconds=P<End?FMath::Lerp(Contact,Follow,Brake((P-Hit)/(End-Hit))):
                FMath::Lerp(Follow,Length,Settle((P-End)/(1.f-End)));
        }
        Variant=S.ActionVariant;Action=S.Action;PreviousProgress=P;
        bActive=true;bWindup=Windup;
        return Seconds;
    }

    float Weight(float Length) const
    {
        return bWindup||bSustained?1.f:1.f-FMath::SmoothStep(FMath::Max(0.f,Length-.12f),Length,Seconds);
    }
};
}
