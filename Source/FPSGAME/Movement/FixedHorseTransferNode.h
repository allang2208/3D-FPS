#pragma once

#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimNodeBase.h"

// Transfer clips are in-place, native skeleton tracks. Blend local rotations before
// the player's usual post-process rig distributes twist to skin and clothing.
struct FFixedHorseTransferNode : FAnimNode_Base
{
    FPoseLink Base, Clip;
    float BodyWeight=0.f, ArmWeight=0.f;
    TBitArray<> UsesArms;

    void Initialize_AnyThread(const FAnimationInitializeContext& C) override
    {
        Base.Initialize(C);
        Clip.Initialize(C);
    }
    void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Base.CacheBones(C);
        Clip.CacheBones(C);
        const FBoneContainer& Bones=C.AnimInstanceProxy->GetRequiredBones();
        UsesArms.Init(false,Bones.GetCompactPoseNumBones());
        const FReferenceSkeleton& Ref=Bones.GetReferenceSkeleton();
        for(int32 I=0;I<UsesArms.Num();++I)
        {
            const FCompactPoseBoneIndex Bone(I);
            const int32 MeshIndex=Bones.MakeMeshPoseIndex(Bone).GetInt();
            const FName Name=Ref.GetBoneName(MeshIndex);
            const auto Parent=Bones.GetParentBoneIndex(Bone);
            UsesArms[I]=Name==TEXT("spine_01")||Name==TEXT("ik_hand_root")||
                (Parent!=INDEX_NONE && UsesArms[Parent.GetInt()]);
        }
    }
    void Update_AnyThread(const FAnimationUpdateContext& C) override
    {
        Base.Update(C);
        if(BodyWeight>ZERO_ANIMWEIGHT_THRESH)Clip.Update(C);
    }
    void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Base.Evaluate(Out);
        if(BodyWeight<=ZERO_ANIMWEIGHT_THRESH)return;
        FPoseContext Fixed(Out);
        Clip.Evaluate(Fixed);
        for(const auto Bone:Out.Pose.ForEachBoneIndex())
            Out.Pose[Bone].BlendWith(Fixed.Pose[Bone],UsesArms[Bone.GetInt()]?ArmWeight:BodyWeight);
    }
};
