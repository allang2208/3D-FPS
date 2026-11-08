#pragma once

#include "PistolHatchetFingerPose.h"
#include "ReferenceSkeleton.h"

namespace PistolHatchetCarry
{
    // Weapon +X is the cutting edge, +Z runs from the fist to the head.
    // In view space +X is forward and +Y is screen right.
    inline FQuat PalmInView(const FQuat& WeaponInHand)
    {
        const FQuat Crosswise(FVector::ForwardVector,FMath::DegreesToRadians(-86.0));
        const FQuat TowardEye(FVector::UpVector,FMath::DegreesToRadians(20.0));
        // This rotation is about the axe's own shaft. It lowers the poll and
        // brings the palm up with the handle, without lifting the whole axe.
        const FQuat TurnInGrip(FVector::UpVector,FMath::DegreesToRadians(-26.0));
        const FQuat WeaponInView=TowardEye*Crosswise*TurnInGrip;
        return (WeaponInView*WeaponInHand.Inverse()).GetNormalized();
    }

    // Apply in parent space so the equipped rig keeps its own finger lengths and scale.
    inline void FitFingers(const FReferenceSkeleton& Ref,TArray<FTransform>& Pose,float Weight=1.f)
    {
        for(int32 Finger=0;Finger<UE_ARRAY_COUNT(FingerPose);Finger+=3)
        {
            int32 Chain[3],Parents[3];
            FTransform Local[3];
            for(int32 J=0;J<3;++J)
            {
                Chain[J]=Ref.FindBoneIndex(FingerPose[Finger+J].Bone);
                if(!Pose.IsValidIndex(Chain[J]))return;
                Parents[J]=Ref.GetParentIndex(Chain[J]);
                Local[J]=Pose[Chain[J]].GetRelativeTransform(Pose[Parents[J]]);
                Local[J].SetRotation(FQuat::Slerp(Local[J].GetRotation(),FingerPose[Finger+J].Local,Weight).GetNormalized());
            }
            for(int32 J=0;J<3;++J)Pose[Chain[J]]=Local[J]*Pose[Parents[J]];
        }
    }
}
