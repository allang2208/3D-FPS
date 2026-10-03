#include "M10MovementComponent.h"
#include "M10Mawcrawler.h"
#include "MonsterAIController.h"
#include "Components/CapsuleComponent.h"

bool UM10MovementComponent::DesiredHeading(float& Yaw) const
{
    const auto* M=Cast<AM10Mawcrawler>(CharacterOwner);
    if(!M||M->Busy()||!IsMovingOnGround())return false;
    if(const auto* AI=Cast<AMonsterAIController>(M->GetController());!AI||!AI->bDecisionEnabled)return false;
    // The remembered target selects the nearer combat end independently of
    // cooldowns. Rear engagement holds only inside gas range; distant targets
    // use the path heading below so the monster can turn and approach them.
    if(M->GetCloseFacingYaw(Yaw))return true;
    if(M->State!=EM10State::Crawl&&M->State!=EM10State::Returning)return false;
    FVector Direction=bHasRequestedVelocity?RequestedVelocity:Acceleration;
    if(Direction.IsNearlyZero())Direction=GetLastUpdateRequestedVelocity();
    if(Direction.IsNearlyZero())return false;
    Yaw=Direction.Rotation().Yaw;return true;
}
float UM10MovementComponent::GetMaxSpeed() const
{
    const float Base=Super::GetMaxSpeed();
    float Desired=0.f;if(!DesiredHeading(Desired))return Base;
    const auto* M=CastChecked<AM10Mawcrawler>(CharacterOwner);
    const float Error=FMath::Abs(FMath::FindDeltaAngleDegrees(M->GetActorRotation().Yaw,Desired));
    if(bPivot||Error>=M->PivotStartAngle)return 0.f;
    return Base*FMath::GetMappedRangeValueClamped(FVector2D(M->SlowTurnAngle,M->PivotStartAngle),FVector2D(1.f,.12f),Error);
}
void UM10MovementComponent::PhysicsRotation(float Dt)
{
    const auto* M=Cast<AM10Mawcrawler>(CharacterOwner);
    if(!M||!M->HasAuthority()||!UpdatedComponent||Dt<=0.f)return;
    float Desired=0.f;
    if(!DesiredHeading(Desired)){TurnRate=0.f;bPivot=false;return;}
    const float Yaw=UpdatedComponent->GetComponentRotation().Yaw;
    const float Delta=FMath::FindDeltaAngleDegrees(Yaw,Desired),Error=FMath::Abs(Delta);
    if(Error>=M->PivotStartAngle)bPivot=true;
    else if(Error<=M->PivotFinishAngle)bPivot=false;
    const bool InPlace=bPivot||Velocity.Size2D()<5.f;
    const float Maximum=InPlace?M->PivotTurnSpeed:M->MovingTurnSpeed;
    // Acceleration and stopping distance prevent abrupt starts, reversals and
    // overshoot. The attack gate additionally waits for this rate to settle.
    const float Wanted=FMath::Sign(Delta)*FMath::Min(Maximum,FMath::Sqrt(2.f*M->TurnAcceleration*Error));
    TurnRate=FMath::FInterpConstantTo(TurnRate,Wanted,Dt,M->TurnAcceleration);
    float Step=TurnRate*Dt;
    if(FMath::Sign(Step)==FMath::Sign(Delta)&&FMath::Abs(Step)>=Error){Step=Delta;TurnRate=0.f;}
    MoveUpdatedComponent(FVector::ZeroVector,FRotator(0,Yaw+Step,0).Quaternion(),true);
}
void UM10MovementComponent::OnTeleported(){TurnRate=0.f;bPivot=false;Super::OnTeleported();}
