#include "FPSTraversalComponent.h"
#include "FPSTraversalArmsComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/HandBrainFearComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

void UFPSTraversalComponent::RunBoundaryAudit()
{
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    auto* PC=GetWorld()->GetFirstPlayerController();
    auto* Movement=C->GetCharacterMovement();
    auto* P=C->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const float Now=GetWorld()->GetTimeSeconds(),Dt=GetWorld()->GetDeltaSeconds();
    const FVector Origin(65000,10000,10000);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("TraversalRuntimeAudit")/P->ProfileSlot();
    const auto Check=[&](bool OK,const TCHAR* Label)
    { if(!OK)++AuditFailures; UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_BOUNDARY %s case=%d %s"),OK?TEXT("PASS"):TEXT("FAIL"),AuditCase,Label); };
    const auto Box=[&](FVector Pos,FVector Size)
    {
        auto* A=GetWorld()->SpawnActor<AStaticMeshActor>(); A->SetMobility(EComponentMobility::Movable);
        A->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        A->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
        A->SetActorLocation(Pos); A->SetActorScale3D(Size/100.f); return A;
    };
    if (AuditStage==0)
    {
        IFileManager::Get().MakeDirectory(*Out,true);
        // The same helper serves the animated camera and cancelled recovery.
        const FVector Center=Origin+FVector(500,800,300),From=Center-FVector(30,0,0),To=Center+FVector(30,0,0);
        auto* A=Box(Center,FVector(10,100,100)); auto* Shape=A->GetStaticMeshComponent();
        Shape->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
        Check(SweepCamera(From,To).X<Center.X-9.f,TEXT("camera blocks on Pawn obstacle that ignores Visibility"));
        Shape->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
        Shape->SetCollisionResponseToChannel(C->GetCapsuleComponent()->GetCollisionObjectType(),ECR_Ignore);
        Check(SweepCamera(From,To).Equals(To,.1f),TEXT("Visibility-only obstacle does not falsely block camera"));
        A->Destroy();
        AuditStage=1; AuditAt=Now; return;
    }
    if (AuditStage==1 && Now-AuditAt>1.f && !C->IsWeaponBusy())
    {
        Cancel(); C->JumpReleased(); C->MoveInput=FVector2D::ZeroVector;
        if (IsValid(AuditWall)) AuditWall->Destroy();
        if (IsValid(AirAuditRoof)) AirAuditRoof->Destroy();
        AirAuditRoof=Box(Origin+FVector(200,0,-10),FVector(3000,2000,20));
        AuditWall=AuditCase==6?Box(Origin+FVector(132,0,50),FVector(60,400,100)):
            Box(Origin+FVector(202,0,90),FVector(200,400,180));
        Movement->StopMovementImmediately(); C->SetActorLocationAndRotation(Origin+FVector(54,0,98),FRotator::ZeroRotator);
        Movement->SetMovementMode(MOVE_Walking); PC->SetControlRotation(FRotator::ZeroRotator);
        C->FirstPersonCamera->SetRelativeLocation(FVector(0,0,C->StandingCameraHeight));
        AuditAmmo=C->MagazineAmmo; C->JumpPressed();
        Check(bTraversing,TEXT("boundary fixture enters real traversal"));
        if (!bTraversing) { bRuntimeAudit=false; PC->ConsoleCommand(TEXT("quit")); return; }
        AuditStage=2; AuditAt=Now; AuditFrame=0; return;
    }
    if (AuditStage==2 && bTraversing && Elapsed>(AuditCase==6?Duration-FMath::Max(.06f,PlaybackRate*Dt*1.5f):.85f))
    {
        if (AuditCase!=6)
            Check(CastChecked<UFPSTraversalArmsComponent>(Arms)->AnchoredHandCount()==2,TEXT("accepted ledge plants both hands before interruption"));
        auto* Shape=CastChecked<UStaticMeshComponent>(AuditWall->GetRootComponent());
        switch (AuditCase)
        {
        case 0: Shape->SetCollisionEnabled(ECollisionEnabled::NoCollision); break;
        case 1: Shape->SetCollisionResponseToChannel(C->GetCapsuleComponent()->GetCollisionObjectType(),ECR_Ignore); break;
        case 2: Shape->UnregisterComponent(); break;
        case 3:
        {
            auto* Fear=C->FindComponentByClass<UHandBrainFearComponent>();
            if (!Fear) { Fear=NewObject<UHandBrainFearComponent>(C); C->AddInstanceComponent(Fear); Fear->RegisterComponent(); }
            Fear->Apply(AuditWall);
            Check(!bTraversing && Movement->IsFalling() && PC->IsMoveInputIgnored(),TEXT("actual fear Apply immediately takes movement control"));
            break;
        }
        case 4: PC->SetIgnoreMoveInput(true); break;
        case 5: AuditWall->Destroy(); break;
        case 6:
            // Independently exercise the completion contract when the far-side
            // ground disappears at arrival, even if a caller requests success.
            AirAuditRoof->Destroy(); C->SetActorLocation(LastJumpTarget.Destination);
            Finish(true);
            Check(!bLastTraversalSucceeded && Movement->IsFalling(),TEXT("completion cannot report success without live landing floor"));
            break;
        }
        AuditStage=3; AuditAt=Now; AuditMaxRecoverySpeed=0;
        AirAuditPreviousCamera=C->FirstPersonCamera->GetComponentLocation(); AuditPreviousCapsule=C->GetActorLocation();
        return;
    }
    if (AuditStage==3)
    {
        const FVector Camera=C->FirstPersonCamera->GetComponentLocation(),Capsule=C->GetActorLocation();
        if (AuditCase!=4 && AuditCase!=6)
        {
            const float Speed=((Camera-AirAuditPreviousCamera)-(Capsule-AuditPreviousCapsule)).Size()/FMath::Max(Dt,.001f);
            AuditMaxRecoverySpeed=FMath::Max(AuditMaxRecoverySpeed,Speed);
            if (Now-AuditAt<Dt*1.5f)
            {
                Check(!bTraversing && !bLastTraversalSucceeded && Movement->IsFalling(),TEXT("invalidated support or fear cancels on next update"));
                UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_BOUNDARY_CAMERA case=%d first_recovery_step=%.3f dt=%.6f"),AuditCase,Speed*Dt,Dt);
            }
        }
        AirAuditPreviousCamera=Camera; AuditPreviousCapsule=Capsule;
        if (Now-AuditCaptureAt>.06f)
        {
            AuditCaptureAt=Now;
            FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("case_%d_frame_%04d.png"),AuditCase,AuditFrame++),false,false);
        }
        if (AuditCase==4 && !bTraversing && PC->IsMoveInputIgnored())
        {
            Check(bLastTraversalSucceeded && Movement->IsMovingOnGround() && PC->IsMoveInputIgnored(),TEXT("menu input lock allows supported traversal to finish"));
            PC->SetIgnoreMoveInput(false);
        }
        if (Now-AuditAt>(AuditCase==3?3.4f:2.1f))
        {
            Check(!bTraversing && bJumpRequestConsumed,TEXT("interruption or completion cannot reuse held jump"));
            Check(!bReturningCamera,TEXT("cancelled camera returns without leaving recovery stuck"));
            if (AuditCase!=4 && AuditCase!=6)
            {
                Check(AuditMaxRecoverySpeed<=451.f,TEXT("camera recovery is speed-bounded after removing body displacement"));
                UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_BOUNDARY_CAMERA case=%d max_recovery_speed=%.3f"),AuditCase,AuditMaxRecoverySpeed);
            }
            if (AuditCase==3)
                Check(C->GetActorLocation().X<LastExitLocation.X-20.f && !PC->IsMoveInputIgnored(),TEXT("fear drives escape then releases its own input lock"));
            Check(C->MagazineAmmo==AuditAmmo && Movement->MovementMode!=MOVE_None,TEXT("ammo and native movement survive boundary case"));
            C->JumpReleased(); AuditStage=1; AuditAt=Now;
            if (++AuditCase==7)
            {
                UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_BOUNDARY_RESULT cases=%d failures=%d"),AuditCase,AuditFailures);
                bRuntimeAudit=false; PC->ConsoleCommand(TEXT("quit"));
            }
        }
    }
}
