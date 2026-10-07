#include "MantisM27AIReviewCommandlet.h"
#include "MantisM27Monster.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

int32 UMantisM27AIReviewCommandlet::Main(const FString& Params)
{
    const auto Settings = UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(true).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("M27RecoveryReview"), nullptr, true, ERHIFeatureLevel::Num, &Settings);
    if (!World) return 1;
    UClass* Type = LoadClass<AMantisM27Monster>(nullptr, TEXT("/Game/Monsters/MantisM27/BP_MantisM27.BP_MantisM27_C"));
    if (!Type) { World->DestroyWorld(false); return 1; }
    // No BeginPlay, profile or gameplay map: exercise actor/Combat entry points
    // and an isolated blackboard, without running a behavior tree or navmesh.
    FActorSpawnParameters Spawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Mantis = World->SpawnActor<AMantisM27Monster>(Type, FVector(0,0,96), FRotator::ZeroRotator, Spawn);
    auto* Victim = World->SpawnActor<ACharacter>(ACharacter::StaticClass(), FVector(110,0,96), FRotator::ZeroRotator, Spawn);
    if (!Mantis || !Victim) { World->DestroyWorld(false); return 1; }
    auto* Combat = Mantis->FindComponentByClass<UMonsterCombatComponent>();
    Combat->SetTarget(Victim);
    Mantis->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    Mantis->CloakMaterial = nullptr;
    Mantis->CloakHealFractionPerSecond = 0.f;
    int32 Passed = 0, Failed = 0;
    FString Report;
    const auto Check = [&](bool Result, const TCHAR* Name)
    {
        Result ? ++Passed : ++Failed;
        Report += FString::Printf(TEXT("%s %s\n"), Result ? TEXT("PASS") : TEXT("FAIL"), Name);
    };
    Mantis->SetCloaked(true);
    Mantis->CloakStartedAt = World->GetTimeSeconds()-4.;
    Mantis->Health = Mantis->MaxHealth*.79f;
    Mantis->TickCloak(0.f);
    Check(!Mantis->IsCloakRecoveryReady() && !Combat->CanAttack(Victim), TEXT("79 percent stays in recovery and cannot attack"));
    Mantis->Health = Mantis->MaxHealth*.8f;
    Mantis->CloakStartedAt = World->GetTimeSeconds()-2.;
    Mantis->TickCloak(0.f);
    Check(!Mantis->IsCloakRecoveryReady(), TEXT("minimum cloak duration remains effective"));
    Mantis->CloakStartedAt = World->GetTimeSeconds()-3.;
    Mantis->CloakGoal = FVector(700,0,0);
    Mantis->TickCloak(0.f);
    Check(Mantis->IsCloakRecoveryReady() && Mantis->CloakGoal.IsZero(), TEXT("exactly 80 percent commits ambush and clears orbit goal"));
    Mantis->Health = Mantis->MaxHealth*.6f;
    Mantis->TickCloak(0.f);
    Check(Mantis->IsCloakRecoveryReady(), TEXT("later damage cannot reopen recovery for the spent charge"));
    Check(Combat->CanAttack(Victim), TEXT("recovered cloaked actor permits close melee"));
    Check(Combat->TryAttack(Victim) && !Mantis->bCloaked && Mantis->State == ENurseState::Attack &&
        FMath::IsNearlyEqual(Mantis->ActiveAttackDamageScale,2.f), TEXT("actual melee entry breaks cloak and captures double damage"));
    Mantis->State = ENurseState::Idle;
    Check(Combat->TryAttack(Victim) && FMath::IsNearlyEqual(Mantis->ActiveAttackDamageScale,1.f), TEXT("following ordinary attack has no shadow multiplier"));
    Mantis->State = ENurseState::Idle;
    Mantis->SetCloaked(true);
    Mantis->TickCloak(0.f);
    Check(!Mantis->IsCloakRecoveryReady(), TEXT("a new cloak charge starts a fresh recovery"));
    Mantis->SetCloaked(false);
    Mantis->NextPounceAt = World->GetTimeSeconds()+100.;
    Check(Combat->CanAttack(Victim), TEXT("pounce cooldown does not prevent close melee fallback"));
    Victim->SetActorLocation(FVector(Mantis->PounceMinRange,0,96));
    Check(Mantis->MeleeStartDistance(Victim)>=Mantis->PounceMinRange && Combat->CanAttack(Victim) && !Mantis->WantsPounce(Victim),
        TEXT("melee overlaps pounce minimum and remains usable during pounce cooldown"));
    Victim->SetActorLocation(FVector(110,0,96));
    Mantis->State = ENurseState::Stagger;
    Check(!Combat->CanAttack(Victim), TEXT("control overrides recovered attack readiness"));
    Mantis->State = ENurseState::Dead;
    Check(!Combat->CanAttack(Victim), TEXT("death overrides recovered attack readiness"));

    // Reproduce the reported close-pursuit blockers without launching a map.
    Mantis->State = ENurseState::Chase;
    Victim->SetActorLocation(FVector(Mantis->MeleeStartDistance(Victim)-1.f,0,96));
    Check(Combat->CanAttack(Victim) && !Mantis->WantsPounce(Victim), TEXT("capsule-surface melee entry takes priority during pounce cooldown"));
    Mantis->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    Check(!Combat->CanAttack(Victim), TEXT("close-range shortcut still rejects airborne melee"));
    Mantis->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    Mantis->State = ENurseState::Recovery;
    Combat->SetLocomotion(false);
    Check(Mantis->State == ENurseState::Recovery, TEXT("stationary recovery holds scythe guard instead of popping into idle"));
    Combat->SetLocomotion(true);
    Check(Mantis->State == ENurseState::Chase, TEXT("target leaving range can interrupt the guard with pursuit"));

    auto* AI = World->SpawnActor<AMonsterAIController>();
    auto* Tree = NewObject<UBehaviorTree>();
    AMonsterAIController::BuildTree(Tree);
    UBlackboardComponent* Blackboard = nullptr;
    if (AI && AI->UseBlackboard(Tree->BlackboardAsset, Blackboard))
    {
        AI->SetPawn(Mantis); // Knowledge fixture only; do not start OnPossess/BT.
        Mantis->bEncounterCloakUsed = true;
        Mantis->SetActorLocation(FVector(3000,0,96));
        Victim->SetActorLocation(FVector(3120,0,96));
        AI->RememberDamage(Victim);
        Check(!Blackboard->GetValueAsBool(TEXT("Returning")) && Blackboard->GetValueAsBool(TEXT("CanAttack")),
            TEXT("visible close target beyond home leash remains attackable"));
        Check(Blackboard->GetValueAsBool(TEXT("Visible")) == Mantis->HasAttackSight(Victim),
            TEXT("AI visibility and combat use the same sight segment"));
        auto* Wall = World->SpawnActor<AActor>();
        auto* Box = NewObject<UBoxComponent>(Wall);
        Wall->SetRootComponent(Box);Box->SetBoxExtent(FVector(10,100,180));
        Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Block);
        Box->RegisterComponent();Wall->SetActorLocation(FVector(3060,0,96));
        AI->UpdateKnowledge();
        Check(!Mantis->HasAttackSight(Victim) && !Combat->CanAttack(Victim) && !Blackboard->GetValueAsBool(TEXT("CanAttack")),
            TEXT("close-range fix cannot attack through a blocking wall"));
        Wall->Destroy();
    }
    else Check(false,TEXT("isolated blackboard fixture initialized"));
    Report += FString::Printf(TEXT("RESULT passed=%d failed=%d\nScope: isolated actor/Combat transitions; not NavMesh or visual gameplay acceptance.\n"), Passed, Failed);
    const FString Directory = FPaths::ProjectDir()/TEXT("SourceAssets/MantisM27/ClawV12");
    IFileManager::Get().MakeDirectory(*Directory,true);
    FFileHelper::SaveStringToFile(Report, *(Directory/TEXT("ai_review.txt")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp,Display,TEXT("M27_AI_REVIEW passed=%d failed=%d"),Passed,Failed);
    World->DestroyWorld(false);
    return Failed ? 1 : 0;
}
