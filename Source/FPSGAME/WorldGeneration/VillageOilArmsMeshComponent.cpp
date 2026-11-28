#include "VillageOilArmsMeshComponent.h"
#include "Engine/SkinnedAsset.h"

void UVillageOilArmsMeshComponent::CommitStationPose(const TArray<FTransform>& StationPose, const TArray<int32>& ArmBones)
{
	const USkinnedAsset* Asset = GetSkinnedAsset();
	if (!Asset || StationPose.Num() != Asset->GetRefSkeleton().GetNum())
	{
		return;
	}

	const FTransform ComponentFrame = GetRelativeTransform();
	PendingPose.SetNum(StationPose.Num());
	for (int32 I = 0; I < StationPose.Num(); ++I)
	{
		PendingPose[I] = StationPose[I].GetRelativeTransform(ComponentFrame);
		PendingPose[I].NormalizeRotation();
	}

	PosedLocalBounds = FBox(ForceInit);
	for (const int32 BoneIndex : ArmBones)
	{
		if (StationPose.IsValidIndex(BoneIndex))
		{
			PosedLocalBounds += ComponentFrame.InverseTransformPosition(StationPose[BoneIndex].GetLocation());
		}
	}
	if (PosedLocalBounds.IsValid)
	{
		PosedLocalBounds = PosedLocalBounds.ExpandBy(14.0);
	}

	TickAnimation(0.f, false);
	RefreshBoneTransforms();
	UpdateBounds();
}

void UVillageOilArmsMeshComponent::FinalizeBoneTransform()
{
	TArray<FTransform>& EditableTransforms = GetEditableComponentSpaceTransforms();
	if (PendingPose.Num() > 0 && EditableTransforms.Num() == PendingPose.Num())
	{
		EditableTransforms = PendingPose;
	}
	Super::FinalizeBoneTransform();
}

FBoxSphereBounds UVillageOilArmsMeshComponent::CalcBounds(const FTransform& LocalToWorld) const
{
	return PosedLocalBounds.IsValid
		? FBoxSphereBounds(PosedLocalBounds).TransformBy(LocalToWorld)
		: Super::CalcBounds(LocalToWorld);
}
