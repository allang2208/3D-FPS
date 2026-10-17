#include "M870TacticalAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

FTransform M870TacticalAssets::Mount(const USkeletalMeshComponent* Host)
{
    const auto& Ref=Host->GetSkeletalMeshAsset()->GetRefSkeleton();
    FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root=Root*Ref.GetRefBonePose()[I];
    // Static tube clamp ahead of the moving pump. The source rig root carries
    // scale 100; full relative conversion preserves centimetre-sized devices.
    const FQuat Forward=FRotationMatrix::MakeFromXZ(FVector(0,-1,0),FVector::UpVector).ToQuat();
    return FTransform(Forward,FVector(0,-35.5f,-80.5f)).GetRelativeTransform(Root);
}
