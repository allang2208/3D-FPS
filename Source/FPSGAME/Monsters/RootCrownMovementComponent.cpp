#include "RootCrownMovementComponent.h"
#include "RootCrownRigPreview.h"
#include "MonsterAIController.h"

bool URootCrownMovementComponent::DesiredHeading(float& Yaw) const
{
    if (!CharacterOwner || !IsMovingOnGround()) return false;
    const auto* AI=Cast<AMonsterAIController>(CharacterOwner->GetController());
    if (!AI || !AI->bDecisionEnabled) return false;
    const auto* Crown=Cast<ARootCrownRigPreview>(CharacterOwner);
    if(Crown && Crown->DesiredFacingYaw(Yaw))return true;
    if(Crown && Crown->Busy())return false;
    // Consume the current path request only; a completed path must not leave
    // a remembered heading rotating an otherwise resting creature.
    const FVector Direction=bHasRequestedVelocity?RequestedVelocity:Acceleration;
    if (Direction.IsNearlyZero()) return false;
    Yaw=Direction.Rotation().Yaw;return true;
}
float URootCrownMovementComponent::GetMaxSpeed() const
{
    float Desired=0.f;const float Base=Super::GetMaxSpeed();
    if(const auto* Crown=Cast<ARootCrownRigPreview>(CharacterOwner);Crown&&Crown->Busy()&&IsMovingOnGround())return 0.f;
    if (!DesiredHeading(Desired)) return Base;
    const float Error=FMath::Abs(FMath::FindDeltaAngleDegrees(CharacterOwner->GetActorRotation().Yaw,Desired));
    if (bPivot || Error>=70.f) return 0.f;
    return Base*FMath::GetMappedRangeValueClamped(FVector2D(15.f,70.f),FVector2D(1.f,.15f),Error);
}
void URootCrownMovementComponent::PhysicsRotation(float Dt)
{
    const auto* Crown=Cast<ARootCrownRigPreview>(CharacterOwner);
    if (!Crown || !Crown->HasAuthority() || !UpdatedComponent || Dt<=0.f) return;
    float Desired=0.f;
    if (!DesiredHeading(Desired)) {TurnVelocity=0.f;bPivot=false;return;}
    const float Yaw=UpdatedComponent->GetComponentRotation().Yaw;
    const float Delta=FMath::FindDeltaAngleDegrees(Yaw,Desired),Error=FMath::Abs(Delta);
    if (Error>=70.f) bPivot=true;
    else if (Error<=12.f) bPivot=false;
    constexpr float AccelerationDegrees=540.f;
    const float Maximum=Crown->IsAttacking()?35.f:Crown->TurnSpeed;
    const float Wanted=FMath::Sign(Delta)*FMath::Min(Maximum,FMath::Sqrt(2.f*AccelerationDegrees*Error));
    TurnVelocity=FMath::FInterpConstantTo(TurnVelocity,Wanted,Dt,AccelerationDegrees);
    TurnVelocity=FMath::Clamp(TurnVelocity,-Maximum,Maximum);
    float Step=TurnVelocity*Dt;
    if (FMath::Sign(Step)==FMath::Sign(Delta) && FMath::Abs(Step)>=Error) {Step=Delta;TurnVelocity=0.f;}
    MoveUpdatedComponent(FVector::ZeroVector,FRotator(0,Yaw+Step,0).Quaternion(),true);
}
void URootCrownMovementComponent::OnTeleported()
{
    TurnVelocity=0.f;bPivot=false;Super::OnTeleported();
}
