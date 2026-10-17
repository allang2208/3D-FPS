#include "NightWardenMonster.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "../Skills/EnemyAttackDamage.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

namespace
{
bool WardenLivingPlayer(const APawn* Pawn)
{
    if (!IsValid(Pawn) || !Pawn->IsPlayerControlled()) return false;
    const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    return !Health || !Health->IsDead();
}
FVector WardenPathPoint(const TArray<FVector>& Points, float Time, float Rate)
{
    const float Index = FMath::Clamp(Time * Rate, 0.f, float(Points.Num() - 1));
    const int32 First = FMath::FloorToInt(Index);
    return FMath::Lerp(Points[First], Points[FMath::Min(First + 1, Points.Num() - 1)], Index - First);
}
}

double ANightWardenMonster::CombatTime() const
{
    const auto* State = GetWorld() ? GetWorld()->GetGameState() : nullptr;
    return State ? State->GetServerWorldTimeSeconds() : GetWorld() ? GetWorld()->GetTimeSeconds() : 0.;
}

bool ANightWardenMonster::IsControlled() const { return CombatTime() < ControlUntil || (Combat && Combat->bStunned); }

float ANightWardenMonster::AttackPresentationTime() const
{
    return FMath::Clamp(bAttacking ? float(CombatTime() - AttackStartedAt) : StoppedAttackTime,
        0.f, AttackClip ? AttackClip->GetPlayLength() : 0.f);
}

bool ANightWardenMonster::HasAttackSight(const APawn* Candidate) const
{
    if (!IsValid(Candidate)) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(NightWardenMeleeSight), false, this);
    Query.AddIgnoredActor(Candidate);
    return !GetWorld()->LineTraceTestByChannel(GetActorLocation() + FVector(0,0,35),
        Candidate->GetActorLocation() + FVector(0,0,20), ECC_Visibility, Query);
}

bool ANightWardenMonster::CanAttack(APawn* Candidate) const
{
    if (!WardenLivingPlayer(Candidate) || !AttackClip || bAttacking || IsControlled() ||
        IsActorBeingDestroyed() || CombatTime() < NextAttackAt || ForearmTrace.Num() < 2 ||
        ForearmTrace.Num() != PalmTrace.Num() || !GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector Delta = Candidate->GetActorLocation() - GetActorLocation();
    // The existing pursue task brakes at StoppingDistance before the windup.
    return GetVelocity().Size2D() < 12.f && Delta.Size2D() <= AttackRange && FMath::Abs(Delta.Z) < 90.f &&
        FVector::DotProduct(GetActorForwardVector(), Delta.GetSafeNormal2D()) >= .5f && HasAttackSight(Candidate);
}

bool ANightWardenMonster::StartAttack(APawn* Candidate)
{
    if (!HasAuthority() || !CanAttack(Candidate)) return false;
    if (auto* AI = Cast<AMonsterAIController>(GetController())) { AI->StopWander(); AI->StopMovement(); }
    auto* Movement = GetCharacterMovement();
    Movement->StopMovementImmediately();
    bMovementOrientationBeforeAttack = Movement->bOrientRotationToMovement;
    Movement->bOrientRotationToMovement = false;
    AttackTarget = Candidate; HitPlayers.Reset();
    AttackStartedAt = CombatTime(); PreviousAttackTime = StoppedAttackTime = 0.f;
    AttackDamageSnapshot = AttackDamage;
    bAttacking = true; ++AttackSerial;
    NextAttackAt = AttackStartedAt + AttackClip->GetPlayLength() + AttackCooldown;
    ForceNetUpdate();
    return true;
}

void ANightWardenMonster::FaceMeleeTarget(APawn* Candidate, float DeltaSeconds)
{
    // The pursue task owns this approach alignment. Without it, a character
    // arriving sideways could remain stopped outside the attack-facing cone.
    if (!HasAuthority() || bAttacking || IsControlled() || !WardenLivingPlayer(Candidate) || GetVelocity().Size2D() >= 12.f) return;
    const float Desired = (Candidate->GetActorLocation() - GetActorLocation()).Rotation().Yaw;
    SetActorRotation(FRotator(0, FMath::FixedTurn(GetActorRotation().Yaw, Desired, 90.f * DeltaSeconds), 0));
}

void ANightWardenMonster::CancelAttack()
{
    if (!HasAuthority() || !bAttacking) return;
    StoppedAttackTime = AttackPresentationTime();
    bAttacking = false; AttackTarget.Reset();
    GetCharacterMovement()->bOrientRotationToMovement = bMovementOrientationBeforeAttack;
    ForceNetUpdate();
}

void ANightWardenMonster::StopForControl(float Seconds)
{
    if (!HasAuthority()) return;
    CancelAttack();
    ControlUntil = FMath::Max(ControlUntil, CombatTime() + FMath::Max(0.f, Seconds));
    GetCharacterMovement()->StopMovementImmediately();
    ForceNetUpdate();
}

void ANightWardenMonster::TickAttack(float DeltaSeconds)
{
    if (!bAttacking) return;
    const auto* AI = Cast<AMonsterAIController>(GetController());
    APawn* Victim = AttackTarget.Get();
    if (!AttackClip || IsControlled() || !AI || !AI->bDecisionEnabled || !WardenLivingPlayer(Victim))
    { CancelAttack(); return; }
    const float Current = AttackPresentationTime();
    if (Current < FacingLockTime)
    {
        const FVector Delta = Victim->GetActorLocation() - GetActorLocation();
        if (Delta.Size2D() > AttackRange * 2.f || !HasAttackSight(Victim)) { CancelAttack(); return; }
        const float Yaw = FMath::FixedTurn(GetActorRotation().Yaw, Delta.Rotation().Yaw, 90.f * DeltaSeconds);
        SetActorRotation(FRotator(0, Yaw, 0));
    }
    // Once committed, the swing keeps its facing and can miss a dodging player.
    if (Current >= ContactStart && PreviousAttackTime < ContactEnd)
        SweepAttack(FMath::Max(PreviousAttackTime, ContactStart), FMath::Min(Current, ContactEnd));
    if (!bAttacking) return; // A parry inside ApplyDamage can synchronously cancel us.
    PreviousAttackTime = Current;
    if (Current >= AttackClip->GetPlayLength()) CancelAttack();
}

void ANightWardenMonster::SweepAttack(float FromTime, float ToTime)
{
    if (ToTime <= FromTime || ForearmTrace.Num() < 2 || ForearmTrace.Num() != PalmTrace.Num()) return;
    const FTransform MeshFrame = GetMesh()->GetComponentTransform();
    const float Radius = FMath::Max(1.f, TraceRadius * float(MeshFrame.GetScale3D().GetAbsMax()));
    const int32 Steps = FMath::Clamp(FMath::CeilToInt((ToTime - FromTime) * 120.f), 1, 32);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(NightWardenGiantArmContact), false, this);
    FVector A = MeshFrame.TransformPosition(WardenPathPoint(ForearmTrace, FromTime, TraceSampleRate));
    FVector B = MeshFrame.TransformPosition(WardenPathPoint(PalmTrace, FromTime, TraceSampleRate));
    for (int32 Step = 1; Step <= Steps && bAttacking; ++Step)
    {
        const float Time = FMath::Lerp(FromTime, ToTime, float(Step) / Steps);
        const FVector NextA = MeshFrame.TransformPosition(WardenPathPoint(ForearmTrace, Time, TraceSampleRate));
        const FVector NextB = MeshFrame.TransformPosition(WardenPathPoint(PalmTrace, Time, TraceSampleRate));
        const FVector Axis = NextB - NextA;
        const FQuat Orientation = FQuat::FindBetweenNormals(FVector::UpVector, Axis.GetSafeNormal());
        TArray<FHitResult> Hits;
        GetWorld()->SweepMultiByObjectType(Hits, (A+B)*.5, (NextA+NextB)*.5, Orientation,
            FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeCapsule(Radius, Radius + Axis.Size()*.5), Query);
        for (const FHitResult& Hit : Hits)
        {
            auto* Player = Cast<APawn>(Hit.GetActor());
            if (!WardenLivingPlayer(Player) || HitPlayers.Contains(Player)) continue;
            const FVector Delta = Player->GetActorLocation() - GetActorLocation();
            if (Delta.Size2D() > AttackRange + Player->GetSimpleCollisionRadius() + Radius ||
                FVector::DotProduct(Delta.GetSafeNormal2D(), GetActorForwardVector()) < .05f || !HasAttackSight(Player)) continue;
            // The actual palm must also have a clear contact line; a long arm
            // cannot damage through a pillar merely because the chest sees past it.
            FCollisionQueryParams ContactQuery(Query); ContactQuery.AddIgnoredActor(Player);
            const FVector ContactPoint = Hit.bStartPenetrating ? Player->GetActorLocation() : FVector(Hit.ImpactPoint);
            if (GetWorld()->LineTraceTestByChannel(NextB, ContactPoint, ECC_Visibility, ContactQuery)) continue;
            HitPlayers.Add(Player);
            UGameplayStatics::ApplyDamage(Player, AttackDamageSnapshot, GetController(), this, UEnemyMeleeDamage::StaticClass());
            if (!bAttacking || IsActorBeingDestroyed()) break;
        }
        A = NextA; B = NextB;
    }
}

void ANightWardenMonster::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ANightWardenMonster, bAttacking);
    DOREPLIFETIME(ANightWardenMonster, AttackSerial);
    DOREPLIFETIME(ANightWardenMonster, AttackStartedAt);
    DOREPLIFETIME(ANightWardenMonster, StoppedAttackTime);
    DOREPLIFETIME(ANightWardenMonster, ControlUntil);
}
