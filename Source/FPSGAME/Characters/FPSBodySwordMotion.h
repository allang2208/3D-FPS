#pragma once
#include "FPSPlayerBodyTypes.h"
#include "../Weapons/RuneSwordWhirlwindFeel.h"
#include "../Weapons/RuneSwordUppercutMotion.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "FPSBodyHighlandMotion.h"
#include "../Skills/ChainSlashMotion.h"

/** Third-person source selection only; the sword executor owns time and hits. */
namespace FPSBodySwordMotion
{
inline bool IsUppercut(const FFPSBodyState& State)
{
    return State.Family==TEXT("Melee")&&State.Action==EFPSBodyAction::HeavyStrike&&
        State.ActionVariant==TEXT("Uppercut");
}
inline float UppercutPlaybackTime(const FFPSBodyState& State,float Progress)
{
    // Entry is the executor's release, expressed in playback seconds. Keeping
    // this on replicated progress also keeps the legs with the visible cut.
    return Progress*RuneSwordUppercutMotion::ReleaseStart/FMath::Max(.01f,State.ActionEntryFraction);
}
inline float UppercutSample(const FFPSBodyState& State,float Progress,float ContactPose,float ReleasePose)
{
    const float Contact=FMath::Clamp(State.ContactFraction,.01f,.98f);
    const float Release=FMath::Clamp(State.ReleaseFraction,Contact+.001f,.99f);
    const float Entry=FMath::Clamp(State.ActionEntryFraction,.001f,Contact-.001f);
    // Current Kwang recovery take: .16 s carry-to-load, then donor
    // PrimaryAttack_A_Slow .0666667 -> .20 at Contact. Only the carry-to-load
    // section belongs in the one-second charge; do not slow the rising blade
    // into that charge. Use the marker ratio to retain its authored rounding.
    const float LoadedPose=ContactPose*(.16f/(.16f+.20f-.0666667f));
    if(Progress<=Entry)
        return FMath::Lerp(0.f,LoadedPose,FMath::SmoothStep(0.f,Entry,Progress));
    if(Progress<=Contact)
    {
        // Push off in the loaded stance, then accelerate the blade through the
        // forward contact as the 150 cm sweep reaches its actual landing phase.
        const float Lunge=(Progress-Entry)/(Contact-Entry);
        const float Lift=FMath::Clamp((Lunge-.25f)/.75f,0.f,1.f);
        return FMath::Lerp(LoadedPose,ContactPose,Lift*Lift);
    }
    if(Progress<=Release)
        return FMath::Lerp(ContactPose,ReleasePose,(Progress-Contact)/(Release-Contact));
    return FMath::Lerp(ReleasePose,1.f,FMath::Clamp((Progress-Release)/(1.f-Release),0.f,1.f));
}
inline float WhirlwindModelYaw(const FFPSBodyState& State,float Progress)
{
    const float Ready=FMath::Clamp(State.ContactFraction,.01f,.98f);
    const float End=FMath::Clamp(State.ReleaseFraction,Ready+.001f,.99f);
    const float Phase=WhirlwindFeel::NormalizedPhase((Progress-Ready)/(End-Ready));
    // World-space performance relative to the release heading. The clips have
    // their donor root turn removed; both variants must supply this rotation.
    return -360.f*State.WhirlwindTurns*Phase;
}
inline float WhirlwindVisualYaw(const FFPSBodyState& State,float Progress)
{
    if(State.Action!=EFPSBodyAction::Whirlwind||State.ActionVariant==TEXT("ZhufengWhirlwind"))return 0.f;
    // The actor already contributes the gameplay turn. Subtract it twice so
    // the world-body performance turns the other way, without reversing the
    // authored windup/jump/plant or changing the camera and damage sweep.
    return FRotator::NormalizeAxis(2.f*WhirlwindModelYaw(State,Progress));
}
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
    case EFPSBodyAction::Strike:
        if(ChainSlashMotion::IsVariant(State.ActionVariant))
            return State.ActionVariant==ChainSlashMotion::Variant(2)?TEXT("Melee.FullBody.Slash2"):TEXT("Melee.FullBody.Slash1");
        if(State.ActionVariant==FPSBodyHighlandMotion::SweepReady)return TEXT("Melee.FullBody.HighlandBreakSweepReady");
        if(State.ActionVariant==TEXT("HighlandBreakSweep"))return TEXT("Melee.FullBody.HighlandBreakSweep");
        return State.ActionVariant==TEXT("Slash2")?TEXT("Melee.FullBody.Slash2"):TEXT("Melee.FullBody.Slash1");
    case EFPSBodyAction::HeavyStrike:
        if(State.ActionVariant==RingChainSweepMotion::Release)return TEXT("Melee.FullBody.HighlandBreakSweepReady");
        if(State.ActionVariant==TEXT("ChixiaoHeavy"))return TEXT("Melee.FullBody.ChixiaoHeavy");
        if(State.ActionVariant==TEXT("Uppercut"))return TEXT("Melee.FullBody.Uppercut");
        if(State.ActionVariant==TEXT("DashOverhead"))return TEXT("Melee.FullBody.DashOverhead");
        return State.ActionVariant==TEXT("HeavyRelease")?TEXT("Melee.FullBody.HeavyRelease"):TEXT("Melee.FullBody.Overhead");
    case EFPSBodyAction::Thrust:
        return HighlandRidgeThrust::IsRelease(State.ActionVariant)?TEXT("Melee.FullBody.HighlandRidgeThrust"):TEXT("Melee.FullBody.Thrust");
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
    case EFPSBodyAction::Charge:
        if(State.ActionVariant==RingChainSweepMotion::Charge)return TEXT("Melee.FullBody.HighlandBreakSweepReady");
        return State.ActionVariant==HighlandRidgeThrust::Charge?TEXT("Melee.FullBody.HighlandRidgeThrust"):TEXT("Melee.FullBody.Charge");
    case EFPSBodyAction::Guard:return TEXT("Melee.FullBody.Guard");
    case EFPSBodyAction::GuardHit:return TEXT("Melee.FullBody.GuardHit");
    case EFPSBodyAction::GuardBreak:return TEXT("Melee.FullBody.GuardBreak");
    default:return NAME_None;
    }
}
}
