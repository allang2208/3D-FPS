#include "HeQueAuditCommandlet.h"
#include "HeQueMonster.h"
#include "M14SoftBodyDeath.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Dungeons/FacilityHallEncounter.h"
#include "../Multiplayer/FPSStatusReplicationComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "UObject/UnrealType.h"

AHeQueAuditPawn::AHeQueAuditPawn(const FObjectInitializer& Init)
    :Super(Init.SetDefaultSubobjectClass<UFPSCharacterMovementComponent>(ACharacter::CharacterMovementComponentName))
{bReplicates=true;GetCharacterMovement()->bRunPhysicsWithNoController=true;}

int32 UHeQueAuditCommandlet::Main(const FString&)
{
    int32 Checks=0,Failures=0;
    auto Check=[&](bool Pass,const FString& Case)
    {++Checks;if(!Pass){++Failures;UE_LOG(LogTemp,Error,TEXT("[HeQueAudit] FAIL %s"),*Case);}};
    const FString BossPath=AFacilityHallEncounter::FinalBossClassPaths()[0];
    UClass* BossClass=LoadClass<AHeQueMonster>(nullptr,*BossPath);
    Check(BossClass!=nullptr,TEXT("final room resolves the saved HeQue class"));
    if(!BossClass)return 1;
    const auto* Boss=BossClass->GetDefaultObject<AHeQueMonster>();
    Check(Boss->FindComponentByClass<UFPSStatusReplicationComponent>()!=nullptr,TEXT("saved HeQue class inherits replicated combat status"));
    for(const TCHAR* Name:{TEXT("Health"),TEXT("MaxHealth"),TEXT("Sweep"),TEXT("Clamp"),TEXT("Rift"),TEXT("Psychic"),TEXT("JumpSlam"),TEXT("Reaction")})
    {
        const auto* Property=FindFProperty<FProperty>(BossClass,Name);
        Check(Property&&Property->HasAnyPropertyFlags(CPF_Net),FString(TEXT("replicated boss field: "))+Name);
    }
    for(const TCHAR* Name:{TEXT("VisualMesh"),TEXT("HitSurfacePhysics"),TEXT("IdleClip"),TEXT("MoveClip"),
        TEXT("TurnLeftClip"),TEXT("TurnRightClip"),TEXT("SweepClip"),TEXT("ClampClip"),TEXT("RiftClip"),TEXT("PsychicClip"),
        TEXT("JumpChargeClip"),TEXT("JumpAirClip"),TEXT("JumpDiveClip"),TEXT("JumpRecoverClip"),TEXT("AirClip"),TEXT("LandClip"),TEXT("GetUpClip"),TEXT("StunClip"),TEXT("DeathClip"),
        TEXT("PressureMesh"),TEXT("PressureMaterial"),TEXT("PsychicWaveMesh"),TEXT("PsychicWaveMaterial"),TEXT("PsychicFearViewMaterial"),
        TEXT("JumpWaveMesh"),TEXT("JumpWaveMaterial"),TEXT("JumpImpactMesh"),TEXT("JumpImpactMaterial"),TEXT("SweepSound"),TEXT("ClampSound"),TEXT("PsychicFearSound")})
    {
        const auto* Property=FindFProperty<FObjectPropertyBase>(BossClass,Name);
        Check(Property&&Property->GetObjectPropertyValue_InContainer(Boss)!=nullptr,FString(TEXT("saved asset: "))+Name);
    }
    Check(Boss->HitClips.Num()==4&&!Boss->HitClips.Contains(nullptr),TEXT("four directional hit clips"));
    Check(!Boss->SweepFrames.IsEmpty()&&!Boss->ClampFrames.IsEmpty(),TEXT("authored kick and clamp contact samples"));
    Check(FMath::IsNearlyEqual(Boss->JumpHeight,210.f),TEXT("saved jump height is 210cm"));
    Check(FMath::IsNearlyEqual(Boss->SweepPushDistance,1000.f),TEXT("saved kick distance is 10m"));
    Check(FMath::IsNearlyEqual(Boss->RiftRange,4800.f),TEXT("saved air cannon range is 48m"));
    Check(FMath::IsNearlyEqual(Boss->PsychicCooldown,30.f),TEXT("saved psychic cooldown is 30s"));
    Check(FMath::IsNearlyEqual(Boss->TurnSpeed,120.f),TEXT("saved turn rate is 120 degrees/s"));
    Check(Boss->HitSurfacePhysics&&Boss->HitSurfacePhysics->SkeletalBodySetups.ContainsByPredicate(
        [](const USkeletalBodySetup* Body){return Body&&Body->BoneName==TEXT("HQ_CoreSwing");}),TEXT("heart has an actual hit body"));
    const auto* Binding=Boss->VisualMesh?Cast<UMonsterSoftCorpseBinding>(Boss->VisualMesh->GetAssetUserDataOfClass(UMonsterSoftCorpseBinding::StaticClass())):nullptr;
    Check(Binding&&Binding->Data,TEXT("saved mesh retains its continuous soft-corpse binding"));

    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("HeQueAudit"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 2;
    auto Box=[World](FVector Center,FVector Extent)
    {
        auto* Actor=World->SpawnActor<AActor>();
        auto* Shape=NewObject<UBoxComponent>(Actor);Actor->SetRootComponent(Shape);Actor->AddInstanceComponent(Shape);
        Shape->SetBoxExtent(Extent);Shape->SetCollisionProfileName(TEXT("BlockAll"));Shape->RegisterComponent();
        Actor->SetActorLocation(Center);return Actor;
    };
    Box(FVector(0,0,-50),FVector(3000,3000,50));
    auto ExercisePush=[&](float Dt,bool Wall)
    {
        AActor* Obstacle=Wall?Box(FVector(500,0,200),FVector(25,2000,200)):nullptr;
        FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=World->SpawnActor<AHeQueAuditPawn>(FVector(0,0,98),FRotator::ZeroRotator,Spawn);
        auto* Move=CastChecked<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
        Move->SetMovementMode(MOVE_Walking);
        const FVector Start=Pawn->GetActorLocation();
        Move->ApplyImpactPush(Wall?FVector(1,.3,0):FVector::ForwardVector,1000.f);
        for(float Time=0;Time<.4f;Time+=Dt)Move->PerformMovement(Dt);
        const FVector End=Pawn->GetActorLocation();
        const float Distance=FVector::Dist2D(Start,End);
        UE_LOG(LogTemp,Display,TEXT("[HeQueAudit] push dt=%.5f wall=%d distance=%.3f end=%s"),Dt,Wall,Distance,*End.ToCompactString());
        Check(Wall?(End.X<=475.f-Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius()+1.f&&Distance>100.f):FMath::Abs(Distance-1000.f)<2.f,
            FString::Printf(TEXT("%s push at dt %.5f"),Wall?TEXT("wall-limited"):TEXT("10m"),Dt));
        for(int32 I=0;I<15;++I)Move->PerformMovement(Dt);
        Check(!Move->HasImpactPush()&&FVector::DistSquared2D(End,Pawn->GetActorLocation())<1.f,TEXT("push ends without residual drift"));
        Pawn->Destroy();if(Obstacle)Obstacle->Destroy();
    };
    for(float Dt:{1.f/30.f,1.f/60.f,1.f/120.f}){ExercisePush(Dt,false);ExercisePush(Dt,true);}

    auto* Target=World->SpawnActor<AHeQueMonster>(BossClass,FVector(0,1500,300),FRotator::ZeroRotator);
    if(!Target){World->DestroyWorld(false);return 2;}
    FHitResult Forged;Forged.HitObjectHandle=FActorInstanceHandle(Target);Forged.BoneName=TEXT("HQ_CoreSwing");
    Check(!Target->IsWeakpointHit(Forged),TEXT("a bone name without the real hit component is not a weakpoint"));
    Forged.Component=Target->GetMesh();
    Target->ResolveRemoteHit(FVector(0,-2000,2000),FVector(100,-2000,2000),Forged);
    Check(!Target->IsWeakpointHit(Forged),TEXT("unverified remote heart claim is downgraded to body"));
    auto* Mesh=Target->GetMesh();
    Mesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);Mesh->PlayAnimation(Target->IdleClip,false);
    Mesh->SetPosition(.2f,false);Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();
    Mesh->UpdateKinematicBonesToAnim(Mesh->GetComponentSpaceTransforms(),ETeleportType::TeleportPhysics,false,EAllowKinematicDeferral::DisallowDeferral);
    bool HeartVerified=false,BodyRejected=false;
    for(const USkeletalBodySetup* Setup:Target->HitSurfacePhysics->SkeletalBodySetups)
    {
        auto* Body=Mesh->GetBodyInstance(Setup->BoneName);if(!Body)continue;
        const FVector Center=Body->GetBodyBounds().GetCenter();
        for(const FVector Direction:{FVector::ForwardVector,-FVector::ForwardVector,FVector::RightVector,-FVector::RightVector})
        {
            const FVector Start=Center+Direction*800.f;
            FHitResult Contact;FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQueAuditHeart),true);
            if(!Mesh->LineTraceComponent(Contact,Start,Center,Query))continue;
            const bool Heart=Target->IsWeakpointHit(Contact);
            const FVector Point=Contact.ImpactPoint;Contact.BoneName=TEXT("HQ_CoreSwing");
            Target->ResolveRemoteHit(Start,Point,Contact);
            if(Heart)HeartVerified|=Target->IsWeakpointHit(Contact);
            else BodyRejected|=!Target->IsWeakpointHit(Contact);
        }
    }
    Check(HeartVerified,TEXT("real exposed heart contact remains a server-verified weakpoint"));
    Check(BodyRejected,TEXT("real body contact cannot claim the heart bone remotely"));
    World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("[HeQueAudit] checks=%d failures=%d (offline physics and assets; not a network session)"),Checks,Failures);
    return Failures?1:0;
}
