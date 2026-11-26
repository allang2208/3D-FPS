#include "WildlifeAnimal.h"
#include "HillsWildlifeAudio.h"
#include "WildlifeDistanceActivity.h"
#include "WildlifeSubsystem.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "TimerManager.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Hearing.h"
#include "QuadrupedAnimationTemplate.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterCoreStats.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/EnemyAttackDamage.h"
#include "FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"


bool AColdSteelAnimal::PlayerThreat(APawn*& OutThreat, float& OutDistance) const
{
    OutThreat = nullptr;
    OutDistance = MAX_flt;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        APawn* Player = It->IsValid() ? It->Get()->GetPawn() : nullptr;
        if (!IsValid(Player)) continue;
        const auto* Vitals = Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if (Vitals && Vitals->IsDead()) continue;
        const float Distance = FVector::Dist2D(Player->GetActorLocation(), GetActorLocation());
        if (Distance < OutDistance) { OutDistance = Distance; OutThreat = Player; }
    }
    return OutThreat != nullptr;
}

void AColdSteelAnimal::PickWanderPoint()
{
    const float Angle = Random.FRandRange(0.f, 2.f * PI);
    const float Distance = Random.FRandRange(250.f, FMath::Max(300.f, Row->HomeRadius * .55f));
    Goal = Home + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f) * Distance;
    FHitResult Ground;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WildlifeGround), false, this);
    const FVector From = Goal + FVector(0.f, 0.f, 300.f);
    if (GetWorld()->LineTraceSingleByChannel(Ground, From, From - FVector(0.f, 0.f, 900.f), ECC_WorldStatic, Query))
        Goal = Ground.ImpactPoint;
}

void AColdSteelAnimal::PickFleePoint(APawn* Threat)
{
    const FVector Away = Threat ? (GetActorLocation() - Threat->GetActorLocation()).GetSafeNormal2D() : GetActorForwardVector();
    const float Jitter = Random.FRandRange(-.6f, .6f);
    const FVector Dir = Away.RotateAngleAxis(Jitter * 90.f, FVector::UpVector);
    Goal = GetActorLocation() + Dir * Row->FleeRadius * 1.8f;
    FHitResult Ground;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WildlifeFlee), false, this);
    const FVector From = Goal + FVector(0.f, 0.f, 300.f);
    if (GetWorld()->LineTraceSingleByChannel(Ground, From, From - FVector(0.f, 0.f, 1200.f), ECC_WorldStatic, Query))
        Goal = Ground.ImpactPoint;
}

void AColdSteelAnimal::SteerTo(const FVector& Destination, float Speed, float ArriveRadius)
{
    FVector Delta = Destination - GetActorLocation();
    Delta.Z = 0.f;
    auto* Move = GetCharacterMovement();
    if (!Move) return;
    Move->MaxWalkSpeed = Speed;
    if (Delta.SizeSquared2D() <= FMath::Square(ArriveRadius)) return;
    AddMovementInput(Delta.GetSafeNormal(), 1.f, true);
}

bool AColdSteelAnimal::BlockedTooLong(float DeltaSeconds)
{
    const float Speed = GetVelocity().Size2D();
    if (Speed > 30.f)
    {
        StuckSeconds = 0.f;
        LastProgress = GetActorLocation();
        return false;
    }
    StuckSeconds += DeltaSeconds;
    return StuckSeconds > 1.5f;
}

