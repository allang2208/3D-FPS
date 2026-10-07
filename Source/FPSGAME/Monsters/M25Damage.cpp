#include "VortexCofferM25.h"
#include "MonsterCorpseRagdollComponent.h"
#include "M25BackElectricComponent.h"
#include "M25BiteComponent.h"
#include "M25MagicComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"

void AVortexCofferM25::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AVortexCofferM25, MaxHealth);
    DOREPLIFETIME(AVortexCofferM25, Health);
    DOREPLIFETIME(AVortexCofferM25, DeathStartedAt);
}

void AVortexCofferM25::ApplyHitCollision()
{
    // Movement uses the capsule; damage traces use the anatomical skeletal bodies.
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
}

bool AVortexCofferM25::IsWeakpointHit(const FHitResult& Hit) const
{
    // Keep classification available after a lethal hit for hit markers and sounds.
    // Network hit receipts carry the actor/bone but may omit Component.
    return Hit.GetActor() == this && (!Hit.GetComponent() || Hit.GetComponent() == GetMesh())
        && !Hit.BoneName.IsNone()
        && (Hit.BoneName == TEXT("maw") || GetMesh()->BoneIsChildOf(Hit.BoneName, TEXT("maw")));
}

float AVortexCofferM25::CombatClock() const
{
    const auto* World = GetWorld();
    if (!World) return 0.f;
    const auto* State = World->GetGameState();
    return State ? State->GetServerWorldTimeSeconds() : World->GetTimeSeconds();
}

float AVortexCofferM25::DeathAnimationTime() const
{
    return Dead() ? FMath::Max(0.f, CombatClock() - DeathStartedAt) : 0.f;
}

void AVortexCofferM25::InterruptAttack(float Seconds)
{
    if (!HasAuthority() || Dead() || Seconds <= 0.f) return;
    bHitReaction = true;
    if (Bite) Bite->Interrupt();
    if (Magic) Magic->Interrupt();
    GetCharacterMovement()->StopMovementImmediately();
    if (Combat) Combat->BeginReaction(Seconds);
    RefreshCombatPoseTick();
}

void AVortexCofferM25::StartHitPresentation()
{
    if (Dead()) return;
    if (GetNetMode() != NM_DedicatedServer && HitSound)
        UGameplayStatics::PlaySoundAtLocation(this, HitSound,
            GetMesh()->GetSocketLocation(TEXT("socket_maw")), .9f, 1.f, 0.f, OneShotAttenuation(1200.f));
    bHitReaction = true;
    HitTime = 0.f;
    RefreshCombatPoseTick();
}

void AVortexCofferM25::SetHitPresentationTime(float Elapsed, float Remaining)
{
    if (Dead()) return;
    const float Length = HitClip ? HitClip->GetPlayLength() : .6f;
    HitTime = FMath::Clamp(Elapsed < .12f ? Elapsed :
        Remaining > .4f ? .12f : Length - FMath::Max(0.f, Remaining), 0.f, Length);
    // The shared component owns the only reaction clock and all control deadlines.
    if (HasAuthority() && Remaining <= 0.f && Combat) Combat->FinishReaction();
}

void AVortexCofferM25::FinishHitReaction()
{
    bHitReaction = false;
    RefreshCombatPoseTick();
}

void AVortexCofferM25::OnRep_Death()
{
    if (!Dead()) return;
    if (GetNetMode() != NM_DedicatedServer && DeathSound)
        UGameplayStatics::PlaySoundAtLocation(this, DeathSound,
            GetMesh()->GetSocketLocation(TEXT("body_05")), 1.f, 1.f, 0.f, OneShotAttenuation(1800.f));
    CorpseRagdoll->TryStartSoftDeath(GetMesh());
    bHitReaction = false;
    CombatTarget.Reset();
    if (Bite) Bite->Interrupt();
    if (Magic) Magic->Interrupt();
    if (BackElectric) BackElectric->StopDischarges();
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RefreshCombatPoseTick();
    // A corpse no longer needs authority socket updates for attacks/hit regions.
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    if (auto* AI = Cast<AMonsterAIController>(GetController()))
    {
        AI->StopMovement();
        AI->UpdateKnowledge();
    }
}

float AVortexCofferM25::TakeDamage(float Damage, const FDamageEvent& Event,
    AController* EventInstigator, AActor* Causer)
{
    if (!HasAuthority() || Dead() || !CanBeDamaged() || Damage <= 0.f) return 0.f;
    // Weakpoint crits are resolved by the common weapon/magic snapshot once.
    const float Reduced = CombatFormulaRuntime::MitigateMonster(this, Damage,
        Event.DamageTypeClass ? Event.DamageTypeClass->GetDefaultObject<UDamageType>() : nullptr, Causer);
    const float Applied = UDevelopmentTuningSubsystem::ShouldOneHitKill(this, EventInstigator, Causer)
        ? Health : FMath::Min(Health, FMath::Max(0.f, Reduced));
    if (Applied <= 0.f) return 0.f;
    Health -= Applied;
    const bool Killed = Health <= 0.f;
    if (Killed) { DeathStartedAt = CombatClock(); OnRep_Death(); SetLifeSpan(CorpseSeconds); }
    // The alive/dead state is committed before external damage delegates can re-enter.
    Super::TakeDamage(Applied, Event, EventInstigator, Causer);
    ForceNetUpdate();
    if (Killed)
    {
        ColdSteelSkills::NotifyKillByOwner(GetGameInstance(), EventInstigator, this);
        // Remote players own a server-side profile; do not gate rewards on a local controller.
        if (Cast<APlayerController>(EventInstigator))
            ColdSteelSkills::AwardKillByOwner(GetGameInstance(), EventInstigator, this, ExperienceReward);
    }
    else if (Combat && !Dead())
        Combat->ReceiveHit(Applied, EventInstigator ? EventInstigator->GetPawn().Get() : Cast<APawn>(Causer),
            MonsterToughness::FormOf(Event.DamageTypeClass));
    return Applied;
}
