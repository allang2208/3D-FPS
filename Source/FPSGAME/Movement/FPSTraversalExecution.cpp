#include "FPSTraversalComponent.h"
#include "FPSTraversalArmsComponent.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace { float Ease(float A,float B,float T) { return FMath::SmoothStep(A,B,T); } }

void UFPSTraversalComponent::InitializePresentation()
{
    auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    if (!C || GetNetMode()!=NM_Standalone) return;
    const auto* S=GetDefault<UFPSTraversalSettings>();
    auto* Mesh=S->ArmsMesh.LoadSynchronous();
    VaultClip=S->VaultAnimation.LoadSynchronous(); MantleClip=S->MantleAnimation.LoadSynchronous(); ClimbClip=S->ClimbAnimation.LoadSynchronous();
    if (!Mesh) return;
    Arms=NewObject<UFPSTraversalArmsComponent>(C,TEXT("TraversalArms"));
    C->AddInstanceComponent(Arms);
    Arms->SetSkeletalMesh(Mesh); Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Arms->SetCastShadow(false); Arms->SetVisibility(false); Arms->SetOnlyOwnerSee(false);
    Arms->SetOwnerNoSee(false); Arms->SetHiddenInGame(false);
    Arms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Arms->RegisterComponent(); Arms->SetComponentTickEnabled(false);
}

bool UFPSTraversalComponent::BeginJumpHold(bool bAvailable)
{
    if (bPendingJumpHold) return true;
    if (bTraversing || !Arms || GetNetMode()!=NM_Standalone)
    {
        UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_INPUT_REJECT presentation=%d net=%d active=%d"),Arms!=nullptr,(int32)GetNetMode(),bTraversing);
        return false;
    }
    const auto Target=FindTarget(true,bAvailable);
    if (Target.Action!=EFPSTraversalAction::Vault && Target.Action!=EFPSTraversalAction::Mantle)
    {
        UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_INPUT_REJECT reason=%s available=%d grounded=%d distance=%.2f facing=%.3f approach=%d pos=%s"),
            *Target.Reason,bAvailable,Target.Probe.bStandingGrounded,Target.Probe.EdgeDistance,Target.Probe.FacingDot,Target.Probe.bApproachClear,*GetOwner()->GetActorLocation().ToString());
        return false;
    }
    auto* Clip=Target.Action==EFPSTraversalAction::Vault?VaultClip.Get():
        (Target.Probe.Height>GetDefault<UFPSTraversalSettings>()->VaultMaxHeight?ClimbClip.Get():MantleClip.Get());
    if (!Clip || Clip->GetPlayLength()<=0.f || Clip->GetSkeleton()!=Arms->GetSkeletalMeshAsset()->GetSkeleton()) return false;
    HoldObstacle=Target.Obstacle; JumpHoldElapsed=0.f; bPendingJumpHold=true;
    return true;
}

bool UFPSTraversalComponent::ReleaseJumpHold()
{
    const bool bTap=bPendingJumpHold && JumpHoldElapsed<GetDefault<UFPSTraversalSettings>()->HoldToTraverseTime;
    bPendingJumpHold=false; JumpHoldElapsed=0.f; HoldObstacle.Reset();
    return bTap;
}

void UFPSTraversalComponent::AdvanceJumpHold(float DeltaSeconds)
{
    if (!bPendingJumpHold) return;
    auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    const bool bAvailable=C && C->Controller && !C->Controller->IsMoveInputIgnored() &&
        !C->bIsSliding && !C->IsWeaponBusy();
    const auto Target=FindTarget(true,bAvailable);
    if (Target.Action==EFPSTraversalAction::None || !HoldObstacle.IsValid() || Target.Obstacle!=HoldObstacle.Get())
    {
        ReleaseJumpHold(); return;
    }
    JumpHoldElapsed+=FMath::Max(0.f,DeltaSeconds);
    if (JumpHoldElapsed>=GetDefault<UFPSTraversalSettings>()->HoldToTraverseTime)
    {
        ReleaseJumpHold();
        if (TryStart(bAvailable)) { C->JumpBufferRemaining=0.f; C->StopJumping(); }
    }
}

bool UFPSTraversalComponent::TryStart(bool bAvailable)
{
    if (bTraversing) return false;
    InspectJump(bAvailable);
    auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    if (!C || !Arms || GetNetMode()!=NM_Standalone) return false;
    const auto& T=LastJumpTarget;
    const bool bVault=T.Action==EFPSTraversalAction::Vault;
    const bool bHigh=T.Probe.Height>GetDefault<UFPSTraversalSettings>()->VaultMaxHeight;
    if (!bVault && T.Action!=EFPSTraversalAction::Mantle) return false;
    ActiveClip=bVault?VaultClip:(bHigh?ClimbClip:MantleClip);
    if (!ActiveClip || ActiveClip->GetPlayLength()<=0.f || ActiveClip->GetSkeleton()!=Arms->GetSkeletalMeshAsset()->GetSkeleton()) return false;
    ClipDuration=ActiveClip->GetPlayLength(); Elapsed=0;
    CastChecked<UFPSTraversalArmsComponent>(Arms)->ResetSurfaceContact();
    Contact=bVault?.27f:(bHigh?.74f:.345f); Release=bVault?.58f:(bHigh?2.25f:1.1f);
    // Keep the grasp/push timings; compress only the released recovery tail.
    Duration=FMath::Min(ClipDuration,Release+(bVault?.22f:.30f));
    EntryView=(C->Controller?C->Controller->GetControlRotation():C->GetActorRotation()).GetNormalized();
    StartLocation=C->GetActorLocation(); StartCamera=LastCamera=C->FirstPersonCamera->GetComponentLocation();
    StartFoot=StartLocation-FVector(0,0,C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.f);
    Facing=(-T.WallNormal).Rotation().Quaternion();
    const FQuat MeshRotation=Facing*FRotator(0,90,0).Quaternion();
    // Exported Blender +Y forward is UE -Y; mesh yaw +90 maps it onto actor +X.
    const FVector ReferenceEdge=bVault?FVector(1.228593f,-80.0114f,100.f):
        (bHigh?FVector(1.811782f,-67.3522f,250.f):FVector(-7.314725f,-62.0007f,100.f));
    EdgeCorrection=T.FrontEdge-(StartFoot+MeshRotation.RotateVector(ReferenceEdge));
    // High ledges are gripped from their front face; the wrist stays outside the wall.
    if (bHigh) EdgeCorrection-=Facing.RotateVector(FVector(6,0,0));
    CameraLocalOffset=FVector(bVault?-12.f:(bHigh?0.f:8.f),0,3);
    Arms->SetWorldLocationAndRotation(StartFoot,MeshRotation);
    Arms->PlayAnimation(ActiveClip,false); Arms->Stop();
    Arms->SetPosition(ClipDuration,false); Arms->TickAnimation(0,false); Arms->RefreshBoneTransforms();
    const FVector CameraOffset=Facing.RotateVector(CameraLocalOffset);
    EndCorrection=T.Destination+FVector(0,0,C->StandingCameraHeight)-
        (Arms->GetSocketLocation(TEXT("head"))+CameraOffset+EdgeCorrection);
    Arms->SetPosition(0,false); Arms->TickAnimation(0,false); Arms->RefreshBoneTransforms();
    ObstacleTransform=T.Obstacle->GetComponentTransform();
    bSavedControllerYaw=C->bUseControllerRotationYaw; C->bUseControllerRotationYaw=false;
    C->FireReleased(); C->SetAimingState(false); C->bIsSprinting=false;
    C->GetCharacterMovement()->StopMovementImmediately(); C->ConsumeMovementInputVector();
    C->GetCharacterMovement()->DisableMovement(); bTraversing=true;
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_START action=%d height=%.1f clip=%s destination=%s"),(int32)T.Action,T.Probe.Height,*ActiveClip->GetName(),*T.Destination.ToString());
    return true;
}

void UFPSTraversalComponent::Advance(float DeltaSeconds)
{
    AdvanceJumpHold(DeltaSeconds);
    if (bRuntimeAudit) RunRuntimeAudit();
    if (!bTraversing) return;
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    if (!IsValid(LastJumpTarget.Obstacle) || !LastJumpTarget.Obstacle->GetComponentTransform().Equals(ObstacleTransform,.1f)) { Finish(false); return; }
    C->ConsumeMovementInputVector();
    const float Next=FMath::Min(Duration,Elapsed+FMath::Max(0.f,DeltaSeconds));
    // Visit each corner even on a long frame: never sweep diagonally through the wall.
    const float Boundaries[]={Duration*.40f,Duration*.78f,Duration};
    const FVector Points[]={StartLocation,LastJumpTarget.RaisedStart,LastJumpTarget.RaisedEnd,LastJumpTarget.Destination};
    float Cursor=Elapsed;
    for (int32 I=0;I<3;++I)
    {
        const float Begin=I?Boundaries[I-1]:0.f,End=Boundaries[I];
        if (Cursor>=End || Next<=Begin) continue;
        const float Time=FMath::Min(Next,End);
        const FVector Position=FMath::Lerp(Points[I],Points[I+1],Ease(Begin,End,Time));
        FHitResult Hit; C->SetActorLocation(Position,true,&Hit);
        if (Hit.bBlockingHit) { Finish(false); return; }
        Cursor=Time;
    }
    Elapsed=Next;
    if (Elapsed>=Duration) Finish(true);
}

void UFPSTraversalComponent::UpdatePresentation()
{
    if (!bTraversing) return;
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    const float Enter=Ease(0.f,Contact,Elapsed), Exit=Ease(Release,Duration,Elapsed);
    Arms->SetWorldLocation(StartFoot+EdgeCorrection*Enter+EndCorrection*Exit);
    const float SampleTime=Elapsed<=Release?Elapsed:FMath::Lerp(Release,ClipDuration,Ease(Release,Duration,Elapsed));
    const float Plant=Ease(Contact-.12f,Contact,Elapsed)*(1.f-Ease(Release-.12f,Release+.12f,Elapsed));
    CastChecked<UFPSTraversalArmsComponent>(Arms)->SetSurfaceContact(LastJumpTarget.Obstacle,LastJumpTarget.FrontEdge,LastJumpTarget.WallNormal,Plant);
    Arms->SetPosition(SampleTime,false); Arms->TickAnimation(0,false); Arms->RefreshBoneTransforms();
    Arms->UpdateBounds(); Arms->MarkRenderTransformDirty(); Arms->MarkRenderDynamicDataDirty();
    const FVector HeadCamera=Arms->GetSocketLocation(TEXT("head"))+Facing.RotateVector(CameraLocalOffset);
    FVector Camera=FMath::Lerp(StartCamera,HeadCamera,Ease(0,.15f,Elapsed));
    Camera=FMath::Lerp(Camera,LastJumpTarget.Destination+FVector(0,0,C->StandingCameraHeight),Ease(Release,Duration,Elapsed));
    FCollisionQueryParams Params(SCENE_QUERY_STAT(TraversalCamera),false,C);
    FHitResult Hit;
    if (GetWorld()->SweepSingleByChannel(Hit,LastCamera,Camera,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(5),Params))
        Camera=Hit.bStartPenetrating?LastCamera:Hit.Location;
    LastCamera=Camera; C->FirstPersonCamera->SetWorldLocation(Camera);
    const FVector Hands=(Arms->GetSocketLocation(TEXT("hand_l"))+Arms->GetSocketLocation(TEXT("hand_r")))*.5f;
    const float Glance=FMath::Clamp((Hands-Camera).Rotation().Pitch,-40.f,40.f)*Enter*(1.f-Exit);
    FRotator View=(C->Controller?C->Controller->GetControlRotation():Facing.Rotator()).GetNormalized();
    // Clamp the controller itself so mouse deltas cannot accumulate behind the camera.
    const float FreeLook=Ease(Release+.12f,Duration,Elapsed);
    const float YawLimit=FMath::Lerp(FMath::Lerp(45.f,20.f,Enter),180.f,FreeLook);
    const float CentreYaw=Facing.Rotator().Yaw;
    View.Yaw=CentreYaw+FMath::Clamp(FMath::FindDeltaAngleDegrees(CentreYaw,View.Yaw),-YawLimit,YawLimit);
    const float PitchCentre=FMath::Lerp(EntryView.Pitch,0.f,Enter);
    const float PitchLimit=FMath::Lerp(15.f,80.f,FreeLook);
    View.Pitch=FMath::ClampAngle(View.Pitch,PitchCentre-PitchLimit,PitchCentre+PitchLimit);
    View.Roll=0.f;
    if (C->Controller) C->Controller->SetControlRotation(View);
    View.Pitch=FMath::ClampAngle(View.Pitch+Glance,-80.f,80.f); C->FirstPersonCamera->SetWorldRotation(View);
    const float Stow=Ease(0,.12f,Elapsed)*(1.f-Ease(Release+.12f,Duration,Elapsed));
    // Retract out of the view before restoring unrestricted look.
    Arms->AddWorldOffset(FVector(0,0,-35.f*Ease(Release,Release+.12f,Elapsed)));
    Arms->SetVisibility(Elapsed>.06f && Elapsed<Release+.12f);
    C->AKMViewmodel->SetVisibility(C->bInventoryWeaponReady && Stow<.98f,true);
    C->AKMViewmodel->AddLocalOffset(FVector(0,0,-30.f*Stow));
}

void UFPSTraversalComponent::Finish(bool bSuccess)
{
    auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    bTraversing=false;
    if (Arms) Arms->SetVisibility(false);
    if (!C) return;
    LastExitLocation=C->GetActorLocation();
    C->bUseControllerRotationYaw=bSavedControllerYaw;
    C->GetCharacterMovement()->StopMovementImmediately(); C->ConsumeMovementInputVector();
    // Falling performs a fresh floor query, including when the support was removed mid-action.
    auto* Movement=C->GetCharacterMovement();
    FFindFloorResult Floor;
    if (bSuccess) Movement->FindFloor(C->GetActorLocation(),Floor,false);
    Movement->SetMovementMode(bSuccess && Floor.IsWalkableFloor()?MOVE_Walking:MOVE_Falling);
    if (bSuccess && C->Controller && !C->Controller->IsMoveInputIgnored())
    {
        const FRotationMatrix Basis(FRotator(0,C->Controller->GetControlRotation().Yaw,0));
        const FVector Wish=Basis.GetUnitAxis(EAxis::X)*C->MoveInput.Y+Basis.GetUnitAxis(EAxis::Y)*C->MoveInput.X;
        Movement->Velocity=Wish.GetClampedToMaxSize(1.f)*Movement->MaxWalkSpeed;
        C->AddMovementInput(Wish.GetSafeNormal(),FMath::Min(1.f,Wish.Size()));
    }
    C->AKMViewmodel->SetVisibility(C->bInventoryWeaponReady,true);
    C->FireReleased(); C->ResumeWeaponPose();
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_END success=%d location=%s"),bSuccess,*C->GetActorLocation().ToString());
}
void UFPSTraversalComponent::Cancel() { ReleaseJumpHold(); if (bTraversing) Finish(false); }
void UFPSTraversalComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    Cancel(); Super::EndPlay(Reason);
}
