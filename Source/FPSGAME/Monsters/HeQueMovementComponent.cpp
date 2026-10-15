#include "HeQueMovementComponent.h"
#include "HeQueMonster.h"
#include "MonsterAIController.h"

bool UHeQueMovementComponent::DesiredHeading(float& Yaw) const
{
    if (!CharacterOwner || !IsMovingOnGround()) return false;
    const auto* AI=Cast<AMonsterAIController>(CharacterOwner->GetController());
    if (!AI || !AI->bDecisionEnabled) return false;
    const auto* Crown=Cast<AHeQueMonster>(CharacterOwner);
    if(Crown && Crown->Busy())return false;
    if(Crown && Crown->DesiredCombatFacing(Yaw))return true;
    // Consume the current path request only; a completed path must not leave
    // a remembered heading rotating an otherwise resting creature.
    const FVector Direction=bHasRequestedVelocity?RequestedVelocity:Acceleration;
    if (Direction.IsNearlyZero()) return false;
    Yaw=Direction.Rotation().Yaw;return true;
}
float UHeQueMovementComponent::GetMaxSpeed() const
{
    float Desired=0.f;const float Base=Super::GetMaxSpeed();
    if(const auto* Crown=Cast<AHeQueMonster>(CharacterOwner);Crown&&Crown->Busy()&&IsMovingOnGround())return 0.f;
    if (!DesiredHeading(Desired)) return Base;
    const float Error=FMath::Abs(FMath::FindDeltaAngleDegrees(CharacterOwner->GetActorRotation().Yaw,Desired));
    if (bPivot || Error>=70.f) return 0.f;
    return Base*FMath::GetMappedRangeValueClamped(FVector2D(15.f,70.f),FVector2D(1.f,.15f),Error);
}
void UHeQueMovementComponent::PhysicsRotation(float Dt)
{
    const auto* Crown=Cast<AHeQueMonster>(CharacterOwner);
    if (!Crown || !Crown->HasAuthority() || !UpdatedComponent || Dt<=0.f) return;
    float Desired=0.f;
    if (!DesiredHeading(Desired)) {TurnVelocity=0.f;bPivot=false;return;}
    const float Yaw=UpdatedComponent->GetComponentRotation().Yaw;
    const float Delta=FMath::FindDeltaAngleDegrees(Yaw,Desired),Error=FMath::Abs(Delta);
    if (Error>=70.f) bPivot=true;
    else if (Error<=12.f) bPivot=false;
    const float Maximum=Crown->TurnSpeed;
    // Reach the requested turning rate in about one third of a second while
    // preserving the existing braking and distance-matched planted steps.
    const float AccelerationDegrees=FMath::Max(120.f,Maximum*3.f);
    const float Wanted=FMath::Sign(Delta)*FMath::Min(Maximum,FMath::Sqrt(2.f*AccelerationDegrees*Error));
    TurnVelocity=FMath::FInterpConstantTo(TurnVelocity,Wanted,Dt,AccelerationDegrees);
    TurnVelocity=FMath::Clamp(TurnVelocity,-Maximum,Maximum);
    float Step=TurnVelocity*Dt;
    if (FMath::Sign(Step)==FMath::Sign(Delta) && FMath::Abs(Step)>=Error) {Step=Delta;TurnVelocity=0.f;}
    MoveUpdatedComponent(FVector::ZeroVector,FRotator(0,Yaw+Step,0).Quaternion(),true);
}
void UHeQueMovementComponent::OnTeleported()
{
    TurnVelocity=0.f;bPivot=false;Super::OnTeleported();
}
