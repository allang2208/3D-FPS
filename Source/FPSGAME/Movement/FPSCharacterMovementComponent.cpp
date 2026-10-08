#include "FPSCharacterMovementComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/WeaponBipodDeploymentComponent.h"
#include "Components/SceneComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/Controller.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

FSavedMove_FPSCharacter::FSavedMove_FPSCharacter()
{
    bSavedWantsToSprint = false;
    bSavedWantsToAim = false;
    bSavedWantsToSlide = false;
    bSavedWantsToMount = false;
}

void FSavedMove_FPSCharacter::Clear()
{
    Super::Clear();
    bSavedWantsToSprint = false;
    bSavedWantsToAim = false;
    bSavedWantsToSlide = false;
    bSavedWantsToMount = false;
}

uint8 FSavedMove_FPSCharacter::GetCompressedFlags() const
{
    uint8 Result = Super::GetCompressedFlags();
    if (bSavedWantsToSprint) Result |= FLAG_Custom_0;
    if (bSavedWantsToAim) Result |= FLAG_Custom_1;
    if (bSavedWantsToSlide) Result |= FLAG_Custom_2;
    if (bSavedWantsToMount) Result |= FLAG_Custom_3;
    return Result;
}

void FSavedMove_FPSCharacter::SetMoveFor(ACharacter* InCharacter, float InDeltaTime, FVector const& NewAccel, FNetworkPredictionData_Client_Character& ClientData)
{
    Super::SetMoveFor(InCharacter, InDeltaTime, NewAccel, ClientData);
    if (const UFPSCharacterMovementComponent* Move = Cast<UFPSCharacterMovementComponent>(InCharacter ? InCharacter->GetCharacterMovement() : nullptr))
    {
        bSavedWantsToSprint = Move->bWantsToSprint;
        bSavedWantsToAim = Move->bWantsToAim;
        bSavedWantsToSlide = Move->bWantsToSlide;
        bSavedWantsToMount = Move->bWantsToMount;
    }
}

void FSavedMove_FPSCharacter::PrepMoveFor(ACharacter* InCharacter)
{
    Super::PrepMoveFor(InCharacter);
    // 纠偏回放时把意图位一起还原，回放帧的速度档与原始帧一致。
    if (UFPSCharacterMovementComponent* Move = Cast<UFPSCharacterMovementComponent>(InCharacter ? InCharacter->GetCharacterMovement() : nullptr))
    {
        Move->bWantsToSprint = bSavedWantsToSprint;
        Move->bWantsToAim = bSavedWantsToAim;
        Move->bWantsToSlide = bSavedWantsToSlide;
        Move->bWantsToMount = bSavedWantsToMount;
        // 滑铲态在回放里只还原状态位与摩擦（该帧速度由 move 重算，不能再注入入铲初速）。
        if (auto* Player = Cast<AFPSGAMECharacter>(InCharacter))
        {
            Player->ApplyNetSlideFlag(bSavedWantsToSlide, false);
        }
    }
}

bool FSavedMove_FPSCharacter::CanCombineWith(const FSavedMovePtr& NewMove, ACharacter* InCharacter, float MaxDelta) const
{
    // 意图位不同的 move 不能合并，否则服务端会以错误的冲刺/瞄准/滑铲档执行这段合并 move。
    if (const FSavedMove_FPSCharacter* NewFPSMove = static_cast<const FSavedMove_FPSCharacter*>(NewMove.Get()))
    {
        if (bSavedWantsToSprint != NewFPSMove->bSavedWantsToSprint || bSavedWantsToAim != NewFPSMove->bSavedWantsToAim
            || bSavedWantsToSlide != NewFPSMove->bSavedWantsToSlide || bSavedWantsToMount != NewFPSMove->bSavedWantsToMount)
        {
            return false;
        }
    }
    return Super::CanCombineWith(NewMove, InCharacter, MaxDelta);
}

FNetworkPredictionData_Client_FPSCharacter::FNetworkPredictionData_Client_FPSCharacter(const UCharacterMovementComponent& ClientMovement)
    : Super(ClientMovement)
{
}

FSavedMovePtr FNetworkPredictionData_Client_FPSCharacter::AllocateNewMove()
{
    return FSavedMovePtr(new FSavedMove_FPSCharacter());
}

void UFPSCharacterMovementComponent::UpdateFromCompressedFlags(uint8 Flags)
{
    Super::UpdateFromCompressedFlags(Flags);
    // 服务端侧：随本帧 move 到达的意图位，服务端模拟远端玩家的速度档依据。
    const uint8 NewSprint = (Flags & FSavedMove_Character::FLAG_Custom_0) != 0;
    const uint8 NewAim = (Flags & FSavedMove_Character::FLAG_Custom_1) != 0;
    if (CharacterOwner && CharacterOwner->HasAuthority() && (NewSprint != bWantsToSprint))
    {
        UE_LOG(LogTemp, Warning, TEXT("MPTEST sprint move-flag server: %s b=%d"), *GetNameSafe(CharacterOwner), NewSprint ? 1 : 0);
    }
    bWantsToSprint = NewSprint;
    bWantsToAim = NewAim;
    bWantsToMount = (Flags & FSavedMove_Character::FLAG_Custom_3) != 0;
    if (CharacterOwner && CharacterOwner->HasAuthority())
        LastServerMoveAppliedAt = GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
    // 滑铲态随移动包到达：权威端在同一帧启停完整滑铲物理（入铲初速客户端已在本帧施加）。
    const bool bNewSlide = (Flags & FSavedMove_Character::FLAG_Custom_2) != 0;
    if (bNewSlide != bWantsToSlide)
    {
        bWantsToSlide = bNewSlide;
        if (auto* Player = Cast<AFPSGAMECharacter>(CharacterOwner))
        {
            Player->ApplyNetSlideFlag(bNewSlide, CharacterOwner->HasAuthority());
        }
    }
    // 速度档在同一帧移动包内生效，不等角色 Tick——消除两端一档之差的 rubber-band 窗口。
    if (auto* Player = Cast<AFPSGAMECharacter>(CharacterOwner))
    {
        MaxWalkSpeed = bWantsToSprint ? Player->SprintSpeed : (bWantsToAim ? Player->ADSWalkSpeed : Player->WalkSpeed);
    }
}

FNetworkPredictionData_Client* UFPSCharacterMovementComponent::GetPredictionData_Client() const
{
    if (ClientPredictionData == nullptr)
    {
        UFPSCharacterMovementComponent* MutableThis = const_cast<UFPSCharacterMovementComponent*>(this);
        MutableThis->ClientPredictionData = new FNetworkPredictionData_Client_FPSCharacter(*MutableThis);
    }
    return ClientPredictionData;
}

bool UFPSCharacterMovementComponent::DoJump(bool bReplayingMoves, float DeltaTime)
{
    if(UBoundCongregateCaptureComponent::IsCaptured(CharacterOwner))return false;
    if(IsBipodMovementLocked())return false;
    if (const auto* Player = Cast<AFPSGAMECharacter>(CharacterOwner); Player && Player->IsMeleeSkillMovementLocked()) return false;
    if (IsDodging()) return false;
    const bool Result=Super::DoJump(bReplayingMoves,DeltaTime);
    if(Result) bLeavingStairJump=bLastFrameSteppedUp;
    if(FParse::Param(FCommandLine::Get(),TEXT("StairMovementAudit")))
        UE_LOG(LogTemp,Display,TEXT("STAIR_JUMP accepted=%d z=%.3f vz=%.3f offset=%.3f"),Result,UpdatedComponent->GetComponentLocation().Z,Velocity.Z,StairVisualOffset);
    return Result;
}

bool UFPSCharacterMovementComponent::IsValidLandingSpot(const FVector& CapsuleLocation,const FHitResult& Hit) const
{
    // At high tick rates the rounded foot can touch the same step immediately
    // after jumping. That contact must not consume an upward jump as a landing.
    // Collision deflection still runs; ordinary descending landings are unchanged.
    if(bLeavingStairJump && FVector::DotProduct(Velocity,-GetGravityDirection())>0.f) return false;
    return Super::IsValidLandingSpot(CapsuleLocation,Hit);
}

UFPSCharacterMovementComponent::UFPSCharacterMovementComponent()
{
    MaxStepHeight = 40.f;
    bWantsToSprint = false;
    bWantsToAim = false;
    bWantsToSlide = false;
    bWantsToMount = false;
}

bool UFPSCharacterMovementComponent::IsBipodMovementLocked() const
{
    const auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner);
    return bWantsToMount||(Player&&Player->HasAuthority()&&Player->BipodDeployment&&Player->BipodDeployment->BlocksMovement());
}

float UFPSCharacterMovementComponent::GetMaxSpeed() const
{
    if(UBoundCongregateCaptureComponent::IsCaptured(CharacterOwner))return 0.f;
    if(IsBipodMovementLocked())return 0.f;
    if (const auto* Player = Cast<AFPSGAMECharacter>(CharacterOwner); Player && Player->IsMeleeSkillMovementLocked()) return 0.f;
    const auto* Status=GetOwner()?GetOwner()->FindComponentByClass<UCombatStatusFormula>():nullptr;
    return Super::GetMaxSpeed()*(Status?Status->MovementMultiplier():1.f);
}

bool UFPSCharacterMovementComponent::StepUp(const FVector& GravDir, const FVector& Delta,
    const FHitResult& Hit, FStepDownResult* OutStepDownResult)
{
    const FVector Before = UpdatedComponent->GetComponentLocation();
    // Keep the engine's capsule sweeps, headroom, walkable floor, perching and rollback rules.
    const bool bStepped = Super::StepUp(GravDir, Delta, Hit, OutStepDownResult);
    if (bCaptureStairs && bStepped)
        FrameStairDisplacement += float(UpdatedComponent->GetComponentLocation().Z - Before.Z);
    return bStepped;
}

void UFPSCharacterMovementComponent::AdjustFloorHeight()
{
    const double BeforeZ = UpdatedComponent->GetComponentLocation().Z;
    Super::AdjustFloorHeight();
    if (bCaptureStairs)
        FrameStairDisplacement += float(UpdatedComponent->GetComponentLocation().Z - BeforeZ);
}

void UFPSCharacterMovementComponent::TickComponent(float DeltaTime, ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    if (DodgeRootMotionId && (MovementMode==MOVE_None ||
        (CharacterOwner && CharacterOwner->Controller && CharacterOwner->Controller->IsMoveInputIgnored())))
        CancelDodge();
    // 服务端断流看门狗：远端客户端停发 move（窗口失焦/丢包/进程卡死）后，最后一个 move
    // 的加速度与意图位会被 SimulatedTick 永续沿用——pawn 沿旧方向一直冲刺，观察者看到
    // "径直冲刺不停"。move 正常发送间隔 ≤0.2s；超过阈值即回退到空输入态，摩擦自然刹停，
    // move 流恢复时下一帧自动复原。
    if (CharacterOwner && CharacterOwner->HasAuthority() && !CharacterOwner->IsLocallyControlled()
        && LastServerMoveAppliedAt > 0.0 && GetWorld())
    {
        const double SinceMove = GetWorld()->GetRealTimeSeconds() - LastServerMoveAppliedAt;
        if (SinceMove > 0.4)
        {
            if (!Acceleration.IsNearlyZero() || bWantsToSprint || bWantsToAim || bWantsToSlide)
            {
                UE_LOG(LogTemp, Warning, TEXT("MPTEST stale-move watchdog: %s no move %.2fs, clearing accel+intent"),
                    *GetNameSafe(CharacterOwner), SinceMove);
            }
            Acceleration = FVector::ZeroVector;
            bWantsToSprint = false;
            bWantsToAim = false;
            bWantsToMount = false;
            if (bWantsToSlide)
            {
                bWantsToSlide = false;
                if (auto* Player = Cast<AFPSGAMECharacter>(CharacterOwner))
                    Player->ApplyNetSlideFlag(false, true); // 恢复摩擦/减速，让衰减真正生效
            }
            if (auto* Player = Cast<AFPSGAMECharacter>(CharacterOwner))
                MaxWalkSpeed = Player->WalkSpeed;
        }
    }
    if(CharacterOwner&&CharacterOwner->IsLocallyControlled())
        if(const auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner))
            bWantsToMount=Player->BipodDeployment&&Player->BipodDeployment->BlocksMovement();
    FrameStairDisplacement = 0.f;
    bCaptureStairs = IsMovingOnGround();
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    UpdateDodgeState();
    bCaptureStairs = false;
    bLastFrameSteppedUp = IsMovingOnGround() && FrameStairDisplacement > .1f;
    if (IsMovingOnGround()) bLeavingStairJump = false;
    if (!StairVisualRoot || !CharacterOwner || !CharacterOwner->IsLocallyControlled()) return;

    // Only accepted step/floor corrections contribute: slope travel, moving bases,
    // crouch capsule resizing, jumping and landing retain their native trajectory.
    if (IsMovingOnGround()) StairVisualOffset -= FrameStairDisplacement;
    const float Speed = FMath::Max(StairVisualSpeed, float(Velocity.Size2D()) * StairSpeedToWalkSpeed);
    StairVisualOffset = FMath::FInterpConstantTo(StairVisualOffset, 0.f, DeltaTime, Speed);
    StairVisualRoot->SetRelativeLocation(FVector(0, 0, StairVisualOffset));
}

void UFPSCharacterMovementComponent::OnTeleported()
{
    bMeleeDashMomentum=false;
    CancelDodge();
    Super::OnTeleported();
    FrameStairDisplacement = StairVisualOffset = 0.f;
    bLastFrameSteppedUp = bLeavingStairJump = false;
    if (StairVisualRoot) StairVisualRoot->SetRelativeLocation(FVector::ZeroVector);
}
