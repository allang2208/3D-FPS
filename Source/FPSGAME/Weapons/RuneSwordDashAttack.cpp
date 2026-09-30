#include "RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "HAL/PlatformTime.h"

namespace
{
float DashReadySeconds(const UColdSteelStatusModel* Profile)
{
    const auto& D=Profile->MasteryDefinition(TEXT("dashAttack"));
    const int32 Level=FMath::Clamp(Profile->MasteryProgress(D.Id).Level,1,D.MaxLevel);
    // 准备条只依赖技能等级；不要每帧评估武器、附魔、配件及属性公式。
    return FMath::Max(.01f,D.DashAttack.ReadySeconds*(1.f-(Level-1)*D.DashAttack.ReadyReductionPerLevel));
}
}

void URuneSwordComponent::TickDashReadiness(float Delta)
{
    const auto* Pawn=Character.Get();
    const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const bool Eligible=Pawn&&IsEquipped()&&!IsBusy()&&!bGuardHeld&&CanUse()&&
        !Pawn->IsCastBlockingLeftHandAction()&&Pawn->bSprintHeld&&
        !Pawn->IsDodging()&&
        Profile&&!Profile->ActiveProductionTool()&&Profile->MasteryProgress(TEXT("dashAttack")).Level>0;
    if(!Eligible){ResetDashReadiness();return;}
    const float ReadySeconds=DashReadySeconds(Profile);
    const auto* Movement=Pawn->GetCharacterMovement();
    const bool bGroundSprint=Pawn->IsSprinting()&&!Pawn->IsSliding()&&Movement->IsMovingOnGround()&&
        Pawn->GetVelocity().SizeSquared2D()>2500.f;
    // Only earned readiness survives locomotion changes. The airborne flag also
    // covers the pending LaunchCharacter frame between slide exit and takeoff.
    const bool bSlideOrJump=Pawn->IsSliding()||Movement->IsFalling()||Pawn->bWeaponJumpAirborne||
        !Movement->PendingLaunchVelocity.IsZero();
    if(DashSprintSeconds>=ReadySeconds&&bSlideOrJump)
    {
        // Once earned, airborne braking or an apex cannot discard the charge.
        // Sprint release and action interruption still reset it normally.
        DashSprintSeconds=ReadySeconds;
        return;
    }
    DashSprintSeconds=bGroundSprint?FMath::Min(DashSprintSeconds+Delta,ReadySeconds):0.f;
}

float URuneSwordComponent::DashReadyFraction() const
{
    const auto* Pawn=Character.Get();
    if(DashSprintSeconds<=0.f||!Pawn||!Pawn->bSprintHeld||IsBusy())return 0.f;
    const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile)return 0.f;
    const float ReadySeconds=DashReadySeconds(Profile);
    const auto* Movement=Pawn->GetCharacterMovement();
    const bool bRetainedReady=DashSprintSeconds>=ReadySeconds&&
        (Pawn->IsSliding()||Movement->IsFalling()||Pawn->bWeaponJumpAirborne||!Movement->PendingLaunchVelocity.IsZero());
    if(!bRetainedReady&&(!Pawn->IsSprinting()||!Movement->IsMovingOnGround()||
        Pawn->GetVelocity().SizeSquared2D()<=2500.f))return 0.f;
    return FMath::Clamp(DashSprintSeconds/ReadySeconds,0.f,1.f);
}

bool URuneSwordComponent::TryBeginDashAttack()
{
    TRACE_CPUPROFILER_EVENT_SCOPE(DashAttack_Entry);
    const double BeginSeconds=FPlatformTime::Seconds();
    auto* Pawn=Character.Get();
    if(bInspecting)CancelAction();
    if(!Pawn||!IsEquipped()||IsBusy()||bGuardHeld||!CanUse()||!Viewmodel||!Viewmodel->GetSkeletalMeshAsset()||
        !Animations.FindRef(TEXT("Overhead"))||!Pawn->bSprintHeld||Pawn->IsCastBlockingLeftHandAction()||
        Pawn->IsDodging())return false;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile||Profile->ActiveProductionTool()||Profile->MasteryProgress(TEXT("dashAttack")).Level<1)return false;
    // Share the displayed readiness contract: a charged slide/jump is a valid
    // release even though locomotion no longer reports grounded sprinting.
    if(DashReadyFraction()<1.f-UE_SMALL_NUMBER)return false;
    auto* Movement=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    // A slide jump may still be queued in LaunchCharacter on this input frame.
    // Capture its actual horizontal launch before the action clears locomotion.
    const bool bPendingJump=Movement && !Movement->PendingLaunchVelocity.IsZero();
    const bool bCarryMomentum=Movement && (Movement->IsFalling() || bPendingJump);
    const FVector CarryVelocity=Movement
        ?(bPendingJump?Movement->PendingLaunchVelocity:Movement->Velocity):FVector::ZeroVector;
    const FDashAttackCast Cast=Profile->DashAttackStats();
    const double StatsSeconds=FPlatformTime::Seconds();
    const bool bFromHighCarry=IsTacticalSprintClip(CurrentClip)&&Animations.FindRef(TEXT("SprintOverhead"));
    // StartSwing 提交一次技能体力，替代本次普通挥击消耗；失败不进入动作。
    if(!StartSwing(TEXT("Overhead"),false,Cast.StaminaCost))return false;
    // Same attack contract and source-time contact window; only its entry pose
    // changes, allowing the held sword to drop directly from the sprint carry.
    if(bFromHighCarry)SetClip(TEXT("SprintOverhead"),false);
    const double SwingSeconds=FPlatformTime::Seconds();
    DashCast=Cast;bDashAttack=bDashTrainingPending=true;bDashCenterCaptured=false;
    DashHits=DashKills=0;DashSprintSeconds=DashTravelCM=DashBounceLeftCM=0.f;
    LungeDirection=Pawn->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
    bLungeStarted=true; // Keep the attack direction throughout the release.
    SwingDamage=Cast.Damage;SwingReach=Cast.RangeCM;SwingKnockbackCM=Cast.KnockbackCM;
    // 冲刺持剑用0.25秒过渡到下劈接触起点；音效、裂隙和判定仍由
    // 同一接触窗触发，前摇期间不命中，接触后的落点与收势保持原时序。
    SwingRate=1.f;
    Elapsed=ContactStart-RuneSwordOverheadRhythm::DashWindupSeconds;
    SamplePose(Elapsed);
    if(Pawn->IsSliding())Pawn->StopSlide(true);
    Pawn->StopMovementForMeleeSkill();
    if(bCarryMomentum && Movement->BeginMeleeDashMomentum(CarryVelocity))
    {
        // The inherited speed owns this cast's displacement, including after
        // contact. Suppress the separate, fixed-distance windup lunge entirely.
        bLungeBlocked=true;
    }
    else
    {
        // Grounded releases keep their original one-metre step. A queued jump
        // still retains its vertical launch even when it has no horizontal speed.
        Pawn->GetCharacterMovement()->PendingLaunchVelocity.X=0.;
        Pawn->GetCharacterMovement()->PendingLaunchVelocity.Y=0.;
    }
    const double EndSeconds=FPlatformTime::Seconds();
    if(EndSeconds-BeginSeconds>.004)
        UE_LOG(LogTemp,Display,TEXT("[DashAttackPerf] entry_ms=%.3f stats_ms=%.3f swing_ms=%.3f stop_ms=%.3f"),
            (EndSeconds-BeginSeconds)*1000.,(StatsSeconds-BeginSeconds)*1000.,(SwingSeconds-StatsSeconds)*1000.,(EndSeconds-SwingSeconds)*1000.);
    return true;
}

void URuneSwordComponent::DashAttackContractHit()
{
    TRACE_CPUPROFILER_EVENT_SCOPE(DashAttack_Contact);
    const double BeginSeconds=FPlatformTime::Seconds();
    auto* Pawn=Character.Get();
    // The original contact window and per-target deduplication remain intact.
    // Carry the sector with the moving player so an airborne release cannot
    // leave its damage volume behind at the start of the swing.
    DashCenter=Pawn->GetActorLocation();bDashCenterCaptured=true;
    const auto Hits=RuneSwordCombat::QuerySector(GetWorld(),Pawn,DashCenter,LungeDirection,
        DashCast.RangeCM,DashCast.ArcDegrees,HitActors);
    const double QuerySeconds=FPlatformTime::Seconds();
    ApplySwingHits(Hits,LungeDirection);
    const double EndSeconds=FPlatformTime::Seconds();
    if(EndSeconds-BeginSeconds>.004)
        UE_LOG(LogTemp,Display,TEXT("[DashAttackPerf] targets=%d query_ms=%.3f damage_ms=%.3f contact_ms=%.3f"),
            Hits.Num(),(QuerySeconds-BeginSeconds)*1000.,(EndSeconds-QuerySeconds)*1000.,(EndSeconds-BeginSeconds)*1000.);
}

void URuneSwordComponent::FinishDashAttack()
{
    // 清标记后提交修炼；档案广播可能再次进入装备刷新／取消。
    bDashAttack=false;DashSprintSeconds=DashBounceLeftCM=0.f;
    if(!bDashTrainingPending)return;
    bDashTrainingPending=false;
    if(auto* Profile=GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
        Profile->TrainDashAttack(DashHits,DashKills);
}
