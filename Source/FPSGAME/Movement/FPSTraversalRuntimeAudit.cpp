#include "FPSTraversalComponent.h"
#include "FPSTraversalArmsComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
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
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UFPSTraversalComponent::RunRuntimeAudit()
{
    auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    auto* P=C?C->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    const float Now=GetWorld()->GetTimeSeconds();
    if (!P || !P->ProfileSlot().Contains(TEXT("TraversalRuntimeAudit")) || Now<5) return;
    if (FParse::Param(FCommandLine::Get(),TEXT("TraversalVillageAudit"))) { RunVillageAudit(); return; }
    if (FParse::Param(FCommandLine::Get(),TEXT("TraversalAirAudit"))) { RunAirAudit(); return; }
    if (FParse::Param(FCommandLine::Get(),TEXT("TraversalBoundaryAudit"))) { RunBoundaryAudit(); return; }
    const auto Check=[&](bool OK,const TCHAR* Label) { if(!OK) ++AuditFailures; UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_RUNTIME %s case=%d %s"),OK?TEXT("PASS"):TEXT("FAIL"),AuditCase,Label); };
    const auto Box=[&](FVector Pos,FVector Size)
    {
        auto* A=GetWorld()->SpawnActor<AStaticMeshActor>();
        A->SetMobility(EComponentMobility::Movable);
        A->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        A->SetActorLocation(Pos); A->SetActorScale3D(Size/100.f);
        A->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
        A->SetMobility(EComponentMobility::Static); return A;
    };
    const bool bSurfaceAudit=FParse::Param(FCommandLine::Get(),TEXT("TraversalSurfaceAudit"));
    const bool bCourse=FParse::Param(FCommandLine::Get(),TEXT("TraversalCourseAudit"));
    FVector Origin(50000,0,10000);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("TraversalRuntimeAudit")/P->ProfileSlot();
    if (AuditStage==0)
    {
        IFileManager::Get().MakeDirectory(*Out,true);
        if (!bCourse) Box(Origin+FVector(200,0,-10),FVector(2000,1600,20));
        Check(Arms && VaultClip && MantleClip && ClimbClip,TEXT("native arms and three clips loaded"));
        if (FParse::Param(FCommandLine::Get(),TEXT("TraversalPreserveProfile"))) { AuditStage=1; AuditAt=Now; return; }
        auto S=P->Snapshot(); S.Items.Reset(); S.Hotbar.Init(TEXT(""),4); S.HotbarDefinitions.Init(TEXT(""),4);
        auto W=P->CreateItem(TEXT("ue_m4a1"));W.Place=1;W.Cell=6;W.Magazine=17;S.Items.Add(W);S.ActiveWeaponSlot=6;
        W=P->CreateItem(TEXT("ue_akm"));
        if (W.Data.IsEmpty()) W=P->CreateItem(TEXT("ue_m4a1")); // Published core does not require the optional AKM catalog.
        W.Place=1;W.Cell=9;W.Magazine=17;S.Items.Add(W);
        P->CommitState(S); AuditStage=1; AuditAt=Now; return;
    }
    if (AuditStage==1 && Now-AuditAt>2 && !C->IsWeaponBusy())
    {
        const float Heights[]={100,100,180,200,100,100};
        const float H=Heights[AuditCase],Depth=AuditCase==0||AuditCase==4||AuditCase==5?60.f:200.f;
        if (bCourse)
        {
            const TCHAR* Labels[]={TEXT("TraversalTest_Low"),TEXT("TraversalTest_Medium"),TEXT("TraversalTest_High"),TEXT("TraversalTest_Platform")};
            for (TActorIterator<AStaticMeshActor> It(GetWorld());It;++It)
                if (It->GetActorNameOrLabel()==Labels[AuditCase]) AuditWall=*It;
            if (!IsValid(AuditWall)) { Check(false,TEXT("course obstacle present")); bRuntimeAudit=false; return; }
            FVector Center,Extent; AuditWall->GetActorBounds(false,Center,Extent);
            Origin=FVector(Center.X-Extent.X-102,Center.Y,Center.Z-Extent.Z);
        }
        else
        {
            if (IsValid(AuditWall)) AuditWall->Destroy();
            AuditWall=Box(Origin+FVector(102+Depth*.5f,0,H*.5f),FVector(Depth,400,H));
            if (bSurfaceAudit && (AuditCase==1||AuditCase==2))
            {
                CastChecked<AStaticMeshActor>(AuditWall)->SetMobility(EComponentMobility::Movable);
                AuditWall->SetActorRotation(FRotator(0,0,AuditCase==1?6.f:-6.f));
            }
        }
        C->GetCharacterMovement()->StopMovementImmediately();C->SetActorLocationAndRotation(Origin+FVector(54,0,98),FRotator::ZeroRotator);
        C->GetCharacterMovement()->SetMovementMode(MOVE_Walking); C->Controller->SetControlRotation(FRotator::ZeroRotator);
        C->FirstPersonCamera->SetRelativeLocation(FVector(0,0,74));
        AuditAmmo=C->MagazineAmmo;
        if (AuditCase==0) { auto Saved=VaultClip; VaultClip=nullptr;Check(!TryStart(true),TEXT("missing animation preserves normal jump fallback"));VaultClip=Saved; }
        if (bCourse) { AuditStage=12; AuditAt=Now; return; }
    }
    if (AuditStage==12 && Now-AuditAt<.75f)
    {
        C->AddMovementInput(C->GetActorForwardVector(),1.f); return;
    }
    if ((AuditStage==1 && Now-AuditAt>2 && !C->IsWeaponBusy()) || (AuditStage==12 && Now-AuditAt>=.75f))
    {
        if (bCourse)
        {
            const float Yaws[]={35.f,-35.f,39.f,-39.f};
            // Exercise the newly allowed clearance as well as the wider facing cone.
            FVector Center,Extent; AuditWall->GetActorBounds(false,Center,Extent);
            C->SetActorLocation(FVector(Center.X-Extent.X-59,Center.Y,Center.Z-Extent.Z+98));
            C->SetActorRotation(FRotator(0,Yaws[AuditCase],0));
            C->Controller->SetControlRotation(C->GetActorRotation());
        }
        const auto Probe=FindTarget(true,true);
        if (bSurfaceAudit && (AuditCase==1||AuditCase==2))
            Check(FMath::Abs(AuditWall->GetActorRotation().Roll)>5.9f && Probe.Handholds.Num()==2 &&
                FMath::Abs(Probe.Handholds[0].Position.Z-Probe.Handholds[1].Position.Z)>5.f,
                TEXT("real sloped fixture produces independently elevated handholds"));
        UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_COURSE_PROBE case=%d reason=%s target=%s"),AuditCase,*Probe.Reason,*GetNameSafe(Probe.Obstacle));
        if (AuditCase==0 && !bCourse)
        {
            C->Controller->SetControlRotation(FRotator(0,90,0)); C->JumpPressed();
            Check(!bTraversing,TEXT("press facing away uses normal jump")); C->JumpReleased();
            C->JumpBufferRemaining=0; C->StopJumping();
            C->Controller->SetControlRotation(FRotator::ZeroRotator);
            C->SetActorRotation(FRotator::ZeroRotator);
        }
        // The press and release can arrive within one input frame. A tap still
        // consumes jump exactly once and cannot cancel an accepted traversal.
        auto* PC=GetWorld()->GetFirstPlayerController();
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::SpaceBar,IE_Pressed,1));
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::SpaceBar,IE_Released,0));
        AuditStage=11; AuditAt=Now; return;
    }
    if (AuditStage==11)
    {
        Check(bTraversing,TEXT("space tap starts traversal without hold delay"));
        Check(C->JumpBufferRemaining==0,TEXT("accepted tap does not queue a second jump"));
        if (!bTraversing) { AuditStage=3;AuditAt=Now;return; }
        if (LastJumpTarget.Action==EFPSTraversalAction::Vault)
            Check(FMath::IsNearlyEqual(Duration/PlaybackRate,.4f,.001f),TEXT("vault body and animation finish in 0.4 seconds"));
        C->FirePressed();C->AimPressed();C->ReloadPressed();
        Check(!C->IsAiming()&&!C->IsReloading()&&C->MagazineAmmo==AuditAmmo,TEXT("hands occupied blocks fire ADS reload"));
        const FString Weapon=C->ActiveInventoryWeapon;
        for(FKey K:{EKeys::MouseScrollUp,EKeys::MouseScrollDown}) GetWorld()->GetFirstPlayerController()->InputKey(FInputKeyEventArgs::CreateSimulated(K,IE_Pressed,1));
        Check(C->ActiveInventoryWeapon==Weapon && bTraversing,TEXT("both wheel directions blocked during traversal"));
        AuditStage=2;AuditAt=Now;return;
    }
    if(AuditStage==2)
    {
        if (bSurfaceAudit && bTraversing && Elapsed>Contact && Elapsed<Release-.15f)
        {
            const auto View=C->Controller->GetControlRotation();
            const float Offset=FMath::Abs(FMath::FindDeltaAngleDegrees(Facing.Rotator().Yaw,View.Yaw));
            Check(Offset<=20.1f,TEXT("controller view constrained without hidden mouse accumulation"));
            C->Controller->SetControlRotation(FRotator(75,View.Yaw+100,0));
        }
        if(Now-AuditCaptureAt>.065f) {
            AuditCaptureAt=Now;
            FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("case_%d_frame_%04d.png"),AuditCase,AuditFrame++),false,false);
            if(Arms) UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_FRAME case=%d elapsed=%.3f camera=%s handL=%s handR=%s edge=%s visible=%d bounds=%s"),AuditCase,Elapsed,*C->FirstPersonCamera->GetComponentLocation().ToString(),*Arms->GetSocketLocation(TEXT("hand_l")).ToString(),*Arms->GetSocketLocation(TEXT("hand_r")).ToString(),*LastJumpTarget.FrontEdge.ToString(),Arms->IsVisible(),*Arms->Bounds.Origin.ToString());
        }
        if (bSurfaceAudit && bTraversing && AuditCase!=4 && Elapsed>Duration-.1f) C->MoveInput=FVector2D(0,1);
        if(AuditCase==4&&bTraversing&&Elapsed>.2f) {AuditWall->Destroy();}
        if(!bTraversing || Now-AuditAt>6) {
            Check(!bTraversing,TEXT("executor exits within duration"));
            if (AuditCase!=4)
                Check(FMath::Abs((Now-AuditAt)-Duration/PlaybackRate)<.1f,TEXT("measured execution time matches playback rate"));
            if(AuditCase!=4)Check(bLastTraversalSucceeded && C->GetCharacterMovement()->IsMovingOnGround() && LastExitLocation.Equals(LastJumpTarget.Destination,5.f),TEXT("capsule reaches live supported destination"));
            else Check(!bLastTraversalSucceeded && !LastExitLocation.Equals(LastJumpTarget.Destination,5.f),TEXT("removed obstacle interrupts movement"));
            Check(C->GetCharacterMovement()->MovementMode!=MOVE_None && C->AKMViewmodel->IsVisible(),TEXT("movement and weapon restored"));
            Check(C->MagazineAmmo==AuditAmmo,TEXT("traversal preserves ammunition"));
            if (bSurfaceAudit && AuditCase!=4)
            {
                auto* SurfaceArms=CastChecked<UFPSTraversalArmsComponent>(Arms);
                Check(SurfaceArms->SurfaceCorrections>0,TEXT("surface-aware arm correction executed"));
                Check(SurfaceArms->AnchoredHandCount()==2,TEXT("both hands use detector-approved contacts"));
                Check(SurfaceArms->MaxBoneLengthError<.05f,TEXT("surface IK preserves limb lengths"));
                Check(!Arms->IsVisible(),TEXT("traversal arms removed before free look resumes"));
                Check(Duration<=Release+.301f,TEXT("released animation tail no longer stalls traversal"));
                Check(C->GetCharacterMovement()->Velocity.Size2D()>10.f,TEXT("held movement resumes immediately at traversal exit"));
                C->MoveInput=FVector2D::ZeroVector;
            }
            C->AimReleased();C->FireReleased(); AuditStage=3;AuditAt=Now;
        }
    }
    if(AuditStage==3 && Now-AuditAt>.4f)
    {
        if(++AuditCase<(bCourse?4:6)) {
            if(AuditCase==5) {Check(P->CycleWeapon(),TEXT("weapon switch restored after traversal"));Check(C->bUsingM4Infima==(P->Equipped()->Definition==TEXT("ue_m4a1")),TEXT("secondary weapon traversal fixture selected"));}
            AuditStage=1;AuditAt=Now;return;
        }
        UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_RUNTIME_RESULT cases=%d failures=%d"),bCourse?4:6,AuditFailures);
        bRuntimeAudit=false;GetWorld()->GetFirstPlayerController()->ConsoleCommand(TEXT("quit"));
    }
}
