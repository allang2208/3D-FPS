#include "BowArmsMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void UBowArmsMeshComponent::CaptureEntry(float Seconds)
{
    EntryMesh = GetSkeletalMeshAsset();
    EntryPose = GetComponentSpaceTransforms();
    EntryAge = 0.f;
    EntryDuration = FMath::Max(.001f, Seconds);
}

void UBowArmsMeshComponent::AdvanceEntry(float Delta)
{
    EntryAge += FMath::Max(0.f, Delta);
    if (EntryAge >= EntryDuration) EntryPose.Reset();
}

void UBowArmsMeshComponent::FinalizeBoneTransform()
{
    auto* Mesh = GetSkeletalMeshAsset();
    auto& Pose = GetEditableComponentSpaceTransforms();
    if (Mesh && EntryMesh.Get() == Mesh && Pose.Num() == EntryPose.Num() && !EntryPose.IsEmpty())
    {
        const auto& Ref = Mesh->GetRefSkeleton();
        const TArray<FTransform> Incoming = Pose;
        const float Alpha = FMath::SmoothStep(0.f, 1.f, EntryAge / EntryDuration);
        for (int32 I = 0; I < Pose.Num(); ++I)
        {
            const int32 Parent = Ref.GetParentIndex(I);
            const FTransform A = Parent == INDEX_NONE ? EntryPose[I] : EntryPose[I].GetRelativeTransform(EntryPose[Parent]);
            const FTransform B = Parent == INDEX_NONE ? Incoming[I] : Incoming[I].GetRelativeTransform(Incoming[Parent]);
            FTransform Local;
            Local.Blend(A, B, Alpha);
            Pose[I] = Parent == INDEX_NONE ? Local : Local * Pose[Parent];
        }
    }
    Super::FinalizeBoneTransform();
}
