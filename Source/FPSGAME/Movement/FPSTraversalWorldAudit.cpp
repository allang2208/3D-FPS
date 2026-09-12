#include "FPSTraversalComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "PhysicsEngine/BodySetup.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"

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
    Character->GetCharacterMovement()->SetMovementMode(MOVE_Falling); Check(TEXT("airborne_close_wall"),A::Vault);
    Character->SetActorLocation(FVector(54,0,156));
    Check(TEXT("airborne_without_nearby_ground_support"),A::Vault);
    Character->GetCharacterMovement()->Velocity=FVector(0,0,-250);
    Check(TEXT("descending_wall_catch"),A::Vault);
    Character->GetCharacterMovement()->Velocity=FVector(0,0,-901);
    Check(TEXT("fast_fall_rejected"),A::None);
    Character->GetCharacterMovement()->Velocity=FVector(-100,0,-100);
    Check(TEXT("looking_at_wall_while_moving_away"),A::Vault);
    // Decouple the actual view, body rotation and velocity. Actor yaw alone can
    // lag a turn on the frame that the held airborne request is evaluated.
    auto* ViewController=World->SpawnActor<APlayerController>();
    ViewController->Possess(Character);
    Character->SetActorRotation(FRotator(0,90,0));
    ViewController->SetControlRotation(FRotator::ZeroRotator);
    Check(TEXT("view_at_wall_body_sideways"),A::Vault);
    Character->GetCharacterMovement()->Velocity=FVector(0,500,-100);
    Check(TEXT("view_at_wall_sideways_velocity"),A::Vault);
    Character->GetCharacterMovement()->Velocity=FVector(-500,300,-100);
    ViewController->SetControlRotation(FRotator(70,39,0));
    Check(TEXT("upward_view_yaw_39_diagonal_away"),A::Vault);
    ViewController->SetControlRotation(FRotator(-70,-39,0));
    Check(TEXT("downward_view_yaw_minus39_diagonal_away"),A::Vault);
    ViewController->SetControlRotation(FRotator(0,41,0));
    Check(TEXT("view_outside_40_degrees_rejected"),A::None);
    Character->SetActorRotation(FRotator::ZeroRotator);
    Character->GetCharacterMovement()->Velocity=FVector(500,0,-100);
    ViewController->SetControlRotation(FRotator(0,90,0));
    Check(TEXT("moving_toward_wall_but_looking_sideways"),A::None);
    ViewController->SetControlRotation(FRotator(0,180,0));
    Check(TEXT("moving_toward_wall_but_looking_behind"),A::None);
    ViewController->SetControlRotation(FRotator::ZeroRotator);
    Character->SetActorLocation(FVector(39,0,156));
    Check(TEXT("view_at_wall_outside_reach"),A::None);
    ViewController->UnPossess(); ViewController->Destroy();
    Character->SetActorLocation(FVector(54,0,156));
    Character->GetCharacterMovement()->Velocity=FVector::ZeroVector;
    Character->SetActorLocation(FVector(54,0,166));
    Check(TEXT("airborne_thirty_cm_lip"),A::Vault);
    Character->SetActorLocation(FVector(54,0,186));
    Check(TEXT("lip_below_airborne_feet_reach"),A::None);
    Character->SetActorLocation(FVector(54,0,156));
    auto* AirRoof=Box(FVector(140,0,250),FVector(220,400,20));
    Check(TEXT("airborne_overhead_capsule_blocked"),A::None); AirRoof->Destroy();
    const auto ReleasedProbe=Detector->FindTarget(false,true);
    if (ReleasedProbe.Action!=A::None) ++Failures;
    ++Checks;
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_WORLD %s airborne_without_jump_request"),ReleasedProbe.Action==A::None?TEXT("PASS"):TEXT("FAIL"));
    Character->SetActorLocation(FVector(54,0,98));
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
    Check(TEXT("stationary_movable_wall"),A::Vault);
    auto* MovingShape=CastChecked<UBoxComponent>(Wall->GetRootComponent());
    MovingShape->ComponentVelocity=FVector(20,0,0);
    Check(TEXT("actually_moving_wall"),A::None);
    MovingShape->ComponentVelocity=FVector::ZeroVector;
    MovingShape->SetSimulatePhysics(true);
    Check(TEXT("physics_simulated_wall"),A::None); Wall->Destroy();
    Wall=Box(FVector(202,0,90),FVector(200,400,180));
    auto* Roof=Box(FVector(202,0,330),FVector(200,400,20));
    Check(TEXT("platform_without_headroom"),A::None); Roof->Destroy(); Wall->Destroy();
    // A stationary movable facade and separate top slab form one usable ledge.
    Wall=Box(FVector(152,0,80),FVector(100,400,160),EComponentMobility::Movable);
    auto* Slab=Box(FVector(202,0,170),FVector(200,400,20),EComponentMobility::Movable);
    Check(TEXT("modular_facade_and_separate_top"),A::Mantle);
    Roof=Box(FVector(202,0,381),FVector(200,400,10)); // 196 cm above the top.
    Check(TEXT("capsule_fits_under_roof"),A::Mantle); Roof->Destroy();
    Roof=Box(FVector(202,0,375),FVector(200,400,10)); // 190 cm: head cannot fit.
    Check(TEXT("modular_top_blocks_capsule_head"),A::None); Roof->Destroy();
    auto* SideBeam=Box(FVector(150,39,270),FVector(20,10,120));
    Check(TEXT("off_center_beam_blocks_capsule"),A::None); SideBeam->Destroy();
    Slab->Destroy(); Wall->Destroy();
    Wall=Box(FVector(147,0,90),FVector(90,400,180));
    Check(TEXT("ninety_cm_top_fits_actual_capsule"),A::Mantle); Wall->Destroy();
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
    // A thin wedge can be vaulted without standing on its steep roof. Its
    // accepted palm normals must survive into presentation (old limit was .65).
    auto* WedgeMesh=NewObject<UStaticMesh>(); WedgeMesh->CreateBodySetup();
    auto* WedgeBody=WedgeMesh->GetBodySetup(); WedgeBody->CollisionTraceFlag=CTF_UseSimpleAsComplex;
    FKConvexElem Wedge;
    for (float X:{0.f,30.f}) for (float Y:{-200.f,200.f})
    {
        Wedge.VertexData.Add(FVector(X,Y,0));
        Wedge.VertexData.Add(FVector(X,Y,60.f+X*1.7320508f));
    }
    Wedge.UpdateElemBox(); WedgeBody->AggGeom.ConvexElems.Add(Wedge); WedgeBody->CreatePhysicsMeshes();
    Wall=World->SpawnActor<AActor>(); auto* WedgeShape=NewObject<UStaticMeshComponent>(Wall);
    Wall->AddInstanceComponent(WedgeShape); Wall->SetRootComponent(WedgeShape); WedgeShape->SetStaticMesh(WedgeMesh);
    WedgeShape->SetCollisionProfileName(TEXT("BlockAll")); WedgeShape->RegisterComponent(); Wall->SetActorLocation(FVector(102,0,0));
    Check(TEXT("steep_lip_thin_wedge_vault"),A::Vault);
    const auto WedgeTarget=Detector->FindTarget(true,true);
    const bool Hands=WedgeTarget.Handholds.Num()==2 && WedgeTarget.Handholds[0].Normal.Z>.2f &&
        WedgeTarget.Handholds[0].Normal.Z<.65f && WedgeTarget.Handholds[1].Normal.Z<.65f;
    ++Checks; if (!Hands)++Failures;
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_WORLD %s steep_lip_exports_both_accepted_handholds"),Hands?TEXT("PASS"):TEXT("FAIL"));
    Wall->Destroy();
    Floor->Destroy();
    World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_WORLD_RESULT checks=%d failures=%d"),Checks,Failures);
    return Failures;
}
