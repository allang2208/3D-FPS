#include "ForgeArmsMeshComponent.h"
#include "Engine/SkinnedAsset.h"

void UForgeArmsMeshComponent::CommitStationPose(const TArray<FTransform>& StationPose,const TArray<int32>& ArmBones)
{
    const auto* Asset=GetSkinnedAsset();if(!Asset||StationPose.Num()!=BoneSpaceTransforms.Num())return;
    const auto& Ref=Asset->GetRefSkeleton();const FTransform ComponentFrame=GetRelativeTransform();
    // Keep the native mesh and inverse binds. The component, not the root bone,
    // carries the body position and facing. All children retain native scale.
    for(int32 I=0;I<StationPose.Num();++I)
    {
        const int32 P=Ref.GetParentIndex(I);
        BoneSpaceTransforms[I]=StationPose[I].GetRelativeTransform(P>=0?StationPose[P]:ComponentFrame);
        BoneSpaceTransforms[I].NormalizeRotation();
    }
    PosedLocalBounds=FBox(ForceInit);
    for(int32 I:ArmBones)PosedLocalBounds+=ComponentFrame.InverseTransformPosition(StationPose[I].GetLocation());
    // Includes the palm surface, upper-arm volume and native shoulder openings.
    PosedLocalBounds=PosedLocalBounds.ExpandBy(10.0);
    MarkRefreshTransformDirty();RefreshBoneTransforms();
}
FBoxSphereBounds UForgeArmsMeshComponent::CalcBounds(const FTransform& LocalToWorld) const
{
    return PosedLocalBounds.IsValid?FBoxSphereBounds(PosedLocalBounds).TransformBy(LocalToWorld):Super::CalcBounds(LocalToWorld);
}
