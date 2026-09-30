#include "RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Animation/AnimSequence.h"

bool URuneSwordComponent::HasTacticalSprintAnimations() const
{
    return Animations.FindRef(TEXT("SprintEnter")) && Animations.FindRef(TEXT("SprintLoop")) &&
        Animations.FindRef(TEXT("SprintExit")) && Animations.FindRef(TEXT("SprintOverhead"));
}

bool URuneSwordComponent::IsTacticalSprintClip(FName Clip) const
{
    return Clip==TEXT("SprintEnter")||Clip==TEXT("SprintLoop")||Clip==TEXT("SprintExit");
}

float URuneSwordComponent::TacticalSprintPoseWeight() const
{
    if(!IsEquipped()||IsBusy()||!CanUse()||!CurrentAnimation)return 0.f;
    const float Progress=FMath::Clamp(Elapsed/FMath::Max(.01f,CurrentAnimation->GetPlayLength()),0.f,1.f);
    if(CurrentClip==TEXT("SprintEnter"))return FMath::SmoothStep(0.f,1.f,Progress);
    if(CurrentClip==TEXT("SprintLoop"))return 1.f;
    if(CurrentClip==TEXT("SprintExit"))return 1.f-FMath::SmoothStep(0.f,1.f,Progress);
    return 0.f;
}

bool URuneSwordComponent::TickTacticalSprintPose(float Delta)
{
    if(!HasTacticalSprintAnimations())return false;
    const auto* Pawn=Character.Get();
    const bool bGroundSprint=Pawn&&Pawn->IsSprinting()&&!Pawn->bWeaponJumpAirborne&&
        Pawn->GetCharacterMovement()->IsMovingOnGround()&&!Pawn->IsSliding();
    // The readiness model already retains an earned charge through slides and
    // jumps, including the pending launch frame. Keep its carry pose as well.
    const bool bRequested=Pawn&&!Pawn->IsDodging()&&
        !Pawn->IsCastBlockingLeftHandAction()&&DashReadyFraction()>=1.f-UE_SMALL_NUMBER;
    if(bRequested)
    {
        if(CurrentClip!=TEXT("SprintEnter")&&CurrentClip!=TEXT("SprintLoop"))
        {
            const float Resume=CurrentClip==TEXT("SprintExit")
                ? 1.f-FMath::Clamp(Elapsed/FMath::Max(.01f,CurrentAnimation->GetPlayLength()),0.f,1.f):0.f;
            SetClip(TEXT("SprintEnter"),false);
            Elapsed=Resume*CurrentAnimation->GetPlayLength();
        }
        if(CurrentClip==TEXT("SprintEnter"))
        {
            Elapsed=FMath::Min(Elapsed+Delta,CurrentAnimation->GetPlayLength());
            if(Elapsed>=CurrentAnimation->GetPlayLength())SetClip(TEXT("SprintLoop"),true);
        }
        if(CurrentClip==TEXT("SprintLoop")&&bGroundSprint)
        {
            // The character caches the audio stride phase before this component
            // ticks. Camera, feet and blade therefore sample the same cycle.
            const float Phase=FMath::Fmod(Pawn->M4SprintPhase,2.f*PI)/(2.f*PI);
            Elapsed=Phase*CurrentAnimation->GetPlayLength();
        }
        // Sliding/airborne movement holds the last carry sample instead of
        // playing running strides. The shared jump root still adds inertia.
        SamplePose(Elapsed);
        return true;
    }
    if(!IsTacticalSprintClip(CurrentClip))return false;
    if(CurrentClip!=TEXT("SprintExit"))
    {
        const float Raised=CurrentClip==TEXT("SprintEnter")
            ? FMath::Clamp(Elapsed/FMath::Max(.01f,CurrentAnimation->GetPlayLength()),0.f,1.f):1.f;
        SetClip(TEXT("SprintExit"),false);
        Elapsed=(1.f-Raised)*CurrentAnimation->GetPlayLength();
    }
    // The authored exit is shorter than the entry (0.20 s vs 0.50 s).
    // Keep its supported two-hand path, but return over the same real-time
    // duration as entering. Elapsed stays in source time so interrupted
    // enter/exit progress and the shared camera weight remain aligned.
    const float ExitLength=CurrentAnimation->GetPlayLength();
    const float ReturnSeconds=FMath::Max(.01f,Animations.FindRef(TEXT("SprintEnter"))->GetPlayLength());
    Elapsed=FMath::Min(Elapsed+Delta*ExitLength/ReturnSeconds,ExitLength);
    SamplePose(Elapsed);
    if(Elapsed>=ExitLength)
        SetClip(Pawn->GetCharacterMovement()->IsMovingOnGround()&&!Pawn->bWeaponJumpAirborne&&!Pawn->IsSliding()
            &&Pawn->GetVelocity().SizeSquared2D()>400.f?TEXT("Walk"):TEXT("Idle"),true);
    return true;
}
