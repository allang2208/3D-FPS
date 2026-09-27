#include "BowArmsMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"

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

void UBowArmsMeshComponent::PreserveBraceContact()
{
    auto* Mesh = GetSkeletalMeshAsset();
    if (!Mesh || !bBraceContact) return;
    const auto& Ref = Mesh->GetRefSkeleton();
    auto& Pose = GetEditableComponentSpaceTransforms();
    const int32 Grip = Ref.FindBoneIndex(TEXT("bow_grip")), Nock = Ref.FindBoneIndex(TEXT("bow_nock"));
    const int32 Upper = Ref.FindBoneIndex(TEXT("upperarm_r")), Lower = Ref.FindBoneIndex(TEXT("lowerarm_r"));
    const int32 Hand = Ref.FindBoneIndex(TEXT("hand_r"));
    if (Grip == INDEX_NONE || Nock == INDEX_NONE || Upper == INDEX_NONE || Lower == INDEX_NONE || Hand == INDEX_NONE) return;
    const FVector Offset = Pose[Grip].TransformPosition(BraceContact) - Pose[Nock].GetLocation();
    if (Offset.IsNearlyZero(.001f)) return;
    const TArray<FTransform> Incoming = Pose;
    const FVector Shoulder = Incoming[Upper].GetLocation(), OldElbow = Incoming[Lower].GetLocation();
    const FVector OldWrist = Incoming[Hand].GetLocation(), Wrist = OldWrist + Offset;
    const double L1 = FVector::Distance(Shoulder, OldElbow), L2 = FVector::Distance(OldElbow, OldWrist);
    const double Distance = FVector::Distance(Shoulder, Wrist);
    if (Distance < .001 || Distance >= L1 + L2 || Distance <= FMath::Abs(L1 - L2)) return;
    const FVector Axis = (Wrist - Shoulder) / Distance;
    const FVector Bend = (OldElbow - Shoulder - Axis * FVector::DotProduct(OldElbow - Shoulder, Axis)).GetSafeNormal();
    if (Bend.IsNearlyZero()) return;
    const double Along = (L1 * L1 - L2 * L2 + Distance * Distance) / (2. * Distance);
    const FVector Elbow = Shoulder + Axis * Along + Bend * FMath::Sqrt(FMath::Max(0., L1 * L1 - Along * Along));
    const FQuat UpperDelta = FQuat::FindBetweenNormals((OldElbow - Shoulder).GetSafeNormal(), (Elbow - Shoulder).GetSafeNormal());
    const FQuat LowerDelta = FQuat::FindBetweenNormals((OldWrist - OldElbow).GetSafeNormal(), (Wrist - Elbow).GetSafeNormal());
    // Preserve the wrist and all finger rotations. Recompose every descendant,
    // including twist helpers and bow_nock, from its existing local transform.
    for (int32 I = Upper; I < Pose.Num(); ++I)
    {
        if (I == Upper) Pose[I].SetRotation((UpperDelta * Incoming[I].GetRotation()).GetNormalized());
        else if (I == Lower) Pose[I] = FTransform((LowerDelta * Incoming[I].GetRotation()).GetNormalized(), Elbow, Incoming[I].GetScale3D());
        else if (I == Hand) Pose[I].SetLocation(Wrist);
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

void UBowArmsMeshComponent::AdvanceEntry(float Delta)
{
    EntryAge += FMath::Max(0.f, Delta);
    if (EntryAge >= EntryDuration)
    {
        EntryPose.Reset();
        ReleaseReference.Reset();
    }
}

void UBowArmsMeshComponent::FinalizeBoneTransform()
{
    BlendLocomotion();
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
    Super::FinalizeBoneTransform();
}
