#include "M66MovementComponent.h"
#include "M66IncineratorMonster.h"
#include "MonsterAIController.h"
bool UM66MovementComponent::DesiredHeading(float& Yaw) const
{
    if(!CharacterOwner||!IsMovingOnGround())return false;
    if(const auto* M66=Cast<AM66IncineratorMonster>(CharacterOwner);M66&&M66->Busy())return M66->DesiredBreathFacing(Yaw);
    const auto* AI=Cast<AMonsterAIController>(CharacterOwner->GetController());
    if(!AI||!AI->bDecisionEnabled)return false;
    const FVector Direction=bHasRequestedVelocity?RequestedVelocity:Acceleration;
    if(Direction.IsNearlyZero())
    {
        const auto* M66=Cast<AM66IncineratorMonster>(CharacterOwner);
        return M66&&M66->DesiredCombatFacing(Yaw);
    }
    Yaw=Direction.Rotation().Yaw;return true;
}
float UM66MovementComponent::GetMaxSpeed() const
{
    if(const auto* M66=Cast<AM66IncineratorMonster>(CharacterOwner);M66&&M66->Busy()&&IsMovingOnGround())return 0.f;
    const float Base=Super::GetMaxSpeed();float Desired;
    if(!DesiredHeading(Desired))return Base;
    const float Error=FMath::Abs(FMath::FindDeltaAngleDegrees(CharacterOwner->GetActorRotation().Yaw,Desired));
    if(bPivot||Error>=65.f)return 0.f;
    return Base*FMath::GetMappedRangeValueClamped(FVector2D(12.f,65.f),FVector2D(1.f,.15f),Error);
}
void UM66MovementComponent::PhysicsRotation(float Dt)
{
    const auto* M66=Cast<AM66IncineratorMonster>(CharacterOwner);
    if(!M66||!M66->HasAuthority()||!UpdatedComponent||Dt<=0)return;
    float Desired;if(!DesiredHeading(Desired)){TurnVelocity=0;bPivot=false;return;}
    const float Yaw=UpdatedComponent->GetComponentRotation().Yaw;
    const float Error=FMath::FindDeltaAngleDegrees(Yaw,Desired);
    if(FMath::Abs(Error)>=65.f)bPivot=true;else if(FMath::Abs(Error)<=12.f)bPivot=false;
    constexpr float TurnAcceleration=360.f;
    const float Wanted=FMath::Sign(Error)*FMath::Min(M66->IsBreathing()?28.f:M66->TurnSpeed,FMath::Sqrt(2.f*TurnAcceleration*FMath::Abs(Error)));
    TurnVelocity=FMath::FInterpConstantTo(TurnVelocity,Wanted,Dt,TurnAcceleration);
    if(M66->IsBreathing())TurnVelocity=FMath::Clamp(TurnVelocity,-28.f,28.f);
    float Step=TurnVelocity*Dt;
    if(FMath::Sign(Step)==FMath::Sign(Error)&&FMath::Abs(Step)>=FMath::Abs(Error)){Step=Error;TurnVelocity=0;}
    MoveUpdatedComponent(FVector::ZeroVector,FRotator(0,Yaw+Step,0).Quaternion(),true);
}
void UM66MovementComponent::OnTeleported(){TurnVelocity=0;bPivot=false;Super::OnTeleported();}
