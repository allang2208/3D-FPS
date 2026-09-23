#include "Mutant3.h"
#include "FatZombieAnimInstance.h"
#include "FPSCombatHealthComponent.h"
#include "MonsterCombatTuning.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "Mutant3PounceCameraShake.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

bool AMutant3::HasFeralSight(const APawn* Victim) const
{
    return HasFeralSightFrom(Victim, GetActorLocation());
}

bool AMutant3::HasFeralSightFrom(const APawn* Victim, const FVector& From) const
{
    if (!IsValid(Victim)) return false;
    if (const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>())
        if (Vitals->IsDead()) return false;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(Mutant3Sight), false, this);
    Params.AddIgnoredActor(Victim);
    return !GetWorld()->LineTraceSingleByChannel(Hit, From+FVector(0,0,25),
        Victim->GetActorLocation(), ECC_Visibility, Params);
}

float AMutant3::GetClawStartDistance() const
{
    return FMath::Max(40.f, MonsterCombatTuning::AttackDistance(AttackRange)-15.f);
}

bool AMutant3::CanClawFrom(const APawn* Victim, const FVector& From, float Range) const
{
    if (!IsValid(Victim)) return false;
    const FVector Offset = Victim->GetActorLocation()-From;
    return Offset.Size2D() <= Range && FMath::Abs(Offset.Z) <= 110.f && HasFeralSightFrom(Victim, From);
}

bool AMutant3::CanStartFeralAttack(APawn* Victim) const
{
    if (!HasAuthority() || !IsValid(Victim) || !GetWorld() || Health <= 0.f ||
        State == ENurseState::Dead || State == ENurseState::Stagger || State == ENurseState::Attack ||
        FeralPhase != EMutant3FeralPhase::None || GetWorld()->GetTimeSeconds() < NextFeralAttackAt ||
        !GetCharacterMovement()->IsMovingOnGround() || !HasFeralSight(Victim)) return false;
    if (CanClawFrom(Victim, GetActorLocation(), GetClawStartDistance()))
        return !ClawClips.IsEmpty() && ClawClips[NextClawIndex % ClawClips.Num()] != nullptr;
    if (GetWorld()->GetTimeSeconds() < NextPounceAt || !PounceWindupClip || !PounceFlightClip || !PounceLandClip)
        return false;
    FVector LaunchVelocity;
    return BuildPounceVelocity(Victim, LaunchVelocity);
}

bool AMutant3::BuildPounceVelocity(APawn* Victim, FVector& Velocity) const
{
    if (!IsValid(Victim)) return false;
    Velocity = FVector::ZeroVector;
    const FVector Start = GetActorLocation();
    const FVector TargetPosition = Victim->GetActorLocation();
    const FVector Offset = TargetPosition-Start;
    if (Offset.Size2D() < PounceMinRange || Offset.Size2D() > PounceMaxRange || FMath::Abs(Offset.Z) > 150.f)
        return false;
    const auto* Capsule = GetCapsuleComponent();
    const auto* Move = GetCharacterMovement();
    const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
    const float Duration = FMath::Max(.2f, PounceFlightSeconds);
    const float Gravity = Move->GetGravityZ();
    // This is evaluated at selection and again at the end of windup. Only the
    // remaining flight time belongs in the prediction at the actual takeoff.
    const FVector TargetVelocity = Victim->GetVelocity();
    FVector Lead = FVector(TargetVelocity.X, TargetVelocity.Y, 0.f)*Duration*
        FMath::Clamp(PounceLeadStrength, 0.f, 1.5f);
    Lead = Lead.GetClampedToMaxSize(FMath::Max(0.f, PounceMaxLeadDistance));
    FCollisionQueryParams Params(SCENE_QUERY_STAT(Mutant3Pounce), false, this);
    Params.AddIgnoredActor(Victim);
    // Do not extrapolate the player through a wall they would collide with.
    if (const auto* TargetCharacter = Cast<ACharacter>(Victim); TargetCharacter && !Lead.IsNearlyZero(1.f))
    {
        const auto* TargetCapsule = TargetCharacter->GetCapsuleComponent();
        FHitResult Obstacle;
        const FCollisionShape TargetShape = FCollisionShape::MakeCapsule(TargetCapsule->GetScaledCapsuleRadius(),
            FMath::Max(TargetCapsule->GetScaledCapsuleRadius(), TargetCapsule->GetScaledCapsuleHalfHeight()-2.f));
        if (GetWorld()->SweepSingleByChannel(Obstacle, TargetPosition, TargetPosition+Lead, FQuat::Identity,
            TargetCapsule->GetCollisionObjectType(), TargetShape, Params,
            FCollisionResponseParams(TargetCapsule->GetCollisionResponseToChannels())))
            Lead *= FMath::Max(0.f, Obstacle.Time-.02f);
    }
    const FCollisionShape Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), HalfHeight-1.f);
    const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
    const int32 Candidates = Lead.IsNearlyZero(1.f) ? 1 : 3;
    for (int32 Candidate=0; Candidate<Candidates; ++Candidate)
    {
        // Prefer full lead, then half, then the current position when terrain
        // makes the forecast unusable. Limit work to these three candidates.
        const FVector Aim = TargetPosition+Lead*(1.f-.5f*Candidate);
        FVector Planar = Aim-Start;
        Planar.Z = 0.f;
        FVector Landing = Aim-Planar.GetSafeNormal()*90.f;
        FVector Travel = Landing-Start;
        Travel.Z = 0.f;
        Travel = Travel.GetClampedToMaxSize(FMath::Max(1.f, PounceMaxRange));
        Landing.X = Start.X+Travel.X;
        Landing.Y = Start.Y+Travel.Y;
        FHitResult Floor;
        if (!GetWorld()->LineTraceSingleByChannel(Floor, Landing+FVector(0,0,120),
            Landing-FVector(0,0,350), ECC_Visibility, Params) || !Move->IsWalkable(Floor)) continue;
        Landing = Floor.ImpactPoint+FVector(0,0,HalfHeight+2.f);
        if (FMath::Abs(Landing.Z-Start.Z) > 150.f) continue;
        const FVector CandidateVelocity = (Landing-Start)/Duration-FVector(0,0,.5f*Gravity*Duration);
        FVector Previous = Start;
        bool bClear = true;
        for (int32 Step=1; Step<=16; ++Step)
        {
            const float T = Duration*Step/16.f;
            const FVector Next = Start+CandidateVelocity*T+FVector(0,0,.5f*Gravity*T*T);
            FHitResult Hit;
            if (GetWorld()->SweepSingleByChannel(Hit, Previous, Next, FQuat::Identity,
                Capsule->GetCollisionObjectType(), Shape, Params, Response))
            {
                bClear = false;
                break;
            }
            Previous = Next;
        }
        if (!bClear) continue;
        Velocity = CandidateVelocity;
        return true;
    }
    return false;
}

bool AMutant3::StartFeralAttack(APawn* Victim)
{
    if (!CanStartFeralAttack(Victim)) return false;
    if (auto* AI = Cast<AAIController>(GetController())) AI->StopMovement();
    auto* Move = GetCharacterMovement();
    Move->StopMovementImmediately();
    bSavedOrientToMovement = Move->bOrientRotationToMovement;
    SavedAirControl = Move->AirControl;
    bFeralMovementSaved = true;
    Move->bOrientRotationToMovement = false;
    Move->AirControl = 0.f;
    FeralTarget = Victim;
    ClawsPerformed = 0;
    State = ENurseState::Attack;
    if (!CanClawFrom(Victim, GetActorLocation(), GetClawStartDistance()))
    {
        NextPounceAt = GetWorld()->GetTimeSeconds()+FMath::Max(0.f, PounceCooldownSeconds);
        BeginFeralPhase(EMutant3FeralPhase::Windup, PounceWindupClip, .16f);
    }
    else BeginClaw();
    return true;
}

void AMutant3::BeginFeralPhase(EMutant3FeralPhase Phase, UAnimSequence* Clip, float BlendSeconds)
{
    FeralPhase = Phase;
    FeralTime = 0.f;
    bFeralHitConsumed = false;
    // The common parry presentation needs the currently attacking clip to rewind it.
    AttackClip = Clip;
    if (auto* Animation = GetBlendedAnimation())
    {
        FMonsterClipTransition Settings;
        Settings.bGroundLowerBody = Phase == EMutant3FeralPhase::Landing;
        Animation->TransitionTo(Clip, false, true, BlendSeconds, Settings);
    }
}

void AMutant3::BeginClaw()
{
    if (ClawClips.IsEmpty() || !ClawClips[NextClawIndex % ClawClips.Num()])
    {
        BeginFeralRecovery(ClawRecoverySeconds);
        return;
    }
    UAnimSequence* Clip = ClawClips[NextClawIndex % ClawClips.Num()];
    NextClawIndex = (NextClawIndex+1) % ClawClips.Num();
    ++ClawsPerformed;
    // Finish blending before the authoritative .13 s contact window opens.
    BeginFeralPhase(EMutant3FeralPhase::Claw, Clip, FMath::Min(.11f, FMath::Max(0.f, ContactTime-.02f)));
}

void AMutant3::TryClawContact()
{
    APawn* Victim = FeralTarget.Get();
    if (bFeralHitConsumed || !Victim) return;
    const FVector Offset = Victim->GetActorLocation()-GetActorLocation();
    // 130 degree frontal sector; range, vertical reach and obstruction match
    // pursuit/selection, with 15 cm of contact slack after the windup.
    if (!CanClawFrom(Victim, GetActorLocation(), MonsterCombatTuning::AttackDistance(AttackRange)) ||
        (!Offset.IsNearlyZero(1.f) && FVector::DotProduct(GetActorForwardVector(), Offset.GetSafeNormal2D()) < .42261826f)) return;
    bFeralHitConsumed = true;
    UGameplayStatics::ApplyDamage(Victim, AttackDamage*ClawDamageScale, GetController(), this, UEnemyMeleeDamage::StaticClass());
    ++SuccessfulHits;
}

void AMutant3::TryPounceImpact(const FVector& LandingPoint)
{
    if (bFeralHitConsumed) return;
    // Landed owns the only pounce hit. Consume before damage callbacks, which
    // can interrupt this action through the player's parry response.
    bFeralHitConsumed = true;
    const float Radius = FMath::Max(1.f, PounceImpactRadius);
    constexpr float VerticalReach = 150.f;
    const float HalfAngle = FMath::Clamp(PounceImpactAngle, 1.f, 180.f)*.5f;
    const float CosHalfAngle = FMath::Cos(FMath::DegreesToRadians(HalfAngle));
    const FVector Forward = GetActorForwardVector().GetSafeNormal2D();
    const FVector LeftEdge = Forward.RotateAngleAxis(-HalfAngle, FVector::UpVector)*Radius;
    const FVector RightEdge = Forward.RotateAngleAxis(HalfAngle, FVector::UpVector)*Radius;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(Mutant3PounceImpact), false, this);
    TArray<FOverlapResult> Hits;
    GetWorld()->OverlapMultiByObjectType(Hits, LandingPoint, FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn),
        FCollisionShape::MakeBox(FVector(Radius, Radius, VerticalReach)), Params);
    TSet<APawn*> Contacted;
    for (const FOverlapResult& Hit : Hits)
    {
        APawn* Victim = Cast<APawn>(Hit.GetActor());
        if (!IsValid(Victim) || !Victim->IsPlayerControlled() || Contacted.Contains(Victim)) continue;
        Contacted.Add(Victim);
        float VictimRadius, VictimHalfHeight;
        Victim->GetSimpleCollisionCylinder(VictimRadius, VictimHalfHeight);
        const FVector Offset = Victim->GetActorLocation()-LandingPoint;
        if (FMath::Abs(Offset.Z-VictimHalfHeight) > VerticalReach) continue;
        const FVector Planar(Offset.X, Offset.Y, 0.f);
        const float Distance = Planar.Size();
        if (Distance > Radius+VictimRadius) continue;
        // Count a capsule touching either edge of the bounded sector, rather
        // than requiring its center inside the cone. The rear remains avoidable.
        const bool CenterInSector = Distance <= UE_KINDA_SMALL_NUMBER ||
            FVector::DotProduct(Forward, Planar/Distance) >= CosHalfAngle;
        if (!CenterInSector &&
            FMath::PointDistToSegmentSquared(Planar, FVector::ZeroVector, LeftEdge) > FMath::Square(VictimRadius) &&
            FMath::PointDistToSegmentSquared(Planar, FVector::ZeroVector, RightEdge) > FMath::Square(VictimRadius)) continue;
        if (!HasFeralSight(Victim)) continue;
        const float Applied = UGameplayStatics::ApplyDamage(Victim, AttackDamage*PounceDamageScale,
            GetController(), this, UEnemyMeleeDamage::StaticClass());
        if (Applied > 0.f)
        {
            ++SuccessfulHits;
            const auto* Vitals = IsValid(Victim) ? Victim->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
            if (IsValid(Victim) && (!Vitals || !Vitals->IsDead()))
            {
                auto* Stun = Victim->FindComponentByClass<UPlayerGuardBreakComponent>();
                if (!Stun)
                {
                    Stun = NewObject<UPlayerGuardBreakComponent>(Victim);
                    Victim->AddInstanceComponent(Stun);
                    Stun->RegisterComponent();
                }
                Stun->Apply(PounceStunSeconds);
                if (auto* PC=Cast<APlayerController>(Victim->GetController()); PC && PC->IsLocalController() && PC->PlayerCameraManager)
                    PC->PlayerCameraManager->StartCameraShake(UMutant3PounceCameraShake::StaticClass());
            }
        }
        // A successful parry cancels the remaining impact and owns the reaction.
        if (State != ENurseState::Attack || FeralPhase != EMutant3FeralPhase::Flight) return;
    }
}

void AMutant3::BeginFeralRecovery(float Seconds)
{
    FeralPhase = EMutant3FeralPhase::Recovery;
    FeralTime = 0.f;
    FeralRecoveryDuration = FMath::Max(0.f, Seconds);
    bFeralHitConsumed = true;
    TransitionFeralLocomotion(IdleClip, 1.f, .24f);
}

void AMutant3::RestoreFeralMovement()
{
    if (!bFeralMovementSaved) return;
    auto* Move = GetCharacterMovement();
    Move->bOrientRotationToMovement = bSavedOrientToMovement;
    Move->AirControl = SavedAirControl;
    bFeralMovementSaved = false;
}

void AMutant3::FinishFeralAction()
{
    RestoreFeralMovement();
    FeralPhase = EMutant3FeralPhase::None;
    FeralTarget.Reset();
    bFeralHitConsumed = true;
    if (State == ENurseState::Attack) State = ENurseState::Recovery;
}

void AMutant3::CancelFeralAction()
{
    if (FeralPhase == EMutant3FeralPhase::None) return;
    // Interruption may happen in the ApplyDamage callback (parry). Cancel both
    // pending launch and future contact before the shared reaction takes ownership.
    GetCharacterMovement()->ClearAccumulatedForces();
    RestoreFeralMovement();
    FeralPhase = EMutant3FeralPhase::None;
    FeralTarget.Reset();
    bFeralHitConsumed = true;
    NextFeralAttackAt = GetWorld()->GetTimeSeconds()+.6;
}

void AMutant3::Tick(float DeltaSeconds)
{
    if (!HasAuthority() || FeralPhase == EMutant3FeralPhase::None || State != ENurseState::Attack)
    {
        if (HasAuthority() && FeralPhase != EMutant3FeralPhase::None) CancelFeralAction();
        Super::Tick(DeltaSeconds);
        return;
    }
    // This action owns its clock. Running ANurseZombie's generic attack tick here
    // would apply a second melee hit and prematurely enter its recovery state.
    ACharacter::Tick(DeltaSeconds);
    const float PreviousTime = FeralTime;
    FeralTime += DeltaSeconds;
    if (AttackClip && FeralPhase != EMutant3FeralPhase::Recovery)
    {
        const float SampleTime = FeralPhase == EMutant3FeralPhase::Flight
            ? FeralTime/FMath::Max(.2f, PounceFlightSeconds)*AttackClip->GetPlayLength() : FeralTime;
        SetAttackAnimationTime(SampleTime);
    }
    if (FeralTarget.IsValid() && ((FeralPhase == EMutant3FeralPhase::Windup && FeralTime < .32f) ||
        (FeralPhase == EMutant3FeralPhase::Claw && FeralTime < ContactTime)))
    {
        const FRotator Facing(0, (FeralTarget->GetActorLocation()-GetActorLocation()).Rotation().Yaw, 0);
        SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), Facing, DeltaSeconds, 540.f));
    }
    switch (FeralPhase)
    {
    case EMutant3FeralPhase::Claw:
        if (PreviousTime <= ContactEnd && FeralTime >= ContactTime) TryClawContact();
        if (State != ENurseState::Attack || FeralPhase != EMutant3FeralPhase::Claw) return;
        if (AttackClip && FeralTime >= AttackClip->GetPlayLength())
        {
            APawn* Victim = FeralTarget.Get();
            if (ClawsPerformed < FMath::Clamp(ClawComboCount, 1, 3) &&
                CanClawFrom(Victim, GetActorLocation(), GetClawStartDistance()))
                BeginClaw();
            else BeginFeralRecovery(ClawRecoverySeconds);
        }
        break;
    case EMutant3FeralPhase::Windup:
        if (FeralTime >= PounceWindupClip->GetPlayLength())
        {
            FVector Velocity;
            if (!HasFeralSight(FeralTarget.Get()) || !BuildPounceVelocity(FeralTarget.Get(), Velocity))
            {
                BeginFeralRecovery(.3f);
                break;
            }
            // Commit the heading at takeoff; moving aside can evade the pounce.
            SetActorRotation(FRotator(0, Velocity.Rotation().Yaw, 0));
            BeginFeralPhase(EMutant3FeralPhase::Flight, PounceFlightClip, .04f);
            LaunchCharacter(Velocity, true, true);
        }
        break;
    case EMutant3FeralPhase::Flight:
        // Actual Landed() ends the flight, including early wall impacts. If the
        // landing surface moves away, relinquish the action and let gravity act.
        if (FeralTime > FMath::Max(.2f, PounceFlightSeconds)+.8f) BeginFeralRecovery(.3f);
        break;
    case EMutant3FeralPhase::Landing:
        if (FeralTime >= PounceLandClip->GetPlayLength()) BeginFeralRecovery(.2f);
        break;
    case EMutant3FeralPhase::Recovery:
        if (FeralTime >= FeralRecoveryDuration) FinishFeralAction();
        break;
    default:
        break;
    }
}

void AMutant3::Landed(const FHitResult& Hit)
{
    Super::Landed(Hit);
    if (!HasAuthority() || State != ENurseState::Attack || FeralPhase != EMutant3FeralPhase::Flight) return;
    // Physical contact is audible/visible even when the player evades damage.
    // Cosmetic pool limits never affect the authoritative attack result below.
    if (auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())
        if (auto* Player=UGameplayStatics::GetPlayerPawn(this,0))
            if (auto* Camera=Player->FindComponentByClass<UCameraComponent>())
                FX->SpawnPounceLanding(Hit,GetActorForwardVector(),PounceImpactRadius,PounceImpactAngle,Camera,this);
    // Center the sector below the actual capsule, using the contacted floor's Z.
    TryPounceImpact(FVector(GetActorLocation().X, GetActorLocation().Y, Hit.ImpactPoint.Z));
    if (State != ENurseState::Attack || FeralPhase != EMutant3FeralPhase::Flight) return;
    GetCharacterMovement()->StopMovementImmediately();
    // Contact owns grounded hips/legs immediately. The spine, head and claws
    // absorb the handoff over .14 s without mixing tucked air legs into support.
    BeginFeralPhase(EMutant3FeralPhase::Landing, PounceLandClip, .14f);
    bFeralHitConsumed = true;
}
