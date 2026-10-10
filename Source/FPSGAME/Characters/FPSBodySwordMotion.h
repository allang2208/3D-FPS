#pragma once
#include "FPSPlayerBodyTypes.h"

/** Third-person source selection only; the sword executor owns time and hits. */
namespace FPSBodySwordMotion
{
inline float WhirlwindSample(const FFPSBodyState& State,float Progress)
{
    const float Ready=FMath::Clamp(State.ContactFraction,.01f,.98f);
    const float End=FMath::Clamp(State.ReleaseFraction,Ready+.001f,.99f);
    if(Progress<Ready)return FMath::Clamp(Progress/Ready,0.f,1.f);
    if(Progress>=End)return FMath::Clamp((Progress-End)/(1.f-End),0.f,1.f);
    // The Kwang turning slash supplies one complete take across the two turns.
    // Gameplay owns actor yaw; repeating the take would repeat its jump/plant.
    // This clock is supplied by the executor and still pauses during hitstop.
    return FMath::Clamp((Progress-Ready)/(End-Ready),0.f,1.f);
}
inline FName Clip(const FFPSBodyState& State)
{
    if(State.Family!=TEXT("Melee")||State.Motion==EFPSBodyMotion::Vault||State.Motion==EFPSBodyMotion::Mantle)return NAME_None;
    switch(State.Action)
    {
    case EFPSBodyAction::Strike:return State.ActionVariant==TEXT("Slash2")?TEXT("Melee.FullBody.Slash2"):TEXT("Melee.FullBody.Slash1");
    case EFPSBodyAction::HeavyStrike:
        if(State.ActionVariant==TEXT("Uppercut"))return TEXT("Melee.FullBody.Uppercut");
        if(State.ActionVariant==TEXT("DashOverhead"))return TEXT("Melee.FullBody.DashOverhead");
        return State.ActionVariant==TEXT("HeavyRelease")?TEXT("Melee.FullBody.HeavyRelease"):TEXT("Melee.FullBody.Overhead");
    case EFPSBodyAction::Thrust:return TEXT("Melee.FullBody.Thrust");
    case EFPSBodyAction::Pommel:return TEXT("Melee.FullBody.Pommel");
    case EFPSBodyAction::Whirlwind:
        // Tang Dao's single edge is mounted half a turn from the double-edged
        // sword frame. Its clips seat that edge during windup; gameplay yaw
        // and the accepted shoulder/elbow performance remain shared.
        if(State.Weapon==TEXT("ue_tang_dao"))
        {
            if(State.ActionProgress<State.ContactFraction)return TEXT("Melee.FullBody.TangDao.Whirlwind.Start");
            return State.ActionProgress<State.ReleaseFraction?TEXT("Melee.FullBody.TangDao.Whirlwind.Loop"):TEXT("Melee.FullBody.TangDao.Whirlwind.End");
        }
        if(State.ActionProgress<State.ContactFraction)return TEXT("Melee.FullBody.Whirlwind.Start");
        return State.ActionProgress<State.ReleaseFraction?TEXT("Melee.FullBody.Whirlwind.Loop"):TEXT("Melee.FullBody.Whirlwind.End");
    case EFPSBodyAction::Charge:return TEXT("Melee.FullBody.Charge");
    case EFPSBodyAction::Guard:return TEXT("Melee.FullBody.Guard");
    case EFPSBodyAction::GuardHit:return TEXT("Melee.FullBody.GuardHit");
    case EFPSBodyAction::GuardBreak:return TEXT("Melee.FullBody.GuardBreak");
    default:return NAME_None;
    }
}
}
