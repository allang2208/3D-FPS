#include "M25BiteComponent.h"
#include "VortexCofferM25.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"

UM25BiteComponent::UM25BiteComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
    SetIsReplicatedByDefault(true);
}

void UM25BiteComponent::BeginPlay()
{
    Super::BeginPlay();
    Monster = Cast<AVortexCofferM25>(GetOwner());
    if (Monster.IsValid()) AddTickPrerequisiteComponent(Monster->GetMesh());
    OnRep_State();
}

float UM25BiteComponent::Clock() const
{
    const auto* GS = GetWorld()->GetGameState();
    return GS ? GS->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
}

void UM25BiteComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UM25BiteComponent, State);
}

bool UM25BiteComponent::LivingPlayer(const APawn* Victim) const
{
    if (!IsValid(Victim) || !Victim->IsPlayerControlled() || Victim->IsActorBeingDestroyed()) return false;
    const auto* Health = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    return Health && !Health->IsDead();
}

bool UM25BiteComponent::CanExecute() const
{
    const auto* M = Monster.Get();
    if (!M || !bBiteEnabled || !M->BiteClip || !M->IsActorTickEnabled() || M->IsActorBeingDestroyed()
        || M->ActorHasTag(TEXT("Friendly")) || M->ActorHasTag(TEXT("Summoned"))) return false;
    const auto* AI = Cast<AMonsterAIController>(M->GetController());
    if (!AI || !AI->bDecisionEnabled) return false;
    if (M->Combat && (M->Combat->IsDead() || M->Combat->IsControlled()
        || M->Combat->StunSecondsRemaining() > 0.f || M->Combat->IsImmobileReaction())) return false;
    const auto* Status = M->FindComponentByClass<UCombatStatusFormula>();
    return !Status || (!Status->IsFrozen() && !Status->IsStunned() && !Status->IsPetrified());
}

FVector UM25BiteComponent::Mouth() const
{
    return Monster.IsValid() ? Monster->GetMesh()->GetSocketLocation(TEXT("socket_maw")) : FVector::ZeroVector;
}

bool UM25BiteComponent::ClearSegment(FVector From, FVector To, const APawn* Victim) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M25BiteSight), false, GetOwner());
    if (Victim) Query.AddIgnoredActor(Victim);
    FHitResult Block;
    return !GetWorld()->LineTraceSingleByChannel(Block, From, To, ECC_Visibility, Query);
}

bool UM25BiteComponent::InFront(const APawn* Victim, FVector From, FVector Forward) const
{
    if (!LivingPlayer(Victim)) return false;
    const FVector Delta = Victim->GetActorLocation() - From;
    return FVector::DotProduct(Delta.GetSafeNormal2D(), Forward.GetSafeNormal2D())
        >= FMath::Cos(FMath::DegreesToRadians(FMath::Clamp(HalfAngle, 1.f, 89.f)));
}

bool UM25BiteComponent::CanAttack(APawn* Victim) const
{
    if (IsBusy() || !CanExecute() || Clock() < ReadyAt || !LivingPlayer(Victim)) return false;
    const FVector From = Mouth();
    if (!InFront(Victim, From, Monster->GetActorForwardVector())) return false;
    float Radius = 0.f, HalfHeight = 0.f;
    Victim->GetSimpleCollisionCylinder(Radius, HalfHeight);
    const FVector Delta = Victim->GetActorLocation() - From;
    if (Delta.Size2D() - Radius > TriggerReach || FMath::Abs(Delta.Z) > HalfHeight + ContactRadius) return false;
    const FVector Body = Monster->GetMesh()->GetSocketLocation(TEXT("body_05"));
    FVector Aim = Victim->GetActorLocation();
    Aim.Z = FMath::Clamp(From.Z, Aim.Z - HalfHeight + Radius, Aim.Z + HalfHeight - Radius);
    return ClearSegment(Body, From, Victim) && ClearSegment(From, Aim, Victim);
}

void UM25BiteComponent::SetTarget(APawn* Victim)
{
    if (Target.Get() != Victim && GetOwner()->HasAuthority() && IsBusy()) Cancel();
    Target = Victim;
}

bool UM25BiteComponent::StartAttack(APawn* Victim)
{
    if (!GetOwner()->HasAuthority() || !CanAttack(Victim)) return false;
    Target = Victim;
    AttackDamage = FMath::Max(0.f, PhysicalAttack);
    bCommitted = bHitConsumed = false;
    PreviousAnimationTime = 0.f;
    State.bActive = true;
    State.StartedAt = Clock();
    State.PlayRate = FMath::Clamp(PlaybackRate, .5f, 2.f);
    State.Duration = Monster->BiteClip->GetPlayLength() / State.PlayRate;
    State.Forward = Monster->GetActorForwardVector();
    PreviousMouth = Mouth();
    StartMouthLocal = Monster->GetActorTransform().InverseTransformPosition(PreviousMouth);
    Monster->GetCharacterMovement()->StopMovementImmediately();
    if (auto* AI = Cast<AMonsterAIController>(Monster->GetController())) AI->StopMovement();
    OnRep_State();
    GetOwner()->ForceNetUpdate();
    // No call into MagicExecution: an ongoing charge or release is left intact.
    if (auto* AI = Cast<AMonsterAIController>(Monster->GetController())) AI->UpdateKnowledge();
    return true;
}

float UM25BiteComponent::AnimationTime() const
{
    return FMath::Clamp(Clock() - State.StartedAt, 0.f, State.Duration) * State.PlayRate;
}

float UM25BiteComponent::AnimationWeight() const
{
    if (!State.bActive) return 0.f;
    // Blend in source-animation seconds so a faster bite keeps its sharp onset/recovery.
    const float Time = AnimationTime();
    return FMath::Min(FMath::SmoothStep(0.f, .14f, Time),
        FMath::SmoothStep(0.f, .18f, State.Duration * State.PlayRate - Time));
}

void UM25BiteComponent::OnRep_State()
{
    SetComponentTickEnabled(State.bActive);
    if (State.bActive && GetNetMode() != NM_DedicatedServer && Monster.IsValid() && Monster->BiteSound)
        UGameplayStatics::PlaySoundAtLocation(this, Monster->BiteSound, Mouth(), .95f, 1.f, 0.f,
            Monster->OneShotAttenuation(1500.f));
    if (Monster.IsValid()) Monster->RefreshCombatPoseTick();
}

void UM25BiteComponent::Contact()
{
    if (bHitConsumed || !State.bActive || !CanExecute()) return;
    const FVector Current = Mouth();
    APawn* Victim = Target.Get();
    if (!InFront(Victim, Monster->GetActorTransform().TransformPosition(StartMouthLocal), State.Forward)) return;
    // A soft muzzle may protrude through a wall; the torso-to-mouth segment still blocks damage.
    if (!ClearSegment(Monster->GetMesh()->GetSocketLocation(TEXT("body_05")), Current, Victim)) return;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M25BiteContact), false, GetOwner());
    FCollisionObjectQueryParams Objects;
    // The broad mouth volume overlaps the floor. Find player contact separately
    // from the visibility segments that prevent bites through walls and props.
    Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByObjectType(Hits, PreviousMouth, Current, FQuat::Identity,
        Objects, FCollisionShape::MakeSphere(FMath::Max(1.f, ContactRadius)), Query);
    const FHitResult* First = nullptr;
    for (const FHitResult& Hit : Hits)
    {
        const auto* Part = Hit.GetComponent();
        const auto* Pawn = Cast<APawn>(Hit.GetActor());
        const bool PlayerBody = Pawn && Pawn->IsPlayerControlled() && Part == Pawn->GetRootComponent();
        if (!PlayerBody) continue;
        if (!First || Hit.Time < First->Time) First = &Hit;
    }
    if (!First || First->GetActor() != Victim) return;
    // Initial overlaps have no reliable surface impact point. Trace to the same
    // capsule-axis point used by CanAttack, keeping the sight segment above ground.
    float Radius = 0.f, HalfHeight = 0.f;
    Victim->GetSimpleCollisionCylinder(Radius, HalfHeight);
    FVector Aim = Victim->GetActorLocation();
    Aim.Z = FMath::Clamp(Current.Z, Aim.Z - HalfHeight + Radius, Aim.Z + HalfHeight - Radius);
    if (!ClearSegment(Current, Aim, Victim)) return;
    bHitConsumed = true; // Before synchronous parry/damage callbacks; one bite never hits twice.
    UGameplayStatics::ApplyPointDamage(Victim, AttackDamage, State.Forward, *First,
        Monster->GetController(), Monster.Get(), UEnemyMeleeDamage::StaticClass());
    if (!CanExecute()) Cancel();
}

void UM25BiteComponent::TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta, Type, Tick);
    if (!GetOwner()->HasAuthority() || !State.bActive) return;
    if (!CanExecute() || !LivingPlayer(Target.Get())) { Cancel(); return; }
    const float Time = AnimationTime();
    if (!bCommitted && Time >= ContactStart)
    {
        bCommitted = true;
        ReadyAt = Clock() + FMath::Max(0.f, BiteCooldown);
    }
    // At 2x the contact window is 80 ms: include the frame that crosses it.
    // Sweep from the previous mouth sample and retain the single-hit/occlusion rules.
    if (PreviousAnimationTime <= ContactEnd && Time >= ContactStart) Contact();
    if (!State.bActive) return;
    PreviousAnimationTime = Time;
    PreviousMouth = Mouth();
    if (Clock() - State.StartedAt >= State.Duration)
    {
        State.bActive = false;
        OnRep_State();
        GetOwner()->ForceNetUpdate();
    }
}

void UM25BiteComponent::Cancel()
{
    if (!GetOwner()->HasAuthority()) return;
    if (!bCommitted) ReadyAt = FMath::Max(ReadyAt, double(Clock()) + .35);
    State.bActive = false;
    OnRep_State();
    GetOwner()->ForceNetUpdate();
}

void UM25BiteComponent::EndPlay(EEndPlayReason::Type Reason)
{
    State.bActive = false;
    if (Monster.IsValid()) Monster->RefreshCombatPoseTick();
    Super::EndPlay(Reason);
}

void UM25BiteComponent::Interrupt()
{
    if (GetOwner()->HasAuthority()) Cancel();
    else { State.bActive = false; OnRep_State(); }
}
