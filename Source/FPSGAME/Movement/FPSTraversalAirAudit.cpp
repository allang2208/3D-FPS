#include "FPSTraversalComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

void UFPSTraversalComponent::RunAirAudit()
{
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    auto* PC=GetWorld()->GetFirstPlayerController();
    auto* P=C->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Movement=C->GetCharacterMovement();
    const float Now=GetWorld()->GetTimeSeconds();
    const bool bControlledAir=AuditCase==3 || AuditCase==5 || AuditCase==6 || AuditCase==10;
    const FVector Origin(60000,10000,10000);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("TraversalRuntimeAudit")/P->ProfileSlot();
    const auto Check=[&](bool OK,const TCHAR* Label)
    { if(!OK) ++AuditFailures; UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_AIR %s case=%d %s"),OK?TEXT("PASS"):TEXT("FAIL"),AuditCase,Label); };
    const auto Box=[&](FVector Pos,FVector Size)
    {
        auto* Actor=GetWorld()->SpawnActor<AStaticMeshActor>(); Actor->SetMobility(EComponentMobility::Movable);
        Actor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        Actor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
        Actor->SetActorLocation(Pos); Actor->SetActorScale3D(Size/100.f); return Actor;
    };
    const auto Space=[&](bool bPress)
    { PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::SpaceBar,bPress?IE_Pressed:IE_Released,bPress?1:0)); };
    if (AuditStage==0)
    {
        IFileManager::Get().MakeDirectory(*Out,true);
        Box(Origin+FVector(200,0,-10),FVector(3000,2000,20));
        auto S=P->Snapshot(); S.Items.Reset(); S.Hotbar.Init(TEXT(""),4); S.HotbarDefinitions.Init(TEXT(""),4);
        auto W=P->CreateItem(TEXT("ue_m4a1")); W.Place=1; W.Cell=6; W.Magazine=17; S.Items.Add(W); S.ActiveWeaponSlot=6;
        P->CommitState(S); AuditStage=1; AuditAt=Now; return;
    }
    if (AuditStage==1 && Now-AuditAt>1.f && !C->IsWeaponBusy())
    {
        Cancel(); Space(false); C->StopJumping(); C->JumpBufferRemaining=0;
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,IE_Released,0));
        if (IsValid(AuditWall)) AuditWall->Destroy();
        if (IsValid(AirAuditRoof)) AirAuditRoof->Destroy();
        AuditWall=Box(Origin+FVector(202,0,90),FVector(200,400,180));
        if (AuditCase==4) AirAuditRoof=Box(Origin+FVector(202,0,330),FVector(200,400,20));
        Movement->StopMovementImmediately(); C->SetActorLocationAndRotation(Origin+FVector(-80,0,98),FRotator::ZeroRotator);
        Movement->SetMovementMode(MOVE_Walking); PC->SetControlRotation(FRotator::ZeroRotator);
        C->FirstPersonCamera->SetRelativeLocation(FVector(0,0,C->StandingCameraHeight));
        if (bControlledAir)
        {
            C->SetActorLocation(Origin+FVector(54,0,AuditCase==5?350:198));
            Movement->SetMovementMode(MOVE_Falling);
            Movement->Velocity=AuditCase==6?FVector(-250,0,-200):
                (AuditCase==10?FVector(250,0,-200):FVector(0,0,AuditCase==5?-1100:-250));
            if (AuditCase==10) PC->SetControlRotation(FRotator(0,90,0));
            C->MoveInput=FVector2D::ZeroVector;
        }
        else
        {
            if (AuditCase==9)
            {
                C->SetActorLocationAndRotation(Origin+FVector(54,-250,98),FRotator(0,90,0));
                PC->SetControlRotation(FRotator(0,90,0));
            }
            C->MoveInput=FVector2D(0,1);
            PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,IE_Pressed,1));
        }
        AuditAmmo=C->MagazineAmmo; AuditFrame=0; bAirAuditStarted=false; AirAuditMaxCameraStep=0;
        AirAuditPreviousCamera=C->FirstPersonCamera->GetComponentLocation();
        if (!bControlledAir)
        {
            // Build speed using the actual forward input before takeoff. From
            // rest, the game's deliberately low air control cannot cover 140 cm.
            AuditStage=10; AuditAt=Now; return;
        }
        Space(true);
        AuditStage=2; AuditAt=Now; return;
    }
    if (AuditStage==10 && Now-AuditAt>.15f)
    {
        Check((AuditCase==9?Movement->Velocity.Y:Movement->Velocity.X)>250.f,TEXT("real forward input establishes jump approach speed"));
        Space(true); AuditStage=2; AuditAt=Now;
        AirAuditPreviousCamera=C->FirstPersonCamera->GetComponentLocation(); return;
    }
    if (AuditStage==2 || AuditStage==3)
    {
        if (AuditCase==9 && !bAirAuditStarted && !bTraversing && Now-AuditAt>.1f)
        {
            // Jump along the wall, then look at it while lateral momentum and
            // the previous body yaw remain. The held request must follow view.
            PC->SetControlRotation(FRotator::ZeroRotator);
            C->SetActorRotation(FRotator(0,90,0));
        }
        if ((AuditCase==1 || AuditCase==2) && AuditStage==2 && bJumpHeld && Now-AuditAt>.06f) Space(false);
        if (AuditCase==2 && AuditStage==2 && Movement->IsFalling() && Now-AuditAt>.1f)
        {
            const auto T=FindTarget(true,true);
            if (T.Action==EFPSTraversalAction::Vault || T.Action==EFPSTraversalAction::Mantle)
            { Space(true); Space(false); AuditStage=3; }
        }
        if (!bAirAuditStarted && bTraversing)
        {
            bAirAuditStarted=true;
            Check(LastJumpTarget.Probe.bAirborne,TEXT("jump transitions directly into airborne traversal"));
            Check(C->JumpBufferRemaining==0 && !C->bPressedJump,TEXT("catch consumes buffered and native jump"));
            Check(StartLocation.Z>Origin.Z+120.f,TEXT("catch starts above ground without teleporting back"));
            if (AuditCase==3) Check(EntryVelocity.Z<0,TEXT("descending jump can catch ledge"));
            if (AuditCase==0) Check(EntryVelocity.Z>0 && EntryLiftTangent>0,TEXT("upward velocity carried into swept lift"));
            if (AuditCase==6) Check(EntryVelocity.X< -200.f,TEXT("looking at wall permits catch while moving away"));
            if (AuditCase==9)
            {
                Check(EntryVelocity.Y>250.f && FMath::Abs(EntryVelocity.X)<100.f,TEXT("look turn catches wall while jumping parallel to it"));
                Check(FMath::Abs(C->GetActorRotation().Yaw)>45.f && FMath::Abs(EntryView.Yaw)<1.f,TEXT("view selects target independently of body yaw"));
            }
            UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_AIR_ENTRY case=%d z=%.2f vz=%.2f tangent=%.3f height=%.2f"),AuditCase,StartLocation.Z-Origin.Z,EntryVelocity.Z,EntryLiftTangent,LastJumpTarget.Probe.Height);
        }
        if (bTraversing && Elapsed<.2f)
            AirAuditMaxCameraStep=FMath::Max(AirAuditMaxCameraStep,(float)FVector::Distance(AirAuditPreviousCamera,C->FirstPersonCamera->GetComponentLocation()));
        AirAuditPreviousCamera=C->FirstPersonCamera->GetComponentLocation();
        if (Now-AuditCaptureAt>.033f)
        {
            AuditCaptureAt=Now;
            if (!bTraversing)
            {
                const auto Probe=FindTarget(true,true);
                UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_AIR_PROBE case=%d t=%.3f pos=%s velocity=%s mode=%d held=%d consumed=%d busy=%d input=%.2f reason=%s height=%.2f distance=%.2f"),
                    AuditCase,Now-AuditAt,*C->GetActorLocation().ToString(),*Movement->Velocity.ToString(),(int32)Movement->MovementMode,
                    bJumpHeld,bJumpRequestConsumed,C->IsWeaponBusy(),C->MoveInput.Y,*Probe.Reason,Probe.Probe.Height,Probe.Probe.EdgeDistance);
            }
            FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("case_%d_frame_%04d.png"),AuditCase,AuditFrame++),false,false);
        }
        if (AuditCase==7 && bTraversing && Elapsed>.3f && IsValid(AuditWall)) AuditWall->Destroy();
        const bool bExpected=AuditCase==0 || AuditCase==2 || AuditCase==3 || AuditCase==6 || AuditCase==7 || AuditCase==8 || AuditCase==9;
        if ((bAirAuditStarted && !bTraversing) || (!bAirAuditStarted && Now-AuditAt>1.1f) || Now-AuditAt>5.f)
        {
            Check(bAirAuditStarted==bExpected,TEXT("held/released/blocked/fall-speed input policy"));
            if (bExpected && bAirAuditStarted)
            {
                Check(!bTraversing,TEXT("airborne executor completes or cancels"));
                if (AuditCase==7) Check(!bLastTraversalSucceeded && Movement->IsFalling(),TEXT("removed wall restores falling without recatching"));
                else Check(bLastTraversalSucceeded && Movement->IsMovingOnGround() && LastExitLocation.Equals(LastJumpTarget.Destination,5.f),TEXT("airborne capsule reaches live supported destination"));
                Check(AirAuditMaxCameraStep<45.f,TEXT("entry camera has no large positional snap"));
                UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_AIR_CAMERA case=%d max_entry_step=%.3f"),AuditCase,AirAuditMaxCameraStep);
            }
            Check(C->MagazineAmmo==AuditAmmo && Movement->MovementMode!=MOVE_None,TEXT("ammo and native movement preserved"));
            if (AuditCase==8 && bAirAuditStarted)
            {
                PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,IE_Released,0));
                C->MoveInput=FVector2D::ZeroVector;
                C->SetActorLocation(Origin+FVector(54,0,198)); Movement->SetMovementMode(MOVE_Falling); Movement->Velocity=FVector(0,0,-100);
                AuditStage=4; AuditAt=Now; return;
            }
            PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,IE_Released,0));
            C->MoveInput=FVector2D::ZeroVector; Space(false); AuditStage=5; AuditAt=Now;
        }
    }
    if (AuditStage==4 && Now-AuditAt>.1f)
    {
        Check(bJumpHeld && bJumpRequestConsumed && !bTraversing,TEXT("one held request cannot chain another catch after exit"));
        Space(false); AuditStage=5; AuditAt=Now;
    }
    if (AuditStage==5 && Now-AuditAt>.25f)
    {
        if (++AuditCase<11) { AuditStage=1; AuditAt=Now; return; }
        UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_AIR_RESULT cases=%d failures=%d"),AuditCase,AuditFailures);
        bRuntimeAudit=false; PC->ConsoleCommand(TEXT("quit"));
    }
}
