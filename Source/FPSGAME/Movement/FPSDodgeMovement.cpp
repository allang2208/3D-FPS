#include "FPSCharacterMovementComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "FPSDodgeRootMotionSource.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "../Combat/CombatStatusFormula.h"

bool UFPSCharacterMovementComponent::StartDodge(const FVector& Direction, float DistanceCM, float DurationSeconds)
{
    if(UBoundCongregateCaptureComponent::IsCaptured(CharacterOwner))return false;
    // Both the predicted owner and authority create this source. SavedMove stores
    // local replay state; FPSDodgeNetwork explicitly transmits the start intent.
    if (!CharacterOwner || !UpdatedComponent || IsDodging() ||
        !(CharacterOwner->IsLocallyControlled() || CharacterOwner->HasAuthority()) ||
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
    if(DodgeRootMotionId&&(IsMovingOnGround()||IsFalling()))
        // UE's lookup is non-const but only reads active/pending root-motion sources.
        if(const auto Source=const_cast<UFPSCharacterMovementComponent*>(this)->GetRootMotionSourceByID(DodgeRootMotionId);Source&&Source->GetTime()<Source->Duration
            &&!Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval))return true;
    // Simulated clients receive the server's root-motion group. Authority uses
    // the source started from the owner's timestamped movement request above.
    if (CharacterOwner&&CharacterOwner->GetLocalRole()==ROLE_SimulatedProxy)
    {
        const auto HasLiveDodge=[](const FRootMotionSourceGroup& Group)
        {
            for (const auto& Source : Group.RootMotionSources)
                if (Source.IsValid() && Source->InstanceName==FName(TEXT("PlayerDodge"))
                    && Source->GetTime()<Source->Duration
                    && !Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval))
                    return true;
            return false;
        };
        if (HasLiveDodge(CurrentRootMotion)
            || (CharacterOwner && HasLiveDodge(CharacterOwner->SavedRootMotion)))
            return true;
    }
    return false;
}

float UFPSCharacterMovementComponent::GetDodgeProgress() const
{
    if(DodgeRootMotionId)
        if(const auto Source=const_cast<UFPSCharacterMovementComponent*>(this)->GetRootMotionSourceByID(DodgeRootMotionId))
            return FMath::Clamp(Source->GetTime()/FMath::Max(SMALL_NUMBER,Source->Duration),0.f,1.f);
    // Other clients derive presentation from the replicated authority source.
    if (CharacterOwner&&CharacterOwner->GetLocalRole()==ROLE_SimulatedProxy)
    {
        const auto Probe = [](const FRootMotionSourceGroup& Group, float& Out)
        {
            for (const auto& Source : Group.RootMotionSources)
                if (Source.IsValid() && Source->InstanceName == FName(TEXT("PlayerDodge"))
                    && !Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval)
                    && Source->Duration > UE_SMALL_NUMBER)
                { Out = FMath::Clamp(Source->GetTime() / Source->Duration, 0.f, 1.f); return true; }
            return false;
        };
        float P = 0.f;
        if (Probe(CurrentRootMotion, P) || (CharacterOwner && Probe(CharacterOwner->SavedRootMotion, P)))
            return P;
    }
    return 0.f;
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
