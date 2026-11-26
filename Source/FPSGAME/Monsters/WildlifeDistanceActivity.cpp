#include "WildlifeDistanceActivity.h"
#include "WildlifeSubsystem.h"
#include "WildlifeAnimal.h"
#include "WolfMonster.h"
#include "MonsterCombatComponent.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig.h"
#include "Perception/AISense.h"
#include "Net/UnrealNetwork.h"

UWildlifeDistanceActivity::UWildlifeDistanceActivity()
{
    SetIsReplicatedByDefault(true);
}

void UWildlifeDistanceActivity::BeginPlay()
{
    Super::BeginPlay();
    if (GetOwner()->HasAuthority())
    {
        const auto* Wolf = Cast<AWolfMonster>(GetOwner());
        if (GetOwner()->IsA<AColdSteelAnimal>() || (Wolf && Wolf->IsWildlifeWolf()))
            if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>())
                Wildlife->RegisterActivity(this);
    }
    else OnRep_Paused();
}

void UWildlifeDistanceActivity::EndPlay(const EEndPlayReason::Type Reason)
{
    if (GetOwner()->HasAuthority())
    {
        if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>())
            Wildlife->UnregisterActivity(this);
        if (bApplied) ResumeAI();
    }
    Super::EndPlay(Reason);
}

void UWildlifeDistanceActivity::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UWildlifeDistanceActivity, bDistancePaused);
}

void UWildlifeDistanceActivity::SetDistancePaused(bool bPause)
{
    if (bDistancePaused == bPause || bLeftForDeath) return;
    bDistancePaused = bPause;
    ApplyPause(bPause);
    GetOwner()->ForceNetUpdate();
}

void UWildlifeDistanceActivity::LeaveForDeath()
{
    if (bLeftForDeath) return;
    bLeftForDeath = true;
    ApplyPause(false);
    if (GetOwner()->HasAuthority())
    {
        bDistancePaused = false;
        if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>())
            Wildlife->UnregisterActivity(this);
    }
}

void UWildlifeDistanceActivity::OnRep_Paused()
{
    if (HasBegunPlay()) ApplyPause(bDistancePaused && !bLeftForDeath);
}

void UWildlifeDistanceActivity::ApplyPause(bool bPause)
{
    if (bApplied == bPause) return;
    bApplied = bPause;
    auto* Animal = CastChecked<ACharacter>(GetOwner());
    auto* Move = Animal->GetCharacterMovement();
    auto* Mesh = Animal->GetMesh();
    if (bPause)
    {
        bRestoreActorTick = Animal->IsActorTickEnabled();
        bRestoreMovementTick = Move->IsComponentTickEnabled();
        bRestoreAnimation = !Mesh->bPauseAnims;
        Animal->SetActorTickEnabled(false);
        if (Animal->HasAuthority()) PauseAI();
        // Combat knockback and pulls sweep the root independently of movement Tick.
        auto* Combat = Animal->FindComponentByClass<UMonsterCombatComponent>();
        if (Combat && Combat->IsComponentTickEnabled())
        {
            PausedCombatTick = Combat;
            Combat->SetComponentTickEnabled(false);
        }
        Animal->ConsumeMovementInputVector();
        Move->StopMovementImmediately();
        Move->ClearAccumulatedForces();
        // Preserve the movement mode, including flight. Simulated proxies must
        // also stop ticking movement or they can continue falling/extrapolating.
        Move->SetComponentTickEnabled(false);
        Mesh->bPauseAnims = true;
    }
    else
    {
        if (bRestoreAnimation) Mesh->bPauseAnims = false;
        if (bRestoreMovementTick) Move->SetComponentTickEnabled(true);
        if (auto* Combat = PausedCombatTick.Get()) Combat->SetComponentTickEnabled(true);
        PausedCombatTick.Reset();
        if (bRestoreActorTick) Animal->SetActorTickEnabled(true);
        if (Animal->HasAuthority())
        {
            if (auto* WildlifeAnimal = Cast<AColdSteelAnimal>(Animal)) WildlifeAnimal->ResumeWildlifeStateClock();
            if (auto* Wolf = Cast<AWolfMonster>(Animal)) Wolf->ResumeWildlifeStateClock();
            ResumeAI();
        }
    }
}

void UWildlifeDistanceActivity::PauseAI()
{
    auto* Character = CastChecked<ACharacter>(GetOwner());
    auto* AI = Cast<AAIController>(Character->GetController());
    PausedController = AI;
    Listener = AI ? AI->GetPerceptionComponent() : Character->FindComponentByClass<UAIPerceptionComponent>();
    if (auto* Senses = Listener.Get())
    {
        for (auto It = Senses->GetSensesConfigIterator(); It; ++It)
        {
            if (!*It) continue;
            const auto Sense = (*It)->GetSenseImplementation();
            if (Senses->IsSenseEnabled(Sense))
            {
                PausedSenses.Add(Sense);
                Senses->SetSenseEnabled(Sense, false);
            }
        }
    }
    if (!AI) return;
    auto* Brain = AI->GetBrainComponent();
    bResumeBrain = Brain && Brain->IsRunning() && !Brain->IsPaused();
    if (bResumeBrain) Brain->PauseLogic(TEXT("Wildlife outside player range"));
    AI->StopMovement();
    bRestoreControllerTick = AI->IsActorTickEnabled();
    AI->SetActorTickEnabled(false);
}

void UWildlifeDistanceActivity::ResumeAI()
{
    if (auto* Senses = Listener.Get())
        for (const auto& Sense : PausedSenses) Senses->SetSenseEnabled(Sense, true);
    Listener.Reset();
    PausedSenses.Reset();
    if (auto* AI = PausedController.Get())
    {
        if (bRestoreControllerTick) AI->SetActorTickEnabled(true);
        auto* Brain = AI->GetBrainComponent();
        if (bResumeBrain && Brain && Brain->IsPaused())
            Brain->ResumeLogic(TEXT("Wildlife activity resumed"));
    }
    PausedController.Reset();
}
