#pragma once
#include "Animation/BoneReference.h"
#include "BonePose.h"

// Spread the pelvis-to-attack correction through the native spine. The upper
// chest keeps the authored attack orientation and every joint keeps its length.
struct FFPSBodySpineBlend
{
    FBoneReference Lower{TEXT("spine_01")}, Upper{TEXT("spine_05")};
    TArray<FCompactPoseBoneIndex,TInlineAllocator<5>> Chain;

    void Initialize(const FBoneContainer& Bones)
    {
        Chain.Reset();
        Lower.Initialize(Bones);
        Upper.Initialize(Bones);
        if (!Lower.IsValidToEvaluate(Bones) || !Upper.IsValidToEvaluate(Bones)) return;
        const auto First=Lower.GetCompactPoseIndex(Bones);
        for (auto Bone=Upper.GetCompactPoseIndex(Bones); Bone!=INDEX_NONE; Bone=Bones.GetParentBoneIndex(Bone))
        {
            Chain.Insert(Bone,0);
            if (Bone==First) return;
        }
        Chain.Reset();
    }

    void Distribute(FCSPose<FCompactPose>& Pose,const FQuat& NaturalLowerRotation) const
    {
        if (Chain.Num()<2) return;
        const auto& Bones=Pose.GetPose().GetBoneContainer();
        TArray<FQuat,TInlineAllocator<5>> Rotations;
        for (const auto Bone:Chain) Rotations.Add(Pose.GetComponentSpaceTransform(Bone).GetRotation());
        const auto Parent=Bones.GetParentBoneIndex(Chain[0]);
        const FQuat Natural=Pose.GetComponentSpaceTransform(Parent).GetRotation()*NaturalLowerRotation;
        const FQuat Correction=(Natural*Rotations[0].Inverse()).GetNormalized();
        for (int32 I=0; I<Chain.Num(); ++I)
        {
            const float Fraction=float(I+1)/Chain.Num();
            const FQuat Rotation=FQuat::Slerp(Correction,FQuat::Identity,Fraction)*Rotations[I];
            auto Transform=Pose.GetComponentSpaceTransform(Chain[I]);
            Transform.SetRotation(Rotation.GetNormalized());
            TArray<FBoneTransform,TInlineAllocator<1>> Change;
            Change.Emplace(Chain[I],Transform);
            Pose.LocalBlendCSBoneTransforms(Change,1.f);
        }
    }
};
