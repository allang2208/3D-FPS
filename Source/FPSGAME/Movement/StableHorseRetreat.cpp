#include "StableRidingHorse.h"
#include "HorseRiderComponent.h"
#include "StableManeComponent.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInterface.h"

namespace HorseRetreat
{
    // Warhorse Lite Rear: both front hooves are lifted at frame 20 of 75.
    constexpr float ThrowFraction=20.f/75.f;
    constexpr float RunBeforeFade=2.1f;
    constexpr float FadeSeconds=1.25f;
}

void AStableRidingHorse::TickRetreat(float Delta)
{
    auto* Move=GetCharacterMovement();
    if(RetreatStartedAt<0.)
    {
        if(!HasAuthority() || Move->IsFalling())
        {
            if(HasAuthority() && InJump())AdvanceJump(Delta);
            UpdateGait(Delta);
            Mane->UpdateMotion(Delta);
            return;
        }
        if(InJump())SetJumpPhase(EStableJumpPhase::Grounded);
        Halt();
        PivotWeight=0.f;
        PivotDegreesPerSecond=0;
        bLeftStall=true;
        RetreatStartedAt=JumpClock();
        ForceNetUpdate();
    }

    const float Age=FMath::Max(0.,JumpClock()-RetreatStartedAt);
    const float RearTime=RearAnimation?RearAnimation->GetPlayLength():2.5f;
    if(HasAuthority() && Rider && Age>=RearTime*HorseRetreat::ThrowFraction)
        if(auto* Ride=Rider->FindComponentByClass<UHorseRiderComponent>())Ride->ThrowFromHorse(*this);

    if(Age<RearTime)
    {
        if(bFadeMaterialsApplied)ApplyHorseFade(0.f);
        if(RearAnimation)
        {
            auto* Skin=GetMesh();
            Skin->VisibilityBasedAnimTickOption=Rider?EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones:EVisibilityBasedAnimTickOption::AlwaysTickPose;
            if(CurrentClip!=RearAnimation)
            {
                Skin->SetAnimation(RearAnimation);
                Skin->Play(false);
                Skin->SetPlayRate(0.f);
                CurrentClip=RearAnimation;
            }
            Skin->SetPosition(Age,false);
        }
    }
    else
    {
        const float RunAge=Age-RearTime;
        if(RunAge>=HorseRetreat::RunBeforeFade+HorseRetreat::FadeSeconds)
        {
            if(HasAuthority())Destroy();
            else SetActorHiddenInGame(true);
            return;
        }
        if(HasAuthority())RunFromDanger(Delta);
        UpdateGait(Delta);
        if(RunAge>=HorseRetreat::RunBeforeFade)
        {
            UpdateAuxiliaryCollision(false,false);
            if(GetNetMode()!=NM_DedicatedServer)
                ApplyHorseFade(FMath::SmoothStep(0.f,HorseRetreat::FadeSeconds,RunAge-HorseRetreat::RunBeforeFade));
        }
    }
    Mane->UpdateMotion(Delta);
}

void AStableRidingHorse::RunFromDanger(float Delta)
{
    auto* Move=GetCharacterMovement();
    const float Yaw=GetActorRotation().Yaw;
    if(!bEscapeRunning)
    {
        bEscapeRunning=true;
        EscapeYaw=Yaw;
        Move->SetMovementMode(MOVE_Walking);
        Move->bCanWalkOffLedges=false;
        Move->MaxWalkSpeed=Traits.CanterSpeed();
    }
    // Accelerate along the current heading. In the enclosed stable, find a clear turn
    // before putting the shoulders through a gate or driving the capsule into a wall.
    const float LookAhead=FMath::Max(92.f,float(GetVelocity().Size2D())*.22f);
    const double Now=JumpClock();
    const FRotator Desired(0,EscapeYaw,0);
    if(Now>=NextEscapeTurn && !ClearBody(Desired.Vector()*LookAhead,Desired))
    {
        NextEscapeTurn=Now+.22;
        for(const float Offset:{35.f,-35.f,70.f,-70.f,105.f,-105.f,145.f,-145.f,180.f})
        {
            const FRotator Option(0,Yaw+Offset,0);
            if(ClearBody(Option.Vector()*LookAhead,Option))
            {
                EscapeYaw=Option.Yaw;
                break;
            }
        }
    }
    const float Error=FMath::FindDeltaAngleDegrees(Yaw,EscapeYaw);
    const FRotator Facing(0,Yaw+FMath::Clamp(Error,-150.f*Delta,150.f*Delta),0);
    if(!FMath::IsNearlyZero(Error) && ClearBody(FVector::ZeroVector,Facing))SetActorRotation(Facing);
    const FVector Forward=GetActorForwardVector();
    if(FMath::Abs(Error)<65.f && ClearBody(Forward*FMath::Max(15.f,Traits.CanterSpeed()*Delta),GetActorRotation()))
        AddMovementInput(Forward,1.f,true);
    else Move->StopMovementImmediately();
}
