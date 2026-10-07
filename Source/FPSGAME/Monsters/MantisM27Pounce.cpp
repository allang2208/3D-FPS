#include "MantisM27Monster.h"
#include "FatZombieAnimInstance.h"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "FPSCombatHealthComponent.h"
#include "Mutant3PounceCameraShake.h"
#include "MantisM27AttackDamage.h"
#include "../Skills/IceWallCombat.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

bool AMantisM27Monster::HasAttackSight(const APawn* Victim) const
{
    if (!IsValid(Victim)) return false;
    if (const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>(); Vitals && Vitals->IsDead()) return false;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M27PounceSight), false, this);
    Query.AddIgnoredActor(Victim);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation()+FVector(0,0,25), Victim->GetActorLocation(), ECC_Visibility, Query);
}

float AMantisM27Monster::MeleeStartDistance(const APawn* Victim) const
{
    // Leave contact slack for movement during the windup, without requiring
    // the long-armed hunter to squeeze into the player's collision/avoidance.
    // Contact includes the victim capsule. Approach and selection must measure
    // that same surface. Reserve 5% for contact; with the M27's 190 cm base
    // reach, ordinary melee overlaps the 280 cm pounce threshold instead of
    // leaving a band where a moving player cannot trigger either attack.
    return FMath::Max(40.f, MonsterCombatTuning::AttackDistance(AttackRange)*.95f) +
        (IsValid(Victim) ? Victim->GetSimpleCollisionRadius() : 0.f);
}

bool AMantisM27Monster::CanMeleeFrom(const APawn* Victim, const FVector& From, float Range) const
{
    if (!IsValid(Victim)) return false;
    if (const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>(); Vitals && Vitals->IsDead()) return false;
    const FVector Offset = Victim->GetActorLocation()-From;
    if (Offset.Size2D() > Range || FMath::Abs(Offset.Z) >= 110.f) return false;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M27MeleeApproach), false, this);
    Query.AddIgnoredActor(Victim);
    return !GetWorld()->LineTraceSingleByChannel(Hit, From+FVector(0,0,25), Victim->GetActorLocation(), ECC_Visibility, Query);
}

bool AMantisM27Monster::WantsPounce(APawn* Victim) const
{
    const float MeleeDistance = MeleeStartDistance(Victim);
    return IsValid(Victim) && !IceWallCombat::BlockingWall(this, Victim, MeleeDistance) &&
        FVector::Dist2D(Victim->GetActorLocation(), GetActorLocation()) > MeleeDistance;
}

bool AMantisM27Monster::CanStartMantisAttack(APawn* Victim) const
{
    if (!HasAuthority() || !IsValid(Victim) || Health <= 0.f || Combat->IsBusy() ||
        PouncePhase != EM27PouncePhase::None || !AttackCooldownReady() || !IsCloakRecoveryReady() ||
        GetWorld()->GetTimeSeconds() < NextMantisAttackAt || !GetCharacterMovement()->IsMovingOnGround()) return false;
    if (IceWallCombat::BlockingWall(this, Victim, MeleeStartDistance(Victim))) return true;
    if (!WantsPounce(Victim)) return CanMeleeFrom(Victim, GetActorLocation(), MeleeStartDistance(Victim));
    if (!HasAttackSight(Victim)) return false;
    const double Now = GetWorld()->GetTimeSeconds();
    const float Distance = FVector::Dist2D(Victim->GetActorLocation(), GetActorLocation());
    if (Now < NextPounceAt || Distance < PounceMinRange || Distance > PounceMaxRange ||
        !PounceWindupClip || !PounceFlightClip || !PounceLandClip) return false;
    // The 10 Hz knowledge service can ask repeatedly. Plan at most ~3 Hz;
    // start and takeoff both compute a fresh bounded ballistic solution.
    if (Now >= NextPouncePlanAt || PlannedPounceTarget.Get() != Victim)
    {
        NextPouncePlanAt = Now+.35;
        PlannedPounceTarget = Victim;
        FVector Velocity;
        bPouncePlanReady = BuildPounceVelocity(Victim, Velocity);
    }
    return bPouncePlanReady;
}

bool AMantisM27Monster::BuildPounceVelocity(APawn* Victim, FVector& Velocity) const
{
    if (!IsValid(Victim)) return false;
    Velocity = FVector::ZeroVector;
    const FVector Start = GetActorLocation(), TargetPosition = Victim->GetActorLocation();
    const FVector Offset = TargetPosition-Start;
    // Selection range and travel budget are different: otherwise leading a
    // fleeing player near max range gets silently clamped back behind them.
    const float MaxTravel = FMath::Max(1.f,PounceMaxRange)+750.f;
    const bool TakingOff = PouncePhase == EM27PouncePhase::Windup && PounceTarget.Get() == Victim;
    if (Offset.Size2D() < PounceMinRange || Offset.Size2D() > (TakingOff ? MaxTravel : PounceMaxRange) ||
        FMath::Abs(Offset.Z) > 150.f) return false;
    const auto* Capsule = GetCapsuleComponent();
    const auto* Move = GetCharacterMovement();
    const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
    const float Duration = FMath::Max(.2f, PounceFlightSeconds), Gravity = Move->GetGravityZ();
    const FVector TargetVelocity = Victim->GetVelocity();
    const FVector PlanarVelocity(TargetVelocity.X, TargetVelocity.Y, 0);
    FVector PredictedVelocity = PlanarVelocity;
    if (const auto* Character = Cast<ACharacter>(Victim))
    {
        const auto* TargetMove = Character->GetCharacterMovement();
        const FVector Acceleration = TargetMove->GetCurrentAcceleration();
        // Account for starting/turning for only 0.12 s, then coast. Extrapolating
        // full input acceleration over the entire flight badly overshoots.
        PredictedVelocity = (PlanarVelocity+FVector(Acceleration.X,Acceleration.Y,0)*.12f)
            .GetClampedToMaxSize(FMath::Max(PlanarVelocity.Size(),TargetMove->GetMaxSpeed()));
    }
    // This function is sampled again at takeoff: do not add elapsed windup.
    const float LeadSeconds = Duration+.04f;
    FVector Lead = (PlanarVelocity*.06f+PredictedVelocity*(LeadSeconds-.06f)).GetClampedToMaxSize(750.f);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M27PounceArc), false, this);
    Query.AddIgnoredActor(Victim);
    if (const auto* Character = Cast<ACharacter>(Victim); Character && !Lead.IsNearlyZero(1.f))
    {
        const auto* TargetCapsule = Character->GetCapsuleComponent();
        FHitResult Obstacle;
        const auto TargetShape = FCollisionShape::MakeCapsule(TargetCapsule->GetScaledCapsuleRadius(),
            FMath::Max(TargetCapsule->GetScaledCapsuleRadius(), TargetCapsule->GetScaledCapsuleHalfHeight()-2.f));
        if (GetWorld()->SweepSingleByChannel(Obstacle, TargetPosition, TargetPosition+Lead, FQuat::Identity,
            TargetCapsule->GetCollisionObjectType(), TargetShape, Query, FCollisionResponseParams(TargetCapsule->GetCollisionResponseToChannels())))
            Lead *= FMath::Max(0.f, Obstacle.Time-.02f);
    }
    const auto Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), HalfHeight-1.f);
    const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
    const int32 Candidates = Lead.IsNearlyZero(1.f) ? 1 : 3;
    for (int32 Candidate=0; Candidate<Candidates; ++Candidate)
    {
        const FVector Aim = TargetPosition+Lead*(1.f-.5f*Candidate);
        FVector Planar = Aim-Start; Planar.Z = 0.f;
        const float StandOff = FMath::Max(Capsule->GetScaledCapsuleRadius()+Victim->GetSimpleCollisionRadius()+25.f,
            FMath::Min(150.f,PounceImpactRadius*.45f));
        FVector Landing = Aim-Planar.GetSafeNormal()*StandOff;
        FVector Travel = Landing-Start; Travel.Z = 0.f;
        Travel = Travel.GetClampedToMaxSize(MaxTravel);
        Landing.X = Start.X+Travel.X; Landing.Y = Start.Y+Travel.Y;
        // Reduced lead/range-clamped plans still need to cover the predicted
        // target; otherwise keep pursuing rather than knowingly land short.
        if (FVector::Dist2D(Landing,TargetPosition+Lead) > PounceImpactRadius+Victim->GetSimpleCollisionRadius()-25.f) continue;
        FHitResult Floor;
        if (!GetWorld()->LineTraceSingleByChannel(Floor, Landing+FVector(0,0,120), Landing-FVector(0,0,350), ECC_Visibility, Query) || !Move->IsWalkable(Floor)) continue;
        Landing = Floor.ImpactPoint+FVector(0,0,HalfHeight+2.f);
        if (FMath::Abs(Landing.Z-Start.Z) > 150.f) continue;
        const FVector CandidateVelocity = (Landing-Start)/Duration-FVector(0,0,.5f*Gravity*Duration);
        FVector Previous = Start;
        bool Clear = true;
        for (int32 Step=1; Step<=16; ++Step)
        {
            const float T = Duration*Step/16.f;
            const FVector Next = Start+CandidateVelocity*T+FVector(0,0,.5f*Gravity*T*T);
            FHitResult Hit;
            if (GetWorld()->SweepSingleByChannel(Hit, Previous, Next, FQuat::Identity, Capsule->GetCollisionObjectType(), Shape, Query, Response))
            { Clear = false; break; }
            Previous = Next;
        }
        if (Clear) { Velocity = CandidateVelocity; return true; }
    }
    return false;
}

bool AMantisM27Monster::StartPounce(APawn* Victim)
{
    FVector Velocity;
    if (!CanStartMantisAttack(Victim) || !WantsPounce(Victim) || !BuildPounceVelocity(Victim, Velocity)) return false;
    BeginShadowStrike();
    if (auto* AI = Cast<AAIController>(GetController())) AI->StopMovement();
    auto* Move = GetCharacterMovement();
    Move->StopMovementImmediately();
    bSavedPounceOrient = Move->bOrientRotationToMovement;
    SavedPounceAirControl = Move->AirControl;
    bPounceMovementSaved = true;
    Move->bOrientRotationToMovement = false;
    Move->AirControl = 0.f;
    PounceTarget = Victim;
    bPounceImpactConsumed = false;
    bContactConsumed = true;
    State = ENurseState::Attack;
    SetActorRotation(FRotator(0, (Victim->GetActorLocation()-GetActorLocation()).Rotation().Yaw, 0));
    NextPounceAt = GetWorld()->GetTimeSeconds()+FMath::Max(0.f, PounceCooldownSeconds);
    BeginPouncePhase(EM27PouncePhase::Windup);
    return true;
}

void AMantisM27Monster::BeginPouncePhase(EM27PouncePhase Phase)
{
    PouncePhase = Phase;
    PouncePhaseStartedAt = ServerClock();
    PresentPounce();
    ForceNetUpdate();
}

void AMantisM27Monster::PresentPounce()
{
    if (PouncePhase == EM27PouncePhase::None) return;
    UAnimSequence* Clip = PouncePhase == EM27PouncePhase::Windup ? PounceWindupClip.Get() :
        PouncePhase == EM27PouncePhase::Flight ? PounceFlightClip.Get() :
        PouncePhase == EM27PouncePhase::Landing ? PounceLandClip.Get() : IdleClip.Get();
    AttackClip = Clip;
    if (auto* Animation = PosePlayer())
    {
        FMonsterClipTransition Settings;
        Settings.bGroundLowerBody = PouncePhase == EM27PouncePhase::Landing;
        const bool Recovering = PouncePhase == EM27PouncePhase::Recovery;
        Animation->TransitionTo(Clip, Recovering, !Recovering,
            PouncePhase == EM27PouncePhase::Flight ? .04f : .14f, Settings);
    }
}

void AMantisM27Monster::OnRep_PouncePhase()
{
    if (State != ENurseState::Dead && State != ENurseState::Stagger) PresentPounce();
}

void AMantisM27Monster::TickPounce(float DeltaSeconds)
{
    const float Time = FMath::Max(0.f, float(ServerClock()-PouncePhaseStartedAt));
    if (AttackClip && PouncePhase != EM27PouncePhase::Recovery)
        SetAttackAnimationTime(PouncePhase == EM27PouncePhase::Flight ?
            Time/FMath::Max(.2f, PounceFlightSeconds)*AttackClip->GetPlayLength() : Time);
    if (!HasAuthority()) return;
    switch (PouncePhase)
    {
    case EM27PouncePhase::Windup:
        if (Time < .32f && PounceTarget.IsValid())
            SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(),
                FRotator(0, (PounceTarget->GetActorLocation()-GetActorLocation()).Rotation().Yaw, 0), DeltaSeconds, 540.f));
        if (Time >= PounceWindupClip->GetPlayLength())
        {
            FVector Velocity;
            if (!HasAttackSight(PounceTarget.Get()) || !BuildPounceVelocity(PounceTarget.Get(), Velocity))
            { BeginPouncePhase(EM27PouncePhase::Recovery); break; }
            SetActorRotation(FRotator(0, Velocity.Rotation().Yaw, 0));
            BeginPouncePhase(EM27PouncePhase::Flight);
            LaunchCharacter(Velocity, true, true);
        }
        break;
    case EM27PouncePhase::Flight:
        if (Time > FMath::Max(.2f, PounceFlightSeconds)+.8f) BeginPouncePhase(EM27PouncePhase::Recovery);
        break;
    case EM27PouncePhase::Landing:
        if (Time >= PounceLandClip->GetPlayLength()) BeginPouncePhase(EM27PouncePhase::Recovery);
        break;
    case EM27PouncePhase::Recovery:
        if (Time >= .25f)
        {
            CancelPounce();
            if (State == ENurseState::Attack) State = ENurseState::Recovery;
            ForceNetUpdate();
        }
        break;
    default: break;
    }
}

void AMantisM27Monster::RestorePounceMovement()
{
    if (!bPounceMovementSaved) return;
    GetCharacterMovement()->bOrientRotationToMovement = bSavedPounceOrient;
    GetCharacterMovement()->AirControl = SavedPounceAirControl;
    bPounceMovementSaved = false;
}

void AMantisM27Monster::CancelPounce()
{
    if (PouncePhase == EM27PouncePhase::None) return;
    RestorePounceMovement();
    PouncePhase = EM27PouncePhase::None;
    PounceTarget.Reset();
    bPounceImpactConsumed = bContactConsumed = true;
    ActiveAttackDamageScale = 1.f;
    NextMantisAttackAt = GetWorld()->GetTimeSeconds()+.2;
    // Do not clear movement forces here: an interrupting knockback/knockdown
    // may have just installed its own physical response.
    ForceNetUpdate();
}

float AMantisM27Monster::ApplyMeleeDamage(APawn* Victim)
{
    const FVector Contact = Victim->GetActorLocation();
    const float Applied = UGameplayStatics::ApplyDamage(Victim, AttackDamage*ActiveAttackDamageScale, GetController(), this, UMantisM27MeleeDamage::StaticClass());
    if (Applied > 0.f) MulticastMantisContact(Contact, ServerClock(), (++MantisContactAudioIndex & 1) != 0);
    return Applied;
}

void AMantisM27Monster::PounceImpact(const FVector& LandingPoint)
{
    if (bPounceImpactConsumed) return;
    bPounceImpactConsumed = true;
    const float Radius = FMath::Max(1.f, PounceImpactRadius), Height = 180.f;
    const float HalfAngle = FMath::Clamp(PounceImpactAngle, 1.f, 180.f)*.5f;
    const float ConeCos = FMath::Cos(FMath::DegreesToRadians(HalfAngle));
    const FVector Forward = GetActorForwardVector().GetSafeNormal2D();
    const FVector Left = Forward.RotateAngleAxis(-HalfAngle, FVector::UpVector)*Radius;
    const FVector Right = Forward.RotateAngleAxis(HalfAngle, FVector::UpVector)*Radius;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M27PounceImpact), false, this);
    TArray<FOverlapResult> Hits;
    GetWorld()->OverlapMultiByObjectType(Hits, LandingPoint, FQuat::Identity, FCollisionObjectQueryParams(ECC_Pawn),
        FCollisionShape::MakeBox(FVector(Radius, Radius, Height)), Query);
    TSet<APawn*> Contacted;
    bool PlayedContact = false;
    for (const auto& Hit : Hits)
    {
        APawn* Victim = Cast<APawn>(Hit.GetActor());
        if (!IsValid(Victim) || !Victim->IsPlayerControlled() || Contacted.Contains(Victim)) continue;
        Contacted.Add(Victim);
        float VictimRadius, VictimHeight;
        Victim->GetSimpleCollisionCylinder(VictimRadius, VictimHeight);
        const FVector Offset = Victim->GetActorLocation()-LandingPoint;
        // Test the whole victim capsule, including a landing against its top;
        // feet-only height checks could reject a direct downward collision.
        if (Offset.Z+VictimHeight < -60.f || Offset.Z-VictimHeight > Height) continue;
        const FVector Planar(Offset.X, Offset.Y, 0);
        const float Distance = Planar.Size();
        if (Distance > Radius+VictimRadius) continue;
        const bool Inside = Distance < UE_KINDA_SMALL_NUMBER || FVector::DotProduct(Forward, Planar/Distance) >= ConeCos;
        if (!Inside && FMath::PointDistToSegmentSquared(Planar, FVector::ZeroVector, Left) > FMath::Square(VictimRadius) &&
            FMath::PointDistToSegmentSquared(Planar, FVector::ZeroVector, Right) > FMath::Square(VictimRadius)) continue;
        if (!HasAttackSight(Victim)) continue;
        const float Applied = UGameplayStatics::ApplyDamage(Victim, AttackDamage*PounceDamageScale*ActiveAttackDamageScale,
            GetController(), this, UMantisM27PounceDamage::StaticClass());
        if (Applied > 0.f)
        {
            ++SuccessfulHits;
            if (!PlayedContact)
            {
                PlayedContact = true;
                MulticastMantisContact(LandingPoint+FVector(0,0,60), ServerClock(), (++MantisContactAudioIndex & 1) != 0);
            }
            const auto* Vitals = IsValid(Victim) ? Victim->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
            if (IsValid(Victim) && (!Vitals || !Vitals->IsDead()))
            {
                // Cripple and bleeding are applied by the accepted health-damage
                // event, after dodge, armor and invulnerability have resolved.
                if (auto* PC = Cast<APlayerController>(Victim->GetController()); PC && PC->IsLocalController() && PC->PlayerCameraManager)
                    PC->PlayerCameraManager->StartCameraShake(UMutant3PounceCameraShake::StaticClass());
            }
        }
        if (State != ENurseState::Attack || PouncePhase != EM27PouncePhase::Flight) return;
    }
}

void AMantisM27Monster::Landed(const FHitResult& Hit)
{
    Super::Landed(Hit);
    if (!HasAuthority() || State != ENurseState::Attack || PouncePhase != EM27PouncePhase::Flight) return;
    MulticastMantisAccent(TEXT("PounceLand"), ServerClock());
    if (auto* FX = GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())
        if (auto* Player = UGameplayStatics::GetPlayerPawn(this, 0))
            if (auto* Camera = Player->FindComponentByClass<UCameraComponent>())
                FX->SpawnPounceLanding(Hit, GetActorForwardVector(), PounceImpactRadius, PounceImpactAngle, Camera, this, false);
    PounceImpact(FVector(GetActorLocation().X, GetActorLocation().Y, Hit.ImpactPoint.Z));
    if (State != ENurseState::Attack || PouncePhase != EM27PouncePhase::Flight) return;
    GetCharacterMovement()->StopMovementImmediately();
    BeginPouncePhase(EM27PouncePhase::Landing);
}
