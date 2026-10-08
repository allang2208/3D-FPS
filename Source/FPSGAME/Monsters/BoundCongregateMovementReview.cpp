#include "BoundCongregate.h"
#include "BoundCongregateAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

// Opt-in diagnosis requested for the ineffective movement tuning. Exercise
// the saved Blueprint, real capsule movement and real animation time. No
// gameplay map, player save, render, cloth simulation or AI encounter.
int32 ReviewBoundCongregateMovementSpeed()
{
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("CongregateMovementReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 1;
    UClass* Type=LoadClass<ABoundCongregate>(nullptr,TEXT("/Game/Monsters/BoundCongregate/BP_BoundCongregate.BP_BoundCongregate_C"));
    if(!Type){World->DestroyWorld(false);return 1;}
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AActor* Floor=World->SpawnActor<AActor>(AActor::StaticClass(),FVector(0,0,-50),FRotator::ZeroRotator,Spawn);
    auto* Box=NewObject<UBoxComponent>(Floor);Floor->SetRootComponent(Box);Box->SetBoxExtent(FVector(5000,5000,50));
    Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();Box->SetWorldLocation(FVector(0,0,-50));
    FString Report=TEXT("Scope: cold Blueprint spawn + BeginPlay, direct path-velocity requests on a flat floor, actual animation clock. 60 Hz; no AI encounter or rendering.\n");
    FString Samples=TEXT("case,time,x,speed,animation_rate\n");
    bool Passed=true;
    for(int32 Case=0;Case<3;++Case)
    {
        Spawn.bDeferConstruction=true;
        auto* Monster=World->SpawnActor<ABoundCongregate>(Type,FVector(0,Case*900,225),FRotator::ZeroRotator,Spawn);
        Monster->AutoPossessAI=EAutoPossessAI::Disabled;
        Monster->FinishSpawning(FTransform(FRotator::ZeroRotator,FVector(0,Case*900,225)));
        Monster->DispatchBeginPlay();
        auto* Move=Monster->GetCharacterMovement();auto* Mesh=Monster->GetMesh();
        Report+=FString::Printf(TEXT("spawn case=%d WalkSpeed=%.3f MaxWalkSpeed=%.3f MaxAcceleration=%.3f AnimationWalkSpeed=%.3f WhipCooldown=%.3f\n"),
            Case,Monster->WalkSpeed,Move->MaxWalkSpeed,Move->MaxAcceleration,Monster->AnimationWalkSpeed,Monster->TentacleCooldown);
        if(Case<2)
        {
            Monster->WalkSpeed=Case==0?60.f:120.f;Move->MaxWalkSpeed=Monster->WalkSpeed;
            Move->MaxAcceleration=150.f;Move->BrakingDecelerationWalking=240.f;
        }
        Move->bRunPhysicsWithNoController=true;Move->SetMovementMode(MOVE_Walking);
        Mesh->bDisableClothSimulation=true;Mesh->bEnableUpdateRateOptimizations=false;Mesh->InitAnim(true);
        auto* Anim=Cast<UBoundCongregateAnimInstance>(Mesh->GetAnimInstance());
        if(!Anim||!Monster->MoveClip){World->DestroyWorld(false);return 1;}
        constexpr float Dt=1.f/60.f;
        double LateSpeed=0,LateRate=0;int32 LateCount=0;
        for(int32 Frame=0;Frame<210;++Frame)
        {
            ++GFrameCounter;
            Move->RequestDirectMove(FVector(Monster->WalkSpeed,0,0),true);
            Move->TickComponent(Dt,LEVELTICK_All,&Move->PrimaryComponentTick);
            const auto* PreviousClip=Anim->ActiveClip.Get();const float PreviousTime=Anim->ClipTime;
            Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();
            const double Speed=Monster->GetVelocity().Size2D();double Rate=0;
            if(PreviousClip==Monster->MoveClip&&Anim->ActiveClip==Monster->MoveClip)
            {
                double Step=Anim->ClipTime-PreviousTime;
                if(Step<0)Step+=Monster->MoveClip->GetPlayLength();
                Rate=Step/Dt;
            }
            if(Frame>=120){LateSpeed+=Speed;LateRate+=Rate;++LateCount;}
            if((Frame+1)%15==0)Samples+=FString::Printf(TEXT("%d,%.3f,%.3f,%.3f,%.3f\n"),Case,(Frame+1)*Dt,Monster->GetActorLocation().X,Speed,Rate);
        }
        LateSpeed/=LateCount;LateRate/=LateCount;
        const double ExpectedRate=Monster->WalkSpeed/FMath::Max(1.f,Monster->AnimationWalkSpeed);
        const bool Valid=FMath::Abs(LateSpeed-Monster->WalkSpeed)<1.&&FMath::Abs(LateRate-ExpectedRate)<.03;
        Passed&=Valid;
        Report+=FString::Printf(TEXT("steady case=%d measured_speed=%.3f measured_clip_rate=%.3f expected_rate=%.3f pass=%d\n"),Case,LateSpeed,LateRate,ExpectedRate,Valid);
        Monster->Destroy();
    }
    World->DestroyWorld(false);
    FFileHelper::SaveStringToFile(Report,*(FPaths::ProjectSavedDir()/TEXT("bound-movement-runtime-20261008.txt")));
    FFileHelper::SaveStringToFile(Samples,*(FPaths::ProjectSavedDir()/TEXT("bound-movement-runtime-20261008.csv")));
    UE_LOG(LogTemp,Display,TEXT("BOUND_MOVEMENT_REVIEW pass=%d\n%s"),Passed,*Report);
    return Passed?0:1;
}
