#include "FPSCharacterMovementComponent.h"
#include "FPSDodgeRootMotionSource.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "../Combat/CombatStatusFormula.h"

bool UFPSCharacterMovementComponent::StartDodge(const FVector& Direction, float DistanceCM, float DurationSeconds)
{
    if (!CharacterOwner || !UpdatedComponent || GetNetMode()!=NM_Standalone || IsDodging() ||
        (!IsMovingOnGround() && !IsFalling()) || !FMath::IsFinite(DistanceCM) ||
        !FMath::IsFinite(DurationSeconds) || DistanceCM<=0.f || DurationSeconds<=UE_SMALL_NUMBER)
        return false;
    // 旧口径：眩晕/束缚/冻结/石化下禁止闪避（bind 在 dodge 入口直接 return false）。
    if(const auto* Status=CharacterOwner->FindComponentByClass<UCombatStatusFormula>();Status&&Status->BlocksMovement())
        return false;
    const FVector HorizontalDirection=Direction.GetSafeNormal2D();
    if (HorizontalDirection.IsNearlyZero()) return false;
    CancelDodge();
    auto Source=MakeShared<FRootMotionSource_FPSDodge>();
    Source->InstanceName=TEXT("PlayerDodge");
    Source->Priority=1000;
    Source->AccumulateMode=ERootMotionAccumulateMode::Override;
    Source->Duration=DurationSeconds;
    Source->Force=HorizontalDirection*(DistanceCM/DurationSeconds);
    // Preserve gravity. Horizontal finish velocity is cleared after the last sweep.
    Source->FinishVelocityParams.Mode=ERootMotionFinishVelocityMode::MaintainLastRootMotionVelocity;
    DodgeRootMotionId=ApplyRootMotionSource(Source);
    if (!DodgeRootMotionId) return false;
    DodgeDirection=HorizontalDirection;
    ActiveDodgeDuration=DurationSeconds;
    DodgeStartedAt=GetWorld()->GetTimeSeconds();
    CharacterOwner->ConsumeMovementInputVector();
    return true;
}

bool UFPSCharacterMovementComponent::IsDodging() const
{
    return DodgeRootMotionId!=0 && GetWorld() &&
        GetWorld()->GetTimeSeconds()<DodgeStartedAt+ActiveDodgeDuration &&
        (IsMovingOnGround() || IsFalling());
}

float UFPSCharacterMovementComponent::GetDodgeProgress() const
{
    return DodgeRootMotionId && GetWorld()
        ? FMath::Clamp(float((GetWorld()->GetTimeSeconds()-DodgeStartedAt)/ActiveDodgeDuration),0.f,1.f) : 0.f;
}

void UFPSCharacterMovementComponent::UpdateDodgeState()
{
    if (!DodgeRootMotionId) return;
    const auto Source=GetRootMotionSourceByID(DodgeRootMotionId);
    if (!Source || Source->GetTime()>=ActiveDodgeDuration ||
        Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval) || !IsDodging())
        CancelDodge();
}

void UFPSCharacterMovementComponent::CancelDodge()
{
    if (!DodgeRootMotionId) return;
    RemoveRootMotionSourceByID(DodgeRootMotionId);
    DodgeRootMotionId=0;
    Velocity.X=Velocity.Y=0.f;
}

void UFPSCharacterMovementComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    CancelDodge();
    Super::EndPlay(EndPlayReason);
}
