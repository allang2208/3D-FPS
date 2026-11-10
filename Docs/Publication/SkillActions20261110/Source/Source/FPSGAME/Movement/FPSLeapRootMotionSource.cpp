#include "FPSLeapRootMotionSource.h"
#include "FPSCharacterMovementComponent.h"
#include "../Skills/LeapStrikeMotion.h"
#include "../Production/ProductionToolComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/PhysicsVolume.h"

FRootMotionSource_FPSLeap::FRootMotionSource_FPSLeap()
{
    Settings.UnSetFlag(ERootMotionSourceSettingsFlags::DisablePartialEndTick);
    FinishVelocityParams.Mode=ERootMotionFinishVelocityMode::MaintainLastRootMotionVelocity;
}
FRootMotionSource* FRootMotionSource_FPSLeap::Clone() const{return new FRootMotionSource_FPSLeap(*this);}
UScriptStruct* FRootMotionSource_FPSLeap::GetScriptStruct() const{return StaticStruct();}
bool FRootMotionSource_FPSLeap::MatchesAndHasSameState(const FRootMotionSource* Other) const
{
    if(!FRootMotionSource_MoveToForce::MatchesAndHasSameState(Other))return false;
    const auto* Source=static_cast<const FRootMotionSource_FPSLeap*>(Other);
    return bLaunched==Source->bLaunched&&LinearVelocity.Equals(Source->LinearVelocity,.1f);
}
bool FRootMotionSource_FPSLeap::UpdateStateFrom(const FRootMotionSource* Other,bool SimulatedCatchup)
{
    if(!FRootMotionSource_MoveToForce::UpdateStateFrom(Other,SimulatedCatchup))return false;
    const auto* Source=static_cast<const FRootMotionSource_FPSLeap*>(Other);
    LinearVelocity=Source->LinearVelocity;bLaunched=Source->bLaunched;bRestoreVelocity=bLaunched;return true;
}
bool FRootMotionSource_FPSLeap::NetSerialize(FArchive& Ar,UPackageMap* Map,bool& Success)
{
    const bool Result=FRootMotionSource_MoveToForce::NetSerialize(Ar,Map,Success);
    Ar<<LinearVelocity;Ar<<bLaunched;
    if(Ar.IsLoading())bRestoreVelocity=bLaunched;
    Success=Success&&!Ar.IsError();return Result;
}
void FRootMotionSource_FPSLeap::PrepareRootMotion(float SimulationTime,float MovementTickTime,
    const ACharacter&,const UCharacterMovementComponent& Move)
{
    RootMotionParams.Clear();
    if(!bLaunched&&SimulationTime>UE_SMALL_NUMBER)
    {
        LeapStrike::FTrajectory Path;
        if(LeapStrike::SolveTrajectory(StartLocation,TargetLocation,Move.GetGravityZ(),Move.GetPhysicsVolume()->TerminalVelocity,Path))
        {LinearVelocity=Path.Velocity;bLaunched=true;bRestoreVelocity=true;}
    }
    // The override marker suppresses air-control/friction. PhysFalling below
    // consumes the seed once; native gravity and impact deflection own velocity.
    if(bLaunched&&!bRestoreVelocity)LinearVelocity=Move.Velocity;
    // PerformMovement accumulates overrides once before PhysFalling as well.
    // Pass through the incoming physical velocity there; never output zero.
    RootMotionParams.Set(FTransform(LinearVelocity));
    SetTime(FMath::Min(GetTime()+SimulationTime,Duration));
}

void UFPSCharacterMovementComponent::ApplyRootMotionToVelocity(float DeltaTime)
{
    if(IsFalling()&&GetRootMotionSource(LeapStrike::MotionName))return;
    Super::ApplyRootMotionToVelocity(DeltaTime);
}

void UFPSCharacterMovementComponent::PhysFalling(float DeltaTime,int32 Iterations)
{
    auto* Tool=CharacterOwner?CharacterOwner->FindComponentByClass<UProductionToolComponent>():nullptr;
    const auto Base=GetRootMotionSource(LeapStrike::MotionName);
    const auto Source=Base&&Base->GetScriptStruct()==FRootMotionSource_FPSLeap::StaticStruct()?StaticCastSharedPtr<FRootMotionSource_FPSLeap>(Base):nullptr;
    if(!Source&&!(Tool&&Tool->bLeapStrike&&Tool->bLeapLaunched&&!Tool->bLeapLanded))
    {Super::PhysFalling(DeltaTime,Iterations);return;}
    if(Source&&Source->bRestoreVelocity)
    {
        Velocity=Source->LinearVelocity;Source->bRestoreVelocity=false;
        CharacterOwner->ResetJumpState();
    }
    TGuardValue<FVector> NoSteering(Acceleration,FVector::ZeroVector);
    TGuardValue<float> NoDrag(FallingLateralFriction,0.f);
    TGuardValue<float> NoBraking(BrakingDecelerationFalling,0.f);
    TGuardValue<float> NoSeparateBrake(BrakingFriction,0.f);
    Super::PhysFalling(DeltaTime,Iterations);
    if(Source)Source->LinearVelocity=Velocity;
}

void UFPSCharacterMovementComponent::ProcessLanded(const FHitResult& Hit,float RemainingTime,int32 Iterations)
{
    auto* Tool=CharacterOwner?CharacterOwner->FindComponentByClass<UProductionToolComponent>():nullptr;
    if(!GetRootMotionSource(LeapStrike::MotionName)&&!(Tool&&Tool->bLeapStrike&&Tool->bLeapLaunched&&!Tool->bLeapLanded))
    {Super::ProcessLanded(Hit,RemainingTime,Iterations);return;}
    // Consume the remaining frame at this contact, rather than carrying launch
    // momentum across the floor before the tool's next tick can observe landing.
    Super::ProcessLanded(Hit,0.f,Iterations);
    if(IsMovingOnGround())
    {
        RemoveRootMotionSource(LeapStrike::MotionName);StopMovementImmediately();
        if(Tool)Tool->CompleteLeapLanding(Hit);
    }
}
