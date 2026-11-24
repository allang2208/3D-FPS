#include "BowArmsMeshComponent.h"
#include "BowWeaponComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/PlayerController.h"
#include "SceneView.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "../../Skills/FPSFireballComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Skills/FPSQuickCombatComponent.h"

void UBowArmsMeshComponent::SetLocomotion(UAnimSequence* Walk, UAnimSequence* Run,
    float Phase, float Weight, float Sprint, bool bKeepBraceContact, const FVector& Brace)
{
    WalkCycle = Walk;
    RunCycle = Run;
    GaitPhase = Phase;
    GaitWeight = FMath::Clamp(Weight, 0.f, 1.f);
    SprintWeight = FMath::Clamp(Sprint, 0.f, 1.f);
    bBraceContact = bKeepBraceContact;
    BraceContact = Brace;
}

void UBowArmsMeshComponent::BlendLocomotion()
{
    auto* Mesh = GetSkeletalMeshAsset();
    if (!Mesh || !WalkCycle || !RunCycle || GaitWeight <= KINDA_SMALL_NUMBER) return;
    auto* Skeleton = Mesh->GetSkeleton();
    if (!Skeleton || WalkCycle->GetSkeleton() != Skeleton || RunCycle->GetSkeleton() != Skeleton) return;
    auto& Pose = GetEditableComponentSpaceTransforms();
    const auto& Ref = Mesh->GetRefSkeleton();
    if (LocomotionMesh.Get() != Mesh || LocomotionBoneMap.Num() != Pose.Num())
    {
        LocomotionMesh = Mesh;
        LocomotionBoneMap.SetNum(Pose.Num());
        for (int32 I = 0; I < Pose.Num(); ++I)
            LocomotionBoneMap[I] = Skeleton->GetSkeletonBoneIndexFromMeshBoneIndex(Mesh, I);
    }
    const FAnimExtractContext WalkTime(double(GaitPhase * WalkCycle->GetPlayLength()));
    const FAnimExtractContext RunTime(double(GaitPhase * RunCycle->GetPlayLength()));
    // Save unmodified parent transforms before composing the blended hierarchy.
    const TArray<FTransform> Incoming = Pose;
    for (int32 I = 0; I < Pose.Num(); ++I)
    {
        const int32 Parent = Ref.GetParentIndex(I);
        const FTransform Base = Parent == INDEX_NONE ? Incoming[I] : Incoming[I].GetRelativeTransform(Incoming[Parent]);
        FTransform Result = Base;
        if (LocomotionBoneMap[I] != INDEX_NONE)
        {
            const FSkeletonPoseBoneIndex Bone(LocomotionBoneMap[I]);
            FTransform Walk = Ref.GetRefBonePose()[I], Run = Walk, Cycle;
            WalkCycle->GetBoneTransform(Walk, Bone, WalkTime, false);
            RunCycle->GetBoneTransform(Run, Bone, RunTime, false);
            Cycle.Blend(Walk, Run, SprintWeight);
            Result.Blend(Base, Cycle, GaitWeight);
        }
        Pose[I] = Parent == INDEX_NONE ? Result : Result * Pose[Parent];
    }
}

void UBowArmsMeshComponent::SetContactFit(bool bEnabled,const FVector& ReferenceBrace,
    const FVector& ReferenceDraw,const FVector& TargetBrace,const FVector& TargetDraw)
{
    bContactFit=bEnabled;ContactReferenceBrace=ReferenceBrace;ContactReferenceDraw=ReferenceDraw;
    ContactBraceDelta=TargetBrace-ReferenceBrace;ContactDrawDelta=TargetDraw-ReferenceDraw;
}

void UBowArmsMeshComponent::FitSharedContact()
{
    auto* Mesh=GetSkeletalMeshAsset();
    if(!Mesh||bBraceContact||CastTransfer>0.f||ContactFitWeight<=KINDA_SMALL_NUMBER)return;
    const auto* Bow=PresentationOwner.Get();
    const float Tension=Bow?Bow->DrawMotionWeight()*Bow->AimShakeScale():0.f;
    if(!bContactFit&&Tension<=UE_SMALL_NUMBER)return;
    const auto& Ref=Mesh->GetRefSkeleton();auto& Pose=GetEditableComponentSpaceTransforms();
    const int32 Grip=Ref.FindBoneIndex(TEXT("bow_grip")),Nock=Ref.FindBoneIndex(TEXT("bow_nock"));
    if(!Pose.IsValidIndex(Grip)||!Pose.IsValidIndex(Nock))return;
    FVector Offset=FVector::ZeroVector;
    if(bContactFit)
    {
        const FVector Native=Pose[Grip].InverseTransformPosition(Pose[Nock].GetLocation());
        const FVector Axis=ContactReferenceDraw-ContactReferenceBrace;
        const double Q=Axis.IsNearlyZero()?0.:FMath::Clamp(FVector::DotProduct(Native-ContactReferenceBrace,Axis)/Axis.SizeSquared(),0.,1.);
        Offset=FMath::Lerp(ContactBraceDelta,ContactDrawDelta,Q);
    }
    if(Tension>UE_SMALL_NUMBER)
    {
        const float Time=Bow->VisualTime;
        Offset+=FVector(.20f*FMath::Sin(Time*19.3f), .13f*FMath::Sin(Time*23.2f+.5f),
            .15f*FMath::Sin(Time*16.7f+1.2f))*Tension;
    }
    // The wrist, fingers and nock marker travel together in the existing arm solve.
    MoveRightContact(Pose[Grip].TransformVectorNoScale(Offset)*ContactFitWeight);
}

void UBowArmsMeshComponent::PreserveBraceContact()
{
    auto* Mesh = GetSkeletalMeshAsset();
    if (!Mesh || !bBraceContact) return;
    const auto& Ref = Mesh->GetRefSkeleton();
    auto& Pose = GetEditableComponentSpaceTransforms();
    const int32 Grip = Ref.FindBoneIndex(TEXT("bow_grip")), Nock = Ref.FindBoneIndex(TEXT("bow_nock"));
    if(Grip==INDEX_NONE||Nock==INDEX_NONE)return;
    MoveRightContact(Pose[Grip].TransformPosition(BraceContact)-Pose[Nock].GetLocation());
}

void UBowArmsMeshComponent::MoveRightContact(const FVector& RequestedOffset)
{
    auto* Mesh = GetSkeletalMeshAsset();
    if (!Mesh) return;
    const auto* Bow = PresentationOwner.Get();
    const bool Scoped = Bow && Bow->UsesCompoundOptic();
    const float SightFit = Bow && CastTransfer <= 0.f && (Scoped || Bow->CompoundAimDepthCM > 0.)
        ? FMath::SmoothStep(0.f, .62f, Bow->AimAlpha()) * (bBraceContact ? 1.f : ContactFitWeight) : 0.f;
    const float Clearance = Scoped ? SightFit : 0.f;
    const auto& Ref=Mesh->GetRefSkeleton();auto& Pose=GetEditableComponentSpaceTransforms();
    FVector Offset = RequestedOffset;
    if (SightFit > UE_SMALL_NUMBER)
    {
        const int32 Grip = Ref.FindBoneIndex(TEXT("bow_grip")), Nock = Ref.FindBoneIndex(TEXT("bow_nock"));
        if (Pose.IsValidIndex(Grip) && Pose.IsValidIndex(Nock))
        {
            const FTransform MeshToPivot = GetRelativeTransform();
            const FTransform Mount = Bow->RiserMountFromGrip(Pose[Grip] * MeshToPivot);
            const FVector Contact = Mount.InverseTransformPosition(MeshToPivot.TransformPosition(Pose[Nock].GetLocation() + Offset));
            // Translate the approaching wrist with the brace. Projecting each free-hand
            // sample onto the seated line would flatten its lateral and vertical arc.
            const bool bPickup = Bow->Stage == EBowStage::Nocking ||
                (Bow->Stage == EBowStage::DrawEntry && Bow->bEntryNeedsArrow);
            const FVector Reference = bPickup ? FMath::Lerp(Bow->BraceNockCM, Contact, Bow->PickupSeatAlpha()) : Contact;
            const FVector Delta = Bow->CompoundSightNock(Reference) - Reference;
            Offset += MeshToPivot.InverseTransformVector(Mount.TransformVector(Delta)) * SightFit;
        }
    }
    if (Offset.IsNearlyZero(.001f) && Clearance <= UE_SMALL_NUMBER) return;
    const int32 Upper = Ref.FindBoneIndex(TEXT("upperarm_r")), Lower = Ref.FindBoneIndex(TEXT("lowerarm_r"));
    const int32 Hand = Ref.FindBoneIndex(TEXT("hand_r"));
    if (Upper == INDEX_NONE || Lower == INDEX_NONE || Hand == INDEX_NONE) return;
    const FVector Shoulder = Pose[Upper].GetLocation(), OldElbow = Pose[Lower].GetLocation();
    const FVector OldWrist = Pose[Hand].GetLocation();
    const double L1 = FVector::Distance(Shoulder, OldElbow), L2 = FVector::Distance(OldElbow, OldWrist);
    FVector Wrist = OldWrist + Offset;
    if (SightFit > UE_SMALL_NUMBER && FMath::Min(L1, L2) > .01)
    {
        // Keep the reachable part of the sight fit as the elbow approaches extension.
        const FVector ToWrist = Wrist - Shoulder;
        const double Reach = FMath::Clamp(ToWrist.Size(), FMath::Abs(L1 - L2) + .01, L1 + L2 - .01);
        Wrist = Shoulder + ToWrist.GetSafeNormal(UE_DOUBLE_SMALL_NUMBER, (OldWrist - Shoulder).GetSafeNormal()) * Reach;
    }
    FQuat HandDelta = FQuat::Identity;
    if (Clearance > UE_SMALL_NUMBER)
    {
        const int32 Grip = Ref.FindBoneIndex(TEXT("bow_grip")), Nock = Ref.FindBoneIndex(TEXT("bow_nock"));
        if (Pose.IsValidIndex(Grip) && Pose.IsValidIndex(Nock))
        {
            // Turn the wrist down and out around the finger/string contact, in the bow frame.
            const FVector Lever = OldWrist - Pose[Nock].GetLocation();
            const double Reach = FVector::Distance(Shoulder, Wrist);
            const double Slack = FMath::Max(0., FMath::Min(L1 + L2 - Reach, Reach - FMath::Abs(L1 - L2)) - .01);
            const FQuat Turn = FRotator(22., -14., 0.).Quaternion();
            const double Weight = FMath::Min(double(Clearance), Slack / FMath::Max(.001, Lever.Size() * Turn.GetAngle()));
            const FQuat Frame = Pose[Grip].GetRotation();
            HandDelta = (Frame * FQuat::Slerp(FQuat::Identity, Turn, Weight) * Frame.Inverse()).GetNormalized();
            Wrist += HandDelta.RotateVector(Lever) - Lever;
        }
    }
    const TArray<FTransform> Incoming = Pose;
    const double Distance = FVector::Distance(Shoulder, Wrist);
    if (Distance < .001 || Distance >= L1 + L2 || Distance <= FMath::Abs(L1 - L2)) return;
    const FVector Axis = (Wrist - Shoulder) / Distance;
    const FVector Bend = (OldElbow - Shoulder - Axis * FVector::DotProduct(OldElbow - Shoulder, Axis)).GetSafeNormal();
    if (Bend.IsNearlyZero()) return;
    const double Along = (L1 * L1 - L2 * L2 + Distance * Distance) / (2. * Distance);
    const FVector Elbow = Shoulder + Axis * Along + Bend * FMath::Sqrt(FMath::Max(0., L1 * L1 - Along * Along));
    const FQuat UpperDelta = FQuat::FindBetweenNormals((OldElbow - Shoulder).GetSafeNormal(), (Elbow - Shoulder).GetSafeNormal());
    const FQuat LowerDelta = FQuat::FindBetweenNormals((OldWrist - OldElbow).GetSafeNormal(), (Wrist - Elbow).GetSafeNormal());
    // Recompose the finger curl, twist helpers and nock from the solved hand.
    for (int32 I = Upper; I < Pose.Num(); ++I)
    {
        if (I == Upper) Pose[I].SetRotation((UpperDelta * Incoming[I].GetRotation()).GetNormalized());
        else if (I == Lower) Pose[I] = FTransform((LowerDelta * Incoming[I].GetRotation()).GetNormalized(), Elbow, Incoming[I].GetScale3D());
        else if (I == Hand) Pose[I] = FTransform((HandDelta * Incoming[I].GetRotation()).GetNormalized(), Wrist, Incoming[I].GetScale3D());
        else
        {
            const int32 Parent = Ref.GetParentIndex(I);
            if (Parent != INDEX_NONE)
                Pose[I] = Incoming[I].GetRelativeTransform(Incoming[Parent]) * Pose[Parent];
        }
    }
}

void UBowArmsMeshComponent::CaptureEntry(float Seconds)
{
    EntryMesh = GetSkeletalMeshAsset();
    EntryPose = GetComponentSpaceTransforms();
    EntryAge = 0.f;
    EntryDuration = FMath::Max(.001f, Seconds);
    bReleaseHandoff = false;
    bCarryHandoff = false;
    ReleaseReference.Reset();
}

void UBowArmsMeshComponent::CaptureCarry(float Seconds)
{
    CaptureEntry(Seconds);
    bCarryHandoff = true;
}

void UBowArmsMeshComponent::CaptureRelease(float Seconds)
{
    CaptureEntry(Seconds);
    bReleaseHandoff = true;
}

bool UBowArmsMeshComponent::IsReturningLeftHand() const
{return !LeftReturnPose.IsEmpty()&&LeftReturnMesh.Get()==GetSkeletalMeshAsset()&&LeftReturnAge<LeftReturnSeconds;}

void UBowArmsMeshComponent::CaptureLeftReturn(float Seconds)
{
    auto* Mesh=GetSkeletalMeshAsset();if(!Mesh)return;
    LeftReturnMesh=Mesh;LeftReturnPose=GetComponentSpaceTransforms();LeftReturnBones.Reset();
    const auto& Ref=Mesh->GetRefSkeleton();const int32 Shoulder=Ref.FindBoneIndex(TEXT("clavicle_l"));
    if(Shoulder<0||LeftReturnPose.Num()!=Ref.GetNum()){ClearLeftReturn();return;}
    for(int32 I=0;I<Ref.GetNum();++I)if(I==Shoulder||Ref.BoneIsChildOf(I,Shoulder))LeftReturnBones.Add(I);
    // Convert backwards so each parent still has its component transform.
    for(int32 I=LeftReturnPose.Num()-1;I>0;--I)
        if(const int32 P=Ref.GetParentIndex(I);P>=0)LeftReturnPose[I]=LeftReturnPose[I].GetRelativeTransform(LeftReturnPose[P]);
    LeftReturnAge=0.f;LeftReturnSeconds=FMath::Max(.001f,Seconds);
}

void UBowArmsMeshComponent::BlendLeftReturn()
{
    if(!IsReturningLeftHand())return;
    auto& Pose=GetEditableComponentSpaceTransforms();if(Pose.Num()!=LeftReturnPose.Num())return;
    const auto Incoming=Pose;const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    const float Weight=FPotionUseMotion::Ease(LeftReturnAge/LeftReturnSeconds);
    for(int32 I:LeftReturnBones)
    {
        const int32 P=Ref.GetParentIndex(I);
        const FTransform Target=P<0?Incoming[I]:Incoming[I].GetRelativeTransform(Incoming[P]);
        FTransform Mixed;Mixed.Blend(LeftReturnPose[I],Target,Weight);Pose[I]=P<0?Mixed:Mixed*Pose[P];
    }
}

void UBowArmsMeshComponent::AdvanceEntry(float Delta)
{
    EntryAge += FMath::Max(0.f, Delta);
    LeftReturnAge+=FMath::Max(0.f,Delta);
    if(LeftReturnAge>=LeftReturnSeconds)ClearLeftReturn();
    if (EntryAge >= EntryDuration)
    {
        EntryPose.Reset();
        ReleaseReference.Reset();
    }
}

void UBowArmsMeshComponent::KeepSupportShoulderBelowView()
{
    const auto* Bow = PresentationOwner.Get();
    auto* Mesh = GetSkeletalMeshAsset();
    if (!Bow || !Bow->Camera || !Mesh || CastTransfer > 0.f || Bow->Stage == EBowStage::QuickCombat) return;
    if (!(Bow->Stage == EBowStage::Nocking || Bow->Stage == EBowStage::DrawEntry ||
        Bow->bArrowNocked || Bow->HipAimProgress > 0.f)) return;

    const auto& Ref = Mesh->GetRefSkeleton();
    auto& Pose = GetEditableComponentSpaceTransforms();
    static const FName ClavicleName(TEXT("clavicle_l")), ShoulderName(TEXT("upperarm_l")), WristName(TEXT("hand_l"));
    static const FName GripName(TEXT("bow_grip")), NockName(TEXT("bow_nock"));
    const int32 Shoulder = Ref.FindBoneIndex(ShoulderName), Wrist = Ref.FindBoneIndex(WristName);
    const int32 Grip = Ref.FindBoneIndex(GripName), Nock = Ref.FindBoneIndex(NockName);
    if (Pose.Num() != Ref.GetNum() || !Pose.IsValidIndex(Shoulder) || !Pose.IsValidIndex(Wrist) ||
        !Pose.IsValidIndex(Grip) || !Pose.IsValidIndex(Nock)) return;

    // UpdatePoseLayers installs the pivot after bone finalization. Solve from
    // the incoming markers so a quick nock never uses the previous frame's aim.
    const FTransform GripInPivot = Pose[Grip] * GetRelativeTransform();
    const FTransform Mount = Bow->RiserMountFromGrip(GripInPivot);
    const FVector HandInMount = Mount.InverseTransformPosition(GetRelativeTransform().TransformPosition(Pose[Nock].GetLocation()));
    const FVector Tail = Bow->Stage == EBowStage::Release || Bow->Stage == EBowStage::Recover
        ? Bow->ReleasedNockCM : Bow->NockPoint(&HandInMount);
    const FTransform MeshToCamera = GetRelativeTransform() * Bow->PoseLayerTransform(GripInPivot, Mount, Tail);
    const FVector RootInView = MeshToCamera.TransformPosition(Pose[Shoulder].GetLocation());
    // The native V7 left opening extends 9.3 cm from upperarm_l. Include
    // the sleeve thickness and a small clearance from the bottom of the view.
    constexpr double RimClearanceCM = 13.;
    if (RootInView.X < -RimClearanceCM) return;

    const auto* Pawn = Cast<APawn>(GetOwner());
    const auto* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    const auto* Local = PC ? PC->GetLocalPlayer() : nullptr;
    const auto& Camera = *Bow->Camera;
    const bool bFirstPersonLens = FirstPersonPrimitiveType == EFirstPersonPrimitiveType::FirstPerson && Camera.bEnableFirstPersonFieldOfView;
    const double ViewFOV = bFirstPersonLens ? Camera.FirstPersonFieldOfView : Camera.FieldOfView;
    const double HalfTan = FMath::Tan(FMath::DegreesToRadians(ViewFOV) * .5);
    double VerticalTangent = HalfTan / FMath::Max(.1, double(Camera.AspectRatio));
    FSceneViewProjectionData Projection;
    if (Local && Local->ViewportClient && Local->ViewportClient->Viewport &&
        Local->GetProjectionData(Local->ViewportClient->Viewport, Projection) && Projection.ProjectionMatrix.M[1][1] > UE_SMALL_NUMBER)
    {
        const double ProjectionFOV = PC->PlayerCameraManager ? PC->PlayerCameraManager->GetFOVAngle() : Camera.FieldOfView;
        const double ProjectionTan = FMath::Tan(FMath::DegreesToRadians(ProjectionFOV) * .5);
        VerticalTangent = HalfTan / (FMath::Max(.001, ProjectionTan) * Projection.ProjectionMatrix.M[1][1]);
    }
    const FVector Normal = FVector(VerticalTangent, 0., 1.).GetSafeNormal();
    if (FVector::DotProduct(RootInView, Normal) <= -RimClearanceCM) return;

    // Rotate the complete bent arm around its fixed wrist. Moving the root
    // alone stretches the elbow and separates a sleeve from the hand.
    const FVector WristInView = MeshToCamera.TransformPosition(Pose[Wrist].GetLocation());
    const FVector Reach = RootInView - WristInView;
    const double Length = Reach.Size();
    if (Length < UE_SMALL_NUMBER) return;
    const double Height = FMath::Clamp(-RimClearanceCM - FVector::DotProduct(WristInView, Normal), -Length, Length);
    const FVector Tangent = FVector::VectorPlaneProject(Reach, Normal).GetSafeNormal(UE_SMALL_NUMBER, -FVector::RightVector);
    const FVector Target = Normal * Height + Tangent * FMath::Sqrt(FMath::Max(0., Length * Length - Height * Height));
    const FQuat ViewDelta = FQuat::FindBetweenNormals(Reach / Length, Target / Length);
    const FQuat Delta = (MeshToCamera.GetRotation().Inverse() * ViewDelta * MeshToCamera.GetRotation()).GetNormalized();
    if (SupportArmMesh.Get() != Mesh)
    {
        SupportArmMesh = Mesh;
        SupportArmBones.Reset();
        const int32 Clavicle = Ref.FindBoneIndex(ClavicleName);
        if (Clavicle != INDEX_NONE)
            for (int32 I = Clavicle; I < Ref.GetNum(); ++I)
                if ((I == Clavicle || Ref.BoneIsChildOf(I, Clavicle)) && I != Wrist && !Ref.BoneIsChildOf(I, Wrist))
                    SupportArmBones.Add(I);
    }
    const FVector Pivot = Pose[Wrist].GetLocation();
    for (int32 I : SupportArmBones)
    {
        Pose[I].SetLocation(Pivot + Delta.RotateVector(Pose[I].GetLocation() - Pivot));
        Pose[I].SetRotation((Delta * Pose[I].GetRotation()).GetNormalized());
    }
}

void UBowArmsMeshComponent::FinalizeBoneTransform()
{
    BlendLocomotion();
    FitSharedContact();
    // Correct only the incoming carry pose. The existing handoff must retain
    // a cancelled full draw while it eases back to brace, rather than snapping.
    PreserveBraceContact();
    auto* Mesh = GetSkeletalMeshAsset();
    auto& Pose = GetEditableComponentSpaceTransforms();
    if (Mesh && EntryMesh.Get() == Mesh && Pose.Num() == EntryPose.Num() && !EntryPose.IsEmpty())
    {
        const auto& Ref = Mesh->GetRefSkeleton();
        const TArray<FTransform> Incoming = Pose;
        // The caller samples Release[0] first. Its local pose is the reference
        // for motion deltas; a half draw must not jump to full draw on release.
        if ((bReleaseHandoff || bCarryHandoff) && ReleaseReference.IsEmpty()) ReleaseReference = Incoming;
        const float Alpha = FMath::SmoothStep(0.f, 1.f, EntryAge / EntryDuration);
        // V15 holds the follow-through for 0.10/0.64 of the release clip before
        // returning to idle. Fade the draw offset on that same recovery curve.
        const float Recovery = FMath::SmoothStep(0.f, 1.f, (EntryAge / EntryDuration - .15625f) / .84375f);
        const float CarryT = FMath::Clamp(EntryAge / EntryDuration, 0.f, 1.f);
        const float CarryFade = CarryT * CarryT * CarryT * (10.f + CarryT * (-15.f + 6.f * CarryT));
        for (int32 I = 0; I < Pose.Num(); ++I)
        {
            const int32 Parent = Ref.GetParentIndex(I);
            const FTransform A = Parent == INDEX_NONE ? EntryPose[I] : EntryPose[I].GetRelativeTransform(EntryPose[Parent]);
            const FTransform B = Parent == INDEX_NONE ? Incoming[I] : Incoming[I].GetRelativeTransform(Incoming[Parent]);
            FTransform Local;
            if (bReleaseHandoff || bCarryHandoff)
            {
                const FTransform Start = Parent == INDEX_NONE ? ReleaseReference[I]
                    : ReleaseReference[I].GetRelativeTransform(ReleaseReference[Parent]);
                Local = B;
                // A moving pickup is sampled at full speed. Only the mismatch
                // with its first pose fades, avoiding a frozen-arm crossfade.
                const float Remaining = 1.f - (bCarryHandoff ? CarryFade : Recovery);
                const FQuat Offset = (A.GetRotation() * Start.GetRotation().Inverse()).GetNormalized();
                Local.SetRotation((FQuat::Slerp(FQuat::Identity, Offset, Remaining)
                    * B.GetRotation()).GetNormalized());
                Local.AddToTranslation((A.GetTranslation() - Start.GetTranslation()) * Remaining);
            }
            else Local.Blend(A, B, Alpha);
            Pose[I] = Parent == INDEX_NONE ? Local : Local * Pose[Parent];
        }
    }
    if(Mesh&&CastTransfer>0.f)
    {
        if(CastMesh.Get()!=Mesh){CastMesh=Mesh;CastHands.Initialize(Mesh->GetRefSkeleton());}
        const int32 Grip=GetBoneIndex(TEXT("bow_grip"));
        if(Pose.IsValidIndex(Grip))
        {
            const FTransform Mount=CastHands.Apply(Pose,Pose[Grip],CastTransfer);
            BlendLeftReturn();
            // The weapon marker stays with the supporting right hand while
            // the shared spell layer is free to move the left arm and fingers.
            if(auto* Magic=GetOwner()->FindComponentByClass<UFPSFireballComponent>();Magic&&Magic->IsOccupyingLeftHand()&&!Magic->IsBowHandTransferActive())ApplyCastPose(Magic);
            if(auto* Use=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();Use&&Use->UsesBowSupport())Use->ApplyHandPose(*this);
            Pose[Grip]=Mount;
        }
    }
    // The entire assembly recoils together, including its contact markers.
    // Applying this to the sampled pose keeps palms fixed to the bow and
    // includes the recoil in the existing replicated native-hand samples.
    if(const auto* Quick=GetOwner()?GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>():nullptr)
    {
        const float Recoil=Quick->GetBowRecoilCM();
        if(!FMath::IsNearlyZero(Recoil))
        {
            const FVector Offset=GetRelativeTransform().InverseTransformVector(FVector(Recoil,0,0));
            for(FTransform& Bone:Pose)Bone.AddToTranslation(Offset);
        }
    }
    // Bow owns its other overlays; do not invoke potion/door/weapon-belt layers.
    KeepSupportShoulderBelowView();
    USkeletalMeshComponent::FinalizeBoneTransform();
}
