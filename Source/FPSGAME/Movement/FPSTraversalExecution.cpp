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

bool UFPSTraversalComponent::TryStart(bool bAvailable, bool bLogRejection)
{
    if (bTraversing) return false;
    auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    InspectJump(bAvailable && C && C->Controller && !C->Controller->IsMoveInputIgnored());
    if (!C || !Arms || GetNetMode()!=NM_Standalone) return false;
    const auto& T=LastJumpTarget;
    const bool bVault=T.Action==EFPSTraversalAction::Vault;
    const bool bHigh=T.Probe.Height>GetDefault<UFPSTraversalSettings>()->VaultMaxHeight;
    if (!bVault && T.Action!=EFPSTraversalAction::Mantle)
    {
        if (bLogRejection || bDebugQueries) UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_INPUT_REJECT reason=%s available=%d grounded=%d distance=%.2f facing=%.3f height=%.1f obstacle=%s mobility=%d pos=%s"),
            *T.Reason,bAvailable,T.Probe.bStandingGrounded,T.Probe.EdgeDistance,T.Probe.FacingDot,T.Probe.Height,
            *GetNameSafe(T.Obstacle),T.Obstacle?(int32)T.Obstacle->Mobility:-1,*C->GetActorLocation().ToString());
        return false;
    }
    ActiveClip=bVault?VaultClip:(bHigh?ClimbClip:MantleClip);
    if (!ActiveClip || ActiveClip->GetPlayLength()<=0.f || ActiveClip->GetSkeleton()!=Arms->GetSkeletalMeshAsset()->GetSkeleton()) return false;
    ClipDuration=ActiveClip->GetPlayLength(); Elapsed=0;
    bReturningCamera=false; bLastTraversalSucceeded=false;
    PlaybackRate=bVault?GetDefault<UFPSTraversalSettings>()->VaultPlaybackRate:1.f;
    CastChecked<UFPSTraversalArmsComponent>(Arms)->ResetSurfaceContact();
    Contact=bVault?.27f:(bHigh?.74f:.345f); Release=bVault?.58f:(bHigh?2.25f:1.1f);
    // Keep the grasp/push timings; compress only the released recovery tail.
    Duration=FMath::Min(ClipDuration,Release+(bVault?.22f:.30f));
    EntryVelocity=T.Probe.bAirborne?C->GetVelocity():FVector::ZeroVector;
    EntryView=(C->Controller?C->Controller->GetControlRotation():C->GetActorRotation()).GetNormalized();
    StartLocation=C->GetActorLocation(); StartCamera=LastCamera=C->FirstPersonCamera->GetComponentLocation();
    LastCameraRotation=C->FirstPersonCamera->GetComponentQuat();
    const float LiftDistance=T.RaisedStart.Z-StartLocation.Z;
    EntryLiftTangent=LiftDistance>1.f?FMath::Clamp(EntryVelocity.Z*(Duration*.4f/PlaybackRate)/LiftDistance,0.f,3.f):0.f;
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
    SupportTransforms.Reset(T.Supports.Num());
    for (const auto& Support:T.Supports) SupportTransforms.Add(Support->GetComponentTransform());
    bSavedControllerYaw=C->bUseControllerRotationYaw; C->bUseControllerRotationYaw=false;
    C->FireReleased(); C->SetAimingState(false); C->bIsSprinting=false;
    C->GetCharacterMovement()->StopMovementImmediately(); C->ConsumeMovementInputVector();
    C->JumpBufferRemaining=0.f; C->StopJumping(); bJumpRequestConsumed=true;
    C->GetCharacterMovement()->DisableMovement(); bTraversing=true;
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_START action=%d height=%.1f clip=%s destination=%s rate=%.2f seconds=%.3f air=%d entry_vz=%.1f"),(int32)T.Action,T.Probe.Height,*ActiveClip->GetName(),*T.Destination.ToString(),PlaybackRate,Duration/PlaybackRate,T.Probe.bAirborne,EntryVelocity.Z);
    return true;
}

void UFPSTraversalComponent::Advance(float DeltaSeconds)
{
    if (bRuntimeAudit) RunRuntimeAudit();
    if (!bTraversing) TryAirCatch();
    if (!bTraversing) return;
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    if (!IsBlockingSupport(LastJumpTarget.Obstacle) || !LastJumpTarget.Obstacle->GetComponentTransform().Equals(ObstacleTransform,.1f)) { Finish(false); return; }
    for (int32 I=0;I<LastJumpTarget.Supports.Num();++I)
        if (!IsBlockingSupport(LastJumpTarget.Supports[I]) ||
            !LastJumpTarget.Supports[I]->GetComponentTransform().Equals(SupportTransforms[I],.1f))
        { Finish(false); return; }
    C->ConsumeMovementInputVector();
    // One source-time clock accelerates body, camera, grasp and release together.
    const float Next=FMath::Min(Duration,Elapsed+FMath::Max(0.f,DeltaSeconds)*PlaybackRate);
    // Visit each corner even on a long frame: never sweep diagonally through the wall.
    const float Boundaries[]={Duration*.40f,Duration*.78f,Duration};
    const FVector Points[]={StartLocation,LastJumpTarget.RaisedStart,LastJumpTarget.RaisedEnd,LastJumpTarget.Destination};
    float Cursor=Elapsed;
    for (int32 I=0;I<3;++I)
    {
        const float Begin=I?Boundaries[I-1]:0.f,End=Boundaries[I];
        if (Cursor>=End || Next<=Begin) continue;
        const float Time=FMath::Min(Next,End);
        float Alpha=Ease(Begin,End,Time);
        if (I==0 && EntryLiftTangent>0.f)
        {
            const float T=FMath::Clamp(Time/End,0.f,1.f);
            // Monotone Hermite: carry compatible upward velocity into the lift,
            // ease to zero at the corner, never overshoot the swept segment.
            Alpha+=EntryLiftTangent*T*(1.f-T)*(1.f-T);
        }
        const FVector Position=FMath::Lerp(Points[I],Points[I+1],Alpha);
        FHitResult Hit; C->SetActorLocation(Position,true,&Hit);
        if (Hit.bBlockingHit) { Finish(false); return; }
        Cursor=Time;
    }
    Elapsed=Next;
    if (Elapsed>=Duration) Finish(true);
}

void UFPSTraversalComponent::UpdatePresentation(float DeltaSeconds)
{
    if (!bTraversing) { if (bReturningCamera) UpdateCameraReturn(DeltaSeconds); return; }
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    const float Enter=Ease(0.f,Contact,Elapsed), Exit=Ease(Release,Duration,Elapsed);
    Arms->SetWorldLocation(StartFoot+EdgeCorrection*Enter+EndCorrection*Exit);
    const float SampleTime=Elapsed<=Release?Elapsed:FMath::Lerp(Release,ClipDuration,Ease(Release,Duration,Elapsed));
    const float Plant=Ease(Contact-.12f,Contact,Elapsed)*(1.f-Ease(Release-.12f,Release+.12f,Elapsed));
    CastChecked<UFPSTraversalArmsComponent>(Arms)->SetSurfaceContact(LastJumpTarget,Plant);
    Arms->SetPosition(SampleTime,false); Arms->TickAnimation(0,false); Arms->RefreshBoneTransforms();
    Arms->UpdateBounds(); Arms->MarkRenderTransformDirty(); Arms->MarkRenderDynamicDataDirty();
    const FVector HeadCamera=Arms->GetSocketLocation(TEXT("head"))+Facing.RotateVector(CameraLocalOffset);
    const float EntryTime=Elapsed/PlaybackRate;
    const FVector EntryCamera=StartCamera+FVector(0,0,EntryVelocity.Z)*EntryTime*(1.f-Ease(0.f,.15f,EntryTime));
    FVector Camera=FMath::Lerp(EntryCamera,HeadCamera,Ease(0,.15f,Elapsed));
    Camera=FMath::Lerp(Camera,LastJumpTarget.Destination+FVector(0,0,C->StandingCameraHeight),Ease(Release,Duration,Elapsed));
    Camera=SweepCamera(LastCamera,Camera);
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
    LastCameraRotation=C->FirstPersonCamera->GetComponentQuat();
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
    if (bSuccess)
    {
        Movement->FindFloor(C->GetActorLocation(),Floor,false);
        const auto* Capsule=C->GetCapsuleComponent();
        const FCollisionQueryParams Query(SCENE_QUERY_STAT(TraversalFinish),false,C);
        bSuccess=Floor.IsWalkableFloor() && Floor.GetDistanceToFloor()<=12.f &&
            IsBlockingSupport(Floor.HitResult.GetComponent()) &&
            !GetWorld()->OverlapBlockingTestByProfile(C->GetActorLocation(),Capsule->GetComponentQuat(),
                Capsule->GetCollisionProfileName(),Capsule->GetCollisionShape(),Query);
    }
    bLastTraversalSucceeded=bSuccess;
    Movement->SetMovementMode(bSuccess?MOVE_Walking:MOVE_Falling);
    if (!bSuccess)
    {
        // Resume physics immediately. Only the rendered view returns gradually.
        bReturningCamera=true; CameraReturnSpeed=0.f; CameraReturnCapsule=C->GetActorLocation();
        C->FirstPersonCamera->SetWorldLocationAndRotation(LastCamera,LastCameraRotation);
    }
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
void UFPSTraversalComponent::Cancel() { bJumpHeld=false; bJumpRequestConsumed=true; if (bTraversing) Finish(false); }
void UFPSTraversalComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    Cancel(); Super::EndPlay(Reason);
}
