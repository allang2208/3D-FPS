#include "FPSTraversalComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "PhysicsEngine/BodySetup.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

int32 AuditFPSTraversalWorld()
{
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("TraversalGeometryAudit"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if (!World) return 1;
    const auto Box=[&](FVector Center,FVector Size,EComponentMobility::Type Mobility=EComponentMobility::Static)
    {
        auto* Actor=World->SpawnActor<AActor>();
        auto* Shape=NewObject<UBoxComponent>(Actor);
        Actor->AddInstanceComponent(Shape); Actor->SetRootComponent(Shape);
        Shape->SetMobility(Mobility); Shape->SetBoxExtent(Size*.5f);
        Shape->SetCollisionProfileName(TEXT("BlockAll")); Shape->RegisterComponent();
        Actor->SetActorLocation(Center); return Actor;
    };
    auto* Floor=Box(FVector(0,0,-10),FVector(4000,4000,20));
    auto* Character=World->SpawnActor<ACharacter>();
    Character->GetCapsuleComponent()->SetCapsuleSize(42,96);
    Character->SetActorLocation(FVector(54,0,98));
    Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    auto* Detector=NewObject<UFPSTraversalComponent>(Character);
    Character->AddInstanceComponent(Detector); Detector->RegisterComponent();
    int32 Failures=0,Checks=0;
    using A=EFPSTraversalAction;
    const auto Check=[&](const TCHAR* Name,A Expected)
    {
        const auto T=Detector->FindTarget(true,true);
        const bool Pass=T.Action==Expected; ++Checks; if(!Pass)++Failures;
        UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_WORLD %s %s action=%d H=%.3f D=%.3f top=%d landing=%d approach=%d vaultpath=%d mantlepath=%d reason=%s"),
            Pass?TEXT("PASS"):TEXT("FAIL"),Name,(int32)T.Action,T.Probe.Height,T.Probe.Depth,
            T.Probe.bTopStandingSpace,T.Probe.bLandingStandingSpace,T.Probe.bApproachClear,
            T.Probe.bVaultPathClear,T.Probe.bMantlePathClear,*T.Reason);
    };
    Check(TEXT("empty_ground"),A::None);
    for(float Height : {50.f,50.1f,120.f,120.1f,200.f,200.1f})
    {
        auto* Wall=Box(FVector(202,0,Height*.5f),FVector(200,400,Height));
        Check(*FString::Printf(TEXT("wide_height_%.1f"),Height),Height<=50.f||Height>200.f?A::None:A::Mantle);
        if (Height>50.f && Height<=200.f)
        {
            for (float Yaw : {-39.f,-24.f,-7.f,7.f,24.f,39.f})
            {
                Character->SetActorRotation(FRotator(0,Yaw,0));
                Check(*FString::Printf(TEXT("wide_height_%.1f_yaw_%.1f"),Height,Yaw),A::Mantle);
            }
            Character->SetActorRotation(FRotator::ZeroRotator);
        }
        Wall->Destroy();
    }
    auto* Wall=Box(FVector(132,0,50),FVector(60,400,100));
    Check(TEXT("thin_low_wall"),A::Vault);
    for (float Yaw : {-39.f,-24.f,-7.f,7.f,24.f,39.f})
    {
        Character->SetActorRotation(FRotator(0,Yaw,0));
        Check(*FString::Printf(TEXT("thin_yaw_%.1f"),Yaw),A::Vault);
    }
    Character->SetActorRotation(FRotator(0,41,0)); Check(TEXT("outside_facing_limit"),A::None);
    Character->SetActorRotation(FRotator::ZeroRotator);
    Character->SetActorLocation(FVector(39,0,98)); Check(TEXT("too_far"),A::None);
    Character->SetActorLocation(FVector(40.1f,0,98));
    Check(TEXT("near_distance_limit"),A::Vault);
    for (float Yaw : {-39.f,39.f})
    {
        Character->SetActorRotation(FRotator(0,Yaw,0));
        Check(TEXT("near_distance_and_angle_limits"),A::Vault);
    }
    Character->SetActorRotation(FRotator::ZeroRotator);
    Character->SetActorLocation(FVector(54,0,98));
    Character->GetCharacterMovement()->SetMovementMode(MOVE_Falling); Check(TEXT("airborne"),A::None);
    Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    auto* Ceiling=Box(FVector(0,0,230),FVector(100,150,20));
    Check(TEXT("approach_ceiling"),A::None); Ceiling->Destroy();
    auto* LandingBlock=Box(FVector(214,0,95),FVector(20,200,190));
    Check(TEXT("blocked_far_side_thin_wall"),A::None); LandingBlock->Destroy();
    Wall->Destroy();
    Wall=Box(FVector(157,0,50),FVector(110,400,100));
    LandingBlock=Box(FVector(270,0,95),FVector(20,200,190));
    Check(TEXT("blocked_far_side_wide_wall_mantle"),A::Mantle);
    LandingBlock->Destroy(); Wall->Destroy();
    Floor->Destroy(); Floor=Box(FVector(0,0,-10),FVector(200,4000,20));
    Wall=Box(FVector(132,0,50),FVector(60,400,100));
    Check(TEXT("no_landing_floor"),A::None); Wall->Destroy(); Floor->Destroy();
    Floor=Box(FVector(0,0,-10),FVector(4000,4000,20));
    Wall=Box(FVector(132,0,90),FVector(60,400,180)); Check(TEXT("high_thin_wall"),A::None); Wall->Destroy();
    Wall=Box(FVector(132,0,50),FVector(60,40,100)); Check(TEXT("narrow_wall"),A::None); Wall->Destroy();
    Wall=Box(FVector(132,0,50),FVector(60,400,100),EComponentMobility::Movable);
    Check(TEXT("movable_wall"),A::None); Wall->Destroy();
    Wall=Box(FVector(202,0,90),FVector(200,400,180));
    auto* Roof=Box(FVector(202,0,330),FVector(200,400,20));
    Check(TEXT("platform_without_headroom"),A::None); Roof->Destroy(); Wall->Destroy();
    // Sloped top/front fixtures exercise surface normals rather than box assumptions.
    for (float Roll : {-6.f,6.f})
    {
        Wall=Box(FVector(202,0,70),FVector(200,400,140));
        Wall->SetActorRotation(FRotator(0,0,Roll));
        Check(TEXT("sloped_platform_top"),A::Mantle); Wall->Destroy();
    }
    // A bevelled convex obstacle with an uneven roof, not a rotated box.
    auto* RockMesh=NewObject<UStaticMesh>(); RockMesh->CreateBodySetup();
    auto* Body=RockMesh->GetBodySetup(); Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
    FKConvexElem Hull;
    const FVector2D Outline[]={{-100,-100},{-85,-200},{85,-200},{100,-100},{100,100},{85,200},{-85,200},{-100,100}};
    for (FVector2D XY:Outline)
    {
        Hull.VertexData.Add(FVector(XY.X,XY.Y,0));
        Hull.VertexData.Add(FVector(XY.X,XY.Y,140+XY.Y*.02f));
    }
    Hull.VertexData.Add(FVector(0,0,145)); Hull.UpdateElemBox();
    Body->AggGeom.ConvexElems.Add(Hull); Body->CreatePhysicsMeshes();
    Wall=World->SpawnActor<AActor>(); auto* Rock=NewObject<UStaticMeshComponent>(Wall);
    Wall->AddInstanceComponent(Rock); Wall->SetRootComponent(Rock); Rock->SetStaticMesh(RockMesh);
    Rock->SetMobility(EComponentMobility::Static); Rock->SetCollisionProfileName(TEXT("BlockAll"));
    Rock->RegisterComponent(); Wall->SetActorLocation(FVector(202,0,0));
    Check(TEXT("bevelled_convex_uneven_roof"),A::Mantle); Wall->Destroy();
    Floor->Destroy();
    World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_WORLD_RESULT checks=%d failures=%d"),Checks,Failures);
    return Failures;
}
