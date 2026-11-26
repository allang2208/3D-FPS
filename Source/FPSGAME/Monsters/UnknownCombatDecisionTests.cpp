#if WITH_DEV_AUTOMATION_TESTS
#include "UnknownHumanoid.h"
#include "MonsterAIController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/BoxComponent.h"
#if WITH_EDITOR
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#endif
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Misc/AutomationTest.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnknownCombatDecisionTest,"FPSGAME.AI.Unknown.CombatDecisions",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)

bool FUnknownCombatDecisionTest::RunTest(const FString&)
{
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("UnknownCombatDecisions"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!TestNotNull(TEXT("transient physics world"),World))return false;
    ON_SCOPE_EXIT{World->DestroyWorld(false);};
    auto* Monster=World->SpawnActor<AUnknownHumanoid>();
    auto* AI=World->SpawnActor<AMonsterAIController>();
    auto SpawnPlayer=[&](FVector At)
    {
        auto* PC=World->SpawnActor<APlayerController>();
        auto* P=World->SpawnActor<ACharacter>(At,FRotator::ZeroRotator);
        auto* PS=World->SpawnActor<APlayerState>();
        PS->SetOwner(PC); PC->SetPlayerState(PS);
        PC->SetAsLocalPlayerController();
        World->AddController(PC); PC->SetPawn(P); P->PossessedBy(PC);
        P->SetPlayerState(PS);
        return P;
    };
    auto* Far=SpawnPlayer(FVector(1100,300,95));
    auto* Close=SpawnPlayer(FVector(900,0,95));
    auto* Wall=World->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Wall);
    Wall->AddInstanceComponent(Box); Wall->SetRootComponent(Box);
    Box->SetBoxExtent(FVector(25,65,240)); Box->SetCollisionProfileName(TEXT("BlockAll")); Box->RegisterComponent();
    Wall->SetActorLocation(FVector(400,0,120));
    AI->SetPawn(Monster);
    Monster->SetActorLocation(FVector(0,0,95));
    Monster->Home=Monster->GetActorLocation();
    Monster->Loadout.Role=EUnknownRole::Gun;
    Monster->AttackRange=1800; Monster->PreferredRange=950;
    Monster->Capacity=20; Monster->Magazine=8;
    Monster->MaxHealth=Monster->Health=100;
    Monster->TacticalTarget=Far;
    auto Observe=[&](bool MaySwitch)
    {
        Monster->NextSightSample=-1;
        return Monster->ConsiderVisibleOpponent(*AI,Far,true,MaySwitch);
    };
    TestTrue(TEXT("both simulated opponents have human player states"),Far->IsPlayerControlled() && Close->IsPlayerControlled());
    TestTrue(TEXT("primary player is visible around the wall"),AI->CanSeePlayer(Far,true));
    TestFalse(TEXT("wall hides the second player"),AI->CanSeePlayer(Close,true));
    TestTrue(TEXT("a hidden opponent cannot steal focus"),Observe(true)==Far);
    TestFalse(TEXT("a hidden opponent does not form a spell cluster"),Monster->HasVisibleCluster(Far,450));
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    TestTrue(TEXT("comparable exposed opponents preserve focus"),Observe(true)==Far);
    TestTrue(TEXT("two visible nearby opponents form a spell cluster"),Monster->HasVisibleCluster(Far,450));
    Close->SetActorLocation(FVector(300,160,95));
    TestTrue(TEXT("encounter lock preserves its designated opponent"),Observe(false)==Far);
    TestTrue(TEXT("a much closer visible opponent can take focus"),Observe(true)==Close);
    TestTrue(TEXT("target switch cooldown prevents immediate reversal"),Observe(true)==Far);

    Close->SetActorLocation(FVector(900,0,95));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Monster->OtherOpponents.Reset(); Monster->TacticalTarget=Close; Monster->LastSeenTime=Monster->ServerTime();
    Monster->bHasCover=true; Monster->Position=EUnknownPosition::SeekCover;
    Monster->CoverPoint=Monster->GetNavAgentLocation(); Monster->FiringPoint=Monster->CoverPoint+FVector(0,200,0);
    Monster->PlannedTarget=Close->GetNavAgentLocation(); Monster->PositionUntil=10;
    TestFalse(TEXT("does not stop for partial reload while crossing to cover"),Monster->CanActOutOfSight());
    Monster->UpdateTactics(Close,false,Monster->PlannedTarget);
    TestTrue(TEXT("physical wall protects the arrived hiding position"),Monster->Position==EUnknownPosition::Sheltered);
    TestTrue(TEXT("partial magazine can be topped up while sheltered"),Monster->CanActOutOfSight());
    Monster->Sheet=NewObject<UColdSteelStatusModel>(NewObject<UGameInstance>(GEngine));
    Monster->ReloadSeconds=3; Monster->TacticalReloadSeconds=1.5f;
    TestTrue(TEXT("behavior-tree attack entry can start the reload without sight"),Monster->StartAttack(Close));
    TestTrue(TEXT("nonempty magazine uses the normal weapon reload time"),
        Monster->Motion.Action==EUnknownAction::Reload && Monster->Motion.Duration==1.5f);
    Monster->Motion.Started-=2;
    Monster->Tick(.01f);
    TestTrue(TEXT("a completed tactical reload refills the weapon to capacity"),
        Monster->Magazine==20 && !Monster->Busy());
    TestFalse(TEXT("full magazine cannot start another reload"),Monster->WantsReload());

    Monster->PositionUntil=-1;
    Monster->UpdateTactics(Close,false,Monster->PlannedTarget);
    TestTrue(TEXT("reload complete and shelter window elapsed allows a peek"),Monster->Position==EUnknownPosition::MoveToPeek);
    Monster->Position=EUnknownPosition::Sheltered; Monster->PositionUntil=10;
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Monster->UpdateTactics(Close,true,Monster->PlannedTarget);
    TestTrue(TEXT("destroyed cover is abandoned and temporarily avoided"),
        Monster->Position==EUnknownPosition::Open && !Monster->bHasCover && Monster->AvoidCoverUntil>Monster->ServerTime());
    Monster->bHasCover=true; Monster->Position=EUnknownPosition::Peeking;
    Monster->LastSeenTime=Monster->ServerTime()-4;
    Monster->UpdateTactics(Close,false,Monster->PlannedTarget);
    TestTrue(TEXT("prolonged sight loss exits the old cover loop"),!Monster->bHasCover && Monster->Position==EUnknownPosition::Open);

    const FVector Feet=Monster->GetNavAgentLocation();
    Monster->Position=EUnknownPosition::Adjust;
    Monster->FiringPoint=Feet+FVector(0,0,250);
    Monster->PositionUntil=-1;
    Monster->UpdateTactics(Close,true,Close->GetNavAgentLocation());
    TestTrue(TEXT("same XY on another floor cannot finish a firing-position move even after the old timer expires"),
        Monster->Position==EUnknownPosition::Adjust);
    Monster->FiringPoint=Feet;
    Monster->UpdateTactics(Close,true,Close->GetNavAgentLocation());
    TestTrue(TEXT("same-floor arrival with an open lane finishes the move"),Monster->Position==EUnknownPosition::Open);

    Monster->NextReposition=Monster->ServerTime()+10.;
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Wall->SetActorLocation(FVector(400,0,108)); Box->SetBoxExtent(FVector(25,65,27));
    Monster->UpdateTactics(Close,true,Close->GetNavAgentLocation());
    TestFalse(TEXT("perception visibility does not make a blocked gun-height lane usable"),Monster->bHasFiringLane);
    Monster->Position=EUnknownPosition::MoveToPeek; Monster->bHasCover=true; Monster->FiringPoint=Feet;
    Monster->UpdateTactics(Close,true,Close->GetNavAgentLocation());
    TestTrue(TEXT("a blocked peek is abandoned instead of holding fire against the obstacle"),
        Monster->Position==EUnknownPosition::Open && !Monster->bHasCover);
    Monster->Loadout.Role=EUnknownRole::Magic;
    TestFalse(TEXT("a solid obstacle also blocks the spell lane"),
        Monster->HasFiringLane(Monster->AimOrigin(),*Close,Close->GetActorLocation()));
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    TestTrue(TEXT("opening the lane allows the spell aim position"),
        Monster->HasFiringLane(Monster->AimOrigin(),*Close,Close->GetActorLocation()));
    Box->SetBoxExtent(FVector(25,65,240));

    Monster->Loadout.Role=EUnknownRole::Melee;
    Monster->AttackRange=180; Monster->PreferredRange=115; Monster->AttackSeconds=.65f;
    Monster->Stamina=100; Monster->StaminaCost=10;
    Close->SetActorLocation(FVector(265,0,95));
    TestFalse(TEXT("stationary short weapon cannot reach a distant capsule"),Monster->CanAttack(Close));
    Monster->AttackRange=270;
    TestTrue(TEXT("longer weapon starts from the same standing position"),Monster->CanAttack(Close));
    Monster->AttackRange=180;
    Monster->GetCharacterMovement()->Velocity=FVector(300,0,0);
    TestTrue(TEXT("advancing hunter can start before reaching stationary range"),Monster->CanAttack(Close));
    Close->GetCharacterMovement()->Velocity=FVector(300,0,0);
    TestFalse(TEXT("matching retreat speed cancels closing-distance lead"),Monster->CanAttack(Close));
    Close->GetCharacterMovement()->Velocity=FVector(0,600,0);
    TestFalse(TEXT("a lateral dodge leaves the committed sweep"),Monster->CanAttack(Close));
    Close->GetCharacterMovement()->Velocity=FVector::ZeroVector;
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Wall->SetActorLocation(FVector(130,0,120));
    TestFalse(TEXT("a wall blocks the predicted windup"),Monster->CanAttack(Close));
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Monster->bSprintIntent=true;
    TestTrue(TEXT("starts a moving swing and spends stamina once"),Monster->StartAttack(Close) && Monster->Stamina==90);
    TestTrue(TEXT("only the committed opponent can be followed during a swing"),
        Monster->CanPursueDuringSwing(Close) && !Monster->CanPursueDuringSwing(Far) && Monster->bSprintIntent);
    TestFalse(TEXT("continued pursuit cannot restart a pending swing"),Monster->StartAttack(Close));
    Monster->SetAction(EUnknownAction::Stagger,.3f);
    TestFalse(TEXT("stagger cancels pursuit and pending melee contact"),Monster->CanPursueDuringSwing(Close) || Monster->bPendingContact);
    Monster->SetAction(EUnknownAction::Ready);
    Monster->Loadout.Role=EUnknownRole::Gun;
    Monster->Magazine=0;
    Monster->Tick(.01f);
    TestTrue(TEXT("an empty gun stays ranged and starts its full reload without a target"),
        Monster->IsRanged() && Monster->Motion.Action==EUnknownAction::Reload &&
        Monster->Motion.Duration==Monster->ReloadSeconds && Monster->Magazine==0);
    Monster->Motion.Started-=Monster->ReloadSeconds+.01f;
    Monster->Tick(.01f);
    TestTrue(TEXT("empty reload restores a full magazine"),Monster->Magazine==Monster->Capacity && !Monster->Busy());
    return true;
}
#if WITH_EDITOR
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnknownObstacleTravelTest,"FPSGAME.AI.Unknown.ObstacleTravel",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)

bool FUnknownObstacleTravelTest::RunTest(const FString&)
{
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("UnknownObstacleTravel"),nullptr,true,ERHIFeatureLevel::Num,&Init);
    if(!TestNotNull(TEXT("isolated navigation world"),World))return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT{GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    auto Box=[&](FVector Center,FVector Size,bool NavRelevant)
    {
        auto* Actor=World->SpawnActor<AStaticMeshActor>();
        Actor->SetMobility(EComponentMobility::Movable);
        auto* Mesh=Actor->GetStaticMeshComponent();
        Mesh->SetCanEverAffectNavigation(NavRelevant);
        Mesh->SetStaticMesh(Cube);
        Mesh->SetCollisionProfileName(TEXT("BlockAll"));
        Actor->SetActorLocation(Center);
        Actor->SetActorScale3D(Size/100.f);
        Actor->SetMobility(EComponentMobility::Static);
    };
    Box(FVector(0,0,-20),FVector(2600,2200,40),true);
    Box(FVector(0,0,120),FVector(110,650,240),true);
    FNavigationSystem::AddNavigationSystemToWorld(*World,FNavigationSystemRunMode::GameMode);
    if(!TestTrue(TEXT("navigation bounds built"),AMonsterAIController::BuildNavigationBounds(World,FVector(0,0,110),FVector(1350,1150,230))))return false;
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if(!Nav)return false;
    Nav->Tick(.033f); // Publish the new volume before synchronously building its tiles.
    Nav->Build();
    const FVector Start(-700,0,94),Goal(700,0,0);
    auto* Monster=World->SpawnActor<AUnknownHumanoid>(Start,FRotator::ZeroRotator);
    auto* AI=World->SpawnActor<AMonsterAIController>();
    if(!Monster || !AI || !Nav)return false;
    Monster->Home=Start;
    AI->SetPawn(Monster); Monster->PossessedBy(AI);
    auto* Follow=AI->GetPathFollowingComponent(); Follow->Initialize();
    auto* Move=Monster->GetCharacterMovement();
    Move->bRunPhysicsWithNoController=true; Move->MaxWalkSpeed=400.f;
    Move->SetMovementMode(MOVE_Walking);
    const auto& Agent=AI->GetNavAgentPropertiesRef();
    const auto* Data=Nav->GetNavDataForProps(Agent,Monster->GetNavAgentLocation());
    FNavLocation OnNav;
    if(!TestTrue(TEXT("human navigation exists under the actual pawn"),
        Data && Nav->ProjectPointToNavigation(Monster->GetNavAgentLocation(),OnNav,FVector(90,90,70),Data)))return false;

    auto Travel=[&](FVector End,bool& Detoured)
    {
        constexpr float Dt=1.f/30.f;
        const double InitialY=Monster->GetActorLocation().Y;
        for (int32 Frame=0;Frame<450;++Frame)
        {
            World->TimeSeconds+=Dt; World->DeltaTimeSeconds=Dt;
            Monster->Pursue(*AI,nullptr,End);
            Follow->TickComponent(Dt,LEVELTICK_All,nullptr);
            Move->TickComponent(Dt,LEVELTICK_All,nullptr);
            const FVector Feet=Monster->GetNavAgentLocation();
            Detoured|=FMath::Abs(Feet.Y-InitialY)>95.;
            if(FVector::Dist2D(Feet,End)<45.f && FMath::Abs(Feet.Z-End.Z)<45.f)return true;
        }
        AddInfo(FString::Printf(TEXT("final pawn feet %s goal %s requests %d failed %d"),
            *Monster->GetNavAgentLocation().ToString(),*End.ToString(),AI->NavigationRequests,AI->bNavigationFailed));
        return false;
    };
    Monster->Loadout.Role=EUnknownRole::Gun; Monster->Magazine=12;
    bool Detoured=false;
    TestTrue(TEXT("gunner walks around the baked wall to the remembered position"),Travel(Goal,Detoured) && Detoured);

    AI->StopMovement();
    Monster->SetActorLocation(FVector(-570,660,94),false,nullptr,ETeleportType::TeleportPhysics);
    Move->StopMovementImmediately(); Move->SetMovementMode(MOVE_Walking);
    World->TimeSeconds+=2.;
    // Collision added after the bake: the nominal route remains straight through this prop.
    Box(FVector(0,660,110),FVector(90,125,220),false);
    Monster->Loadout.Role=EUnknownRole::Magic; Detoured=false;
    TestTrue(TEXT("caster clears an unbaked obstacle with a physical side-step and resumes the goal"),
        Travel(FVector(570,660,0),Detoured) && Detoured);
    return true;
}
#endif
#endif
