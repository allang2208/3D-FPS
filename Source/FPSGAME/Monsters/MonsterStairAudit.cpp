#include "MonsterStairAudit.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "NurseZombie.h"
#include "HandBrainMonster.h"
#include "PoisonMaggotMonster.h"
#include "BrainComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavMesh/RecastNavMesh.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

namespace MonsterStairs
{
    const FVector Origin(50000, 0, 10000);
    const TCHAR* Kinds[] = {TEXT("nurse"), TEXT("handbrain"), TEXT("maggot")};
    const TCHAR* Cases[] = {TEXT("step40"), TEXT("reject45"), TEXT("nav_stairs_up"), TEXT("nav_stairs_down"),
        TEXT("nav_obstacles"), TEXT("stop_on_step"), TEXT("low_ceiling"), TEXT("death_on_step"),
        TEXT("ramp"), TEXT("fall_onto_step"), TEXT("reject40_5"), TEXT("nav_dense_obstacles")};
    bool IsNavCase(int32 Index) { return (Index>=2 && Index<=4) || Index==11; }
    const TCHAR* Classes[] = {TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"),
        TEXT("/Game/Monsters/HandBrain/BP_HandBrain.BP_HandBrain_C"),
        TEXT("/Game/Monsters/PoisonMaggot/BP_PoisonMaggot.BP_PoisonMaggot_C")};
}

bool UMonsterStairAudit::ShouldCreateSubsystem(UObject* Outer) const
{
    const auto* World = Cast<UWorld>(Outer);
    return World && World->IsGameWorld() && FParse::Param(FCommandLine::Get(), TEXT("MonsterStairAudit"));
}

void UMonsterStairAudit::Check(bool Pass, const TCHAR* Name)
{
    ++Checks; if (!Pass) ++Failures;
    UE_LOG(LogTemp, Display, TEXT("MONSTER_STAIR %s %s/%s %s"), Pass?TEXT("PASS"):TEXT("FAIL"),
        MonsterStairs::Kinds[Species], MonsterStairs::Cases[Case], Name);
}

void UMonsterStairAudit::Setup()
{
    using namespace MonsterStairs;
    if (Monster) { if (Monster->GetController()) Monster->GetController()->Destroy(); Monster->Destroy(); }
    for (const auto& Actor : Fixture) if (IsValid(Actor)) Actor->Destroy();
    Fixture.Reset();
    auto Box = [&](FVector Center, FVector Size)
    {
        auto* Actor = GetWorld()->SpawnActor<AStaticMeshActor>();
        Actor->SetMobility(EComponentMobility::Movable);
        Actor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
        Actor->SetActorLocation(Origin + Center); Actor->SetActorScale3D(Size / 100.f);
        Actor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
        Actor->SetMobility(EComponentMobility::Static); Fixture.Add(Actor); return Actor;
    };
    Box(FVector(550,0,-10), FVector(1700,500,20));
    if (Case == 2 || Case == 3)
    {
        for (int32 I=0; I<6; ++I) Box(FVector(170+I*60,0,(I+1)*10), FVector(60,500,(I+1)*20));
        Box(FVector(940,0,60), FVector(1000,500,120));
    }
    else if (Case == 4)
    {
        for (int32 I=0; I<3; ++I) Box(FVector(220+I*360,0,10+I*5), FVector(140,500,20+I*10));
    }
    else if (Case == 11)
    {
        const float Heights[]={20,30,40,20,35,25,40,20};
        for (int32 I=0; I<8; ++I) Box(FVector(200+I*100,0,Heights[I]/2),FVector(60,500,Heights[I]));
    }
    else if (Case == 8)
    {
        auto* Ramp=Box(FVector(650,0,90),FVector(1000,500,20));
        Ramp->SetMobility(EComponentMobility::Movable); Ramp->SetActorRotation(FRotator(12,0,0));
        Ramp->SetMobility(EComponentMobility::Static);
    }
    else
    {
        float Height = Case == 1 ? 45.f : Case == 10 ? 40.5f : 40.f;
        Box(FVector(700,0,Height/2), FVector(1100,500,Height));
    }

    UClass* Class = LoadClass<ACharacter>(nullptr, Classes[Species]);
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    const auto* CDO = Class ? Cast<ACharacter>(Class->GetDefaultObject()) : nullptr;
    if (!CDO) { Check(false,TEXT("blueprint_loaded")); Finish(); return; }
    const float HalfHeight = CDO->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    Start = Origin + (Case == 3 ? FVector(690,0,HalfHeight+122.15f) : FVector(0,0,HalfHeight+2.15f));
    Goal = Origin + (Case == 3 ? FVector(0,0,2) : Case == 4 || Case == 11 ? FVector(1200,0,2) : FVector(680,0,Case == 2 ? 122 : 42));
    Monster = GetWorld()->SpawnActor<ACharacter>(Class, Start, FRotator(0,Case == 3 ? 180 : 0,0), Params);
    auto* AI = Cast<AMonsterAIController>(Monster->GetController());
    Check(AI && AI->Behavior, TEXT("shipped_controller_and_tree"));
    if (AI) { AI->SetDecisionEnabled(false); if (AI->BrainComponent) AI->BrainComponent->StopLogic(TEXT("Stair fixture owns movement requests")); }
    Monster->FindComponentByClass<UMonsterCombatComponent>()->SetLocomotion(true);
    auto* Move = Cast<UMonsterCharacterMovementComponent>(Monster->GetCharacterMovement());
    Check(Move && FMath::IsNearlyEqual(Move->MaxStepHeight,40.f) && FMath::IsNearlyEqual(Move->GetNavAgentPropertiesRef().AgentStepHeight,40.f), TEXT("movement_and_agent_40cm"));
    if (!Move) { Finish(); return; }
    Move->StopMovementImmediately(); Move->SetMovementMode(MOVE_Walking);
    BaselineMeshZ = Monster->GetMesh()->GetRelativeLocation().Z;
    Check(Monster->GetMesh()->GetSkeletalMeshAsset() && Monster->GetMesh()->GetAnimationMode()==EAnimationMode::AnimationSingleNode, TEXT("real_mesh_and_locomotion_animation"));
    if (Case == 6) Box(FVector(300,0,HalfHeight*2+15), FVector(700,500,20));

    if (!Camera) Camera = GetWorld()->SpawnActor<ACameraActor>();
    Camera->SetActorLocation(Origin+FVector(430,-1050,430));
    Camera->SetActorRotation((Origin+FVector(430,0,110)-Camera->GetActorLocation()).Rotation());
    Camera->GetCameraComponent()->FieldOfView = 65;
    GetWorld()->GetFirstPlayerController()->SetViewTarget(Camera);
    if (IsNavCase(Case))
    {
        auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
        Check(Nav!=nullptr, TEXT("navigation_system_available"));
        if (Nav) Nav->Build();
    }
    Time=0; Frame=0; MaxVisualSpeed=MaxHorizontalSpeed=MaxOffset=0;
    bAirborne=bStopped=bKilled=false; Stage=1;
}

void UMonsterStairAudit::Tick(float DT)
{
    Super::Tick(DT);
    using namespace MonsterStairs;
    // Inventory preview worlds also tick; only drive the possessed gameplay world.
    if (bFinished || !GetWorld()->HasBegunPlay() || !GetWorld()->GetFirstPlayerController() ||
        !GetWorld()->GetFirstPlayerController()->GetPawn() || GetWorld()->GetTimeSeconds()<4.f) return;
    if (Output.IsEmpty())
    {
        FString Run(TEXT("run")); FParse::Value(FCommandLine::Get(),TEXT("MonsterStairRun="),Run);
        int32 RequestedCase=0, RequestedSpecies=0;
        bSingleCase=FParse::Value(FCommandLine::Get(),TEXT("MonsterStairCase="),RequestedCase) &&
            FParse::Value(FCommandLine::Get(),TEXT("MonsterStairSpecies="),RequestedSpecies);
        if (bSingleCase) { Case=FMath::Clamp(RequestedCase,0,11); Species=FMath::Clamp(RequestedSpecies,0,2); }
        Output=FPaths::ProjectSavedDir()/TEXT("MonsterStairs")/Run;
        IFileManager::Get().MakeDirectory(*Output,true);
        Samples=TEXT("species,case,frame,dt,x,capsule_z,mesh_z,offset,grounded\n");
        for (TActorIterator<ACharacter> It(GetWorld()); It; ++It)
        {
            if (auto* AI=Cast<AMonsterAIController>(It->GetController())) { AI->SetDecisionEnabled(false); if(AI->BrainComponent)AI->BrainComponent->StopLogic(TEXT("Isolated stair audit")); }
        }
    }
    if (Stage==0) { Setup(); return; }
    if (!IsValid(Monster)) { Check(false,TEXT("monster_remains_valid")); Finish(); return; }
    auto* Move=CastChecked<UMonsterCharacterMovementComponent>(Monster->GetCharacterMovement());
    auto* AI=CastChecked<AMonsterAIController>(Monster->GetController());
    Time+=DT;
    if (Stage==1)
    {
        if (Time<1.5f) return;
        if (IsNavCase(Case))
        {
            auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
            if (UNavigationSystemV1::IsNavigationBeingBuiltOrLocked(this) && Time<18.f) return;
            const ANavigationData* Data=Nav->GetNavDataForProps(Monster->GetNavAgentPropertiesRef(),Monster->GetActorLocation());
            auto* Recast=Cast<ARecastNavMesh>(Data);
            Check(Recast && FMath::IsNearlyEqual(Recast->GetAgentMaxStepHeight(ENavigationDataResolution::Default),40.f),TEXT("selected_navmesh_step_40cm"));
            auto* Path=UNavigationSystemV1::FindPathToLocationSynchronously(this,Monster->GetActorLocation(),Goal,AI);
            bool Valid=Path && Path->IsValid() && !Path->IsPartial();
            Check(Valid,TEXT("complete_navigation_path"));
            UE_LOG(LogTemp,Display,TEXT("MONSTER_STAIR_PATH %s/%s nav=%s points=%d"),Kinds[Species],Cases[Case],*GetNameSafe(Data),Path?Path->PathPoints.Num():0);
            Check(AI->MoveToLocation(Goal,8,false,true,true,false,nullptr,false)!=EPathFollowingRequestResult::Failed,TEXT("path_following_started"));
        }
        if (Case==9)
        {
            Monster->SetActorLocation(Origin+FVector(450,0,Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+220),false,nullptr,ETeleportType::TeleportPhysics);
            Move->SetMovementMode(MOVE_Falling); Move->OnTeleported();
        }
        PreviousCapsule=Monster->GetActorLocation(); PreviousMesh=Monster->GetMesh()->GetComponentLocation();
        Start=PreviousCapsule; Stage=2; Time=0; return;
    }

    const FVector Capsule=Monster->GetActorLocation(), Mesh=Monster->GetMesh()->GetComponentLocation();
    const float Offset=Move->GetMeshStairOffset();
    Samples+=FString::Printf(TEXT("%s,%s,%d,%.6f,%.4f,%.4f,%.4f,%.4f,%d\n"),Kinds[Species],Cases[Case],Frame,DT,
        Capsule.X-Origin.X,Capsule.Z-Origin.Z,Mesh.Z-Origin.Z,Offset,Move->IsMovingOnGround());
    if (!bKilled)
    {
        MaxVisualSpeed=FMath::Max(MaxVisualSpeed,float(FMath::Abs(Mesh.Z-PreviousMesh.Z))/DT);
        MaxHorizontalSpeed=FMath::Max(MaxHorizontalSpeed,float(FVector::Dist2D(Capsule,PreviousCapsule))/DT);
        MaxOffset=FMath::Max(MaxOffset,FMath::Abs(Offset));
        bAirborne|=!Move->IsMovingOnGround();
    }
    PreviousCapsule=Capsule; PreviousMesh=Mesh;
    if (IsNavCase(Case) && Frame%FMath::Max(1,FMath::RoundToInt(.1f/DT))==0 && Time<13.f)
        FScreenshotRequest::RequestScreenshot(Output/FString::Printf(TEXT("%s_%s_%04d.png"),Kinds[Species],Cases[Case],Frame),false,false);
    ++Frame;

    if (Case==5 && !bStopped && Offset<-.5f) { bStopped=true; Time=0; Move->StopMovementImmediately(); }
    if (Case==7 && !bKilled && Offset<-.5f)
    {
        bKilled=true; DeathOffset=Offset; Time=0;
        UGameplayStatics::ApplyDamage(Monster,100000,nullptr,nullptr,nullptr);
        Check(Monster->FindComponentByClass<UMonsterCombatComponent>()->IsDead(),TEXT("death_during_step"));
        Check(Monster->GetMesh()->GetComponentLocation().Equals(Mesh,.01f),TEXT("death_keeps_visible_pose"));
    }
    if (bKilled)
    {
        if (Time>3.f)
        {
            Check(Monster->GetMesh()->IsSimulatingPhysics(),TEXT("ragdoll_takes_ownership"));
            Check(FMath::IsNearlyEqual(Move->GetMeshStairOffset(),DeathOffset,.01f),TEXT("no_corpse_offset_updates"));
            FinishCase();
        }
        return;
    }
    const bool Navigation=IsNavCase(Case);
    const float Duration=Navigation?float(FVector::Dist2D(Start,Goal))/Move->MaxWalkSpeed+3.f:Case==1||Case==6||Case>=9?4.f:8.f;
    if (bStopped ? Time>1.f : Time>Duration) { FinishCase(); return; }
    if (!Navigation && !bStopped && Case!=9) Monster->AddMovementInput(FVector::ForwardVector,1,true);
}

void UMonsterStairAudit::FinishCase()
{
    auto* Move=CastChecked<UMonsterCharacterMovementComponent>(Monster->GetCharacterMovement());
    const FVector End=Monster->GetActorLocation();
    if (Case!=9) Check(MaxVisualSpeed<=Move->StairVisualSpeed+2.f,TEXT("mesh_height_speed_bounded"));
    Check(MaxHorizontalSpeed<=Move->MaxWalkSpeed+2.f,TEXT("no_horizontal_teleport"));
    Check(MaxOffset<=40.5f,TEXT("repeated_steps_no_offset_growth"));
    if (Case!=7 && Case!=9) Check(!bAirborne,TEXT("walk_without_jump_or_fall"));
    if (MonsterStairs::IsNavCase(Case)) Check(FVector::Dist2D(End,Goal)<30.f,TEXT("path_following_reaches_goal"));
    if (Case==0) Check(End.X-Start.X>350 && End.Z-Start.Z>39,TEXT("walks_up_40cm"));
    if (Case==1 || Case==6 || Case==10) Check(End.X-Start.X<155 && End.Z-Start.Z<20,TEXT("blocked_by_height_or_headroom"));
    if (Case==8) Check(End.X-Start.X>350 && End.Z-Start.Z>40,TEXT("walkable_ramp_preserved"));
    if (Case==9) Check(bAirborne && Move->IsMovingOnGround() && FMath::IsNearlyEqual(float(End.Z-MonsterStairs::Origin.Z-Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),42.f,1.f),TEXT("fall_lands_on_step"));
    if (Case==5) Check(bStopped && Move->Velocity.IsNearlyZero(),TEXT("stops_during_active_step"));
    if (Case==7) Check(bKilled,TEXT("death_case_exercised"));
    if (Case==5 || MonsterStairs::IsNavCase(Case))
        Check(FMath::Abs(Move->GetMeshStairOffset())<.01f && FMath::IsNearlyEqual(Monster->GetMesh()->GetRelativeLocation().Z,BaselineMeshZ,.02f),TEXT("mesh_rest_offset_restored"));
    UE_LOG(LogTemp,Display,TEXT("MONSTER_STAIR_METRIC %s/%s visual_speed=%.3f horizontal_speed=%.3f max_offset=%.3f end=%s"),
        MonsterStairs::Kinds[Species],MonsterStairs::Cases[Case],MaxVisualSpeed,MaxHorizontalSpeed,MaxOffset,*End.ToString());
    ++CompletedCases;
    if (bSingleCase) { Finish(); return; }
    Stage=0; ++Case; if (Case==12) { Case=0; ++Species; }
    if (Species==3) Finish();
}

void UMonsterStairAudit::Finish()
{
    bFinished=true;
    FFileHelper::SaveStringToFile(Samples,*(Output/TEXT("trajectory.csv")));
    UE_LOG(LogTemp,Display,TEXT("MONSTER_STAIR_RESULT cases=%d checks=%d failures=%d"),CompletedCases,Checks,Failures);
    FPlatformMisc::RequestExitWithStatus(false,Failures?1:0);
}
