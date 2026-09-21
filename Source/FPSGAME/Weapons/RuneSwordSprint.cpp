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
    const bool bRequested=Pawn&&Pawn->IsSprinting()&&Pawn->GetVelocity().SizeSquared2D()>2500.f&&
        Pawn->GetCharacterMovement()->IsMovingOnGround()&&!Pawn->IsDodging()&&!Pawn->IsSliding()&&
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
        if(CurrentClip==TEXT("SprintLoop"))
        {
            // The character caches the audio stride phase before this component
            // ticks. Camera, feet and blade therefore sample the same cycle.
            const float Phase=FMath::Fmod(Pawn->M4SprintPhase,2.f*PI)/(2.f*PI);
            Elapsed=Phase*CurrentAnimation->GetPlayLength();
        }
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
    Elapsed=FMath::Min(Elapsed+Delta,CurrentAnimation->GetPlayLength());
    SamplePose(Elapsed);
    if(Elapsed>=CurrentAnimation->GetPlayLength())
        SetClip(Pawn->GetVelocity().SizeSquared2D()>400.f?TEXT("Walk"):TEXT("Idle"),true);
    return true;
}
