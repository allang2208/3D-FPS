#include "FPSCharacterMovementComponent.h"
#include "FPSDodgeRootMotionSource.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "../Combat/CombatStatusFormula.h"

bool UFPSCharacterMovementComponent::StartDodge(const FVector& Direction, float DistanceCM, float DurationSeconds)
{
    // 联机：闪避发起端是本地预测的自主代理（或 listen 主机 pawn）；远端副本不调用本函数——
    // 闪避位移以 RootMotionSource 存进 SavedMove，服务端经 SavedRootMotion 自动回放。
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
    if (DodgeRootMotionId!=0 && GetWorld() &&
        GetWorld()->GetTimeSeconds()<DodgeStartedAt+ActiveDodgeDuration &&
        (IsMovingOnGround() || IsFalling()))
        return true;
    // 联机：远端玩家的闪避经 SavedMove 的 SavedRootMotion 抵达服务端/其他副本，
    // 没有本地 DodgeRootMotionId——按激活源名判定（服务端无敌帧/动作门禁用依赖它）。
    if (GetNetMode()==NM_Client)
    {
        const auto HasLiveDodge=[](const FRootMotionSourceGroup& Group)
        {
            for (const auto& Source : Group.RootMotionSources)
                if (Source.IsValid() && Source->InstanceName==FName(TEXT("PlayerDodge"))
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
    if (DodgeRootMotionId && GetWorld())
        return FMath::Clamp(float((GetWorld()->GetTimeSeconds()-DodgeStartedAt)/ActiveDodgeDuration),0.f,1.f);
    // 联机：远端副本没有本地 DodgeRootMotionId——闪避源经 SavedMove 到达，
    // 按激活 RootMotionSource 的时长取进度，远端动画加权才不再恒 0。
    if (GetNetMode() == NM_Client)
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
