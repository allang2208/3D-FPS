#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/BoneReference.h"

// Recover to the live idle arm phase while leaving animated boxes/belts on
// their source pose. Component-space blending preserves the seated palm.
struct FWeaponArmIdleHandoffNode : FAnimNode_Base
{
    FPoseLink Source,Reference;
    float Alpha=0.f;
    FBoneReference Weapon;
    TArray<FCompactPoseBoneIndex> Arms;
    TArray<FTransform> SourceSpace,ReferenceSpace,WriteSpace;
    FWeaponArmIdleHandoffNode(){Weapon.BoneName=TEXT("WPN_root");}
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override
    {Source.Initialize(C);Reference.Initialize(C);}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Source.CacheBones(C);Reference.CacheBones(C);Arms.Reset();
        const auto& Required=C.AnimInstanceProxy->GetRequiredBones();Weapon.Initialize(Required);
        const auto& Ref=Required.GetReferenceSkeleton();
        for(int32 I=0;I<Ref.GetNum();++I)
        {
            const FName Name=Ref.GetBoneName(I);const FString N=Name.ToString();
            if(!(N.EndsWith(TEXT("_l"))||N.EndsWith(TEXT("_r"))))continue;
            if(!(N.StartsWith(TEXT("clavicle"))||N.StartsWith(TEXT("upperarm"))||N.StartsWith(TEXT("lowerarm"))
                ||N.StartsWith(TEXT("hand"))||N.StartsWith(TEXT("thumb"))||N.StartsWith(TEXT("index"))
                ||N.StartsWith(TEXT("middle"))||N.StartsWith(TEXT("ring"))||N.StartsWith(TEXT("pinky"))))continue;
            FBoneReference Bone;Bone.BoneName=Name;Bone.Initialize(Required);
            if(Bone.IsValidToEvaluate(Required))Arms.Add(Bone.GetCompactPoseIndex(Required));
        }
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override
    {Source.Update(C);if(Alpha>0.f)Reference.Update(C);}
    virtual void Evaluate_AnyThread(FPoseContext& Output) override
    {
        Source.Evaluate(Output);const auto& Bones=Output.Pose.GetBoneContainer();
        if(Alpha<=0.f||!Weapon.IsValidToEvaluate(Bones))return;
        FPoseContext Idle(Output);Reference.Evaluate(Idle);const int32 Count=Output.Pose.GetNumBones();
        SourceSpace.SetNumUninitialized(Count);ReferenceSpace.SetNumUninitialized(Count);
        for(int32 I=0;I<Count;++I)
        {
            const FCompactPoseBoneIndex B(I),P=Bones.GetParentBoneIndex(B);
            SourceSpace[I]=P.IsValid()?Output.Pose[B]*SourceSpace[P.GetInt()]:Output.Pose[B];
            ReferenceSpace[I]=P.IsValid()?Idle.Pose[B]*ReferenceSpace[P.GetInt()]:Idle.Pose[B];
        }
        WriteSpace=SourceSpace;const int32 Root=Weapon.GetCompactPoseIndex(Bones).GetInt();
        for(const FCompactPoseBoneIndex B:Arms)
        {
            const FTransform Goal=ReferenceSpace[B.GetInt()].GetRelativeTransform(ReferenceSpace[Root])*SourceSpace[Root];
            WriteSpace[B.GetInt()].Blend(SourceSpace[B.GetInt()],Goal,FMath::Clamp(Alpha,0.f,1.f));
        }
        for(const FCompactPoseBoneIndex B:Arms)
        {
            const auto P=Bones.GetParentBoneIndex(B);
            Output.Pose[B]=P.IsValid()?WriteSpace[B.GetInt()].GetRelativeTransform(WriteSpace[P.GetInt()]):WriteSpace[B.GetInt()];
            Output.Pose[B].NormalizeRotation();
        }
    }
};
