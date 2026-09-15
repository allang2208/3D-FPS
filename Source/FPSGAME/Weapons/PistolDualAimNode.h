#pragma once

#include "Animation/AnimNodeBase.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/BoneReference.h"

// Each dual mesh contains one anatomical arm. A bounded rotation of the entire
// posed rig preserves every wrist/elbow angle, skin helper and gun contact.
// Solve from a neutral reference so recoil and reload motion are not cancelled.
struct FPistolDualAimNode : FAnimNode_Base
{
    FPoseLink Source, Reference;
    FBoneReference Shoulder[2], Front, Rear, Muzzle;
    FVector Target=FVector::ZeroVector;
    float Weight=0.f;
    int32 Side=0;
    bool bEnabled=false;

    FPistolDualAimNode()
    {
        Shoulder[0].BoneName=TEXT("upperarm_r");Shoulder[1].BoneName=TEXT("upperarm_l");
        Front.BoneName=TEXT("WPN_FrontSight");Rear.BoneName=TEXT("WPN_RearSight");Muzzle.BoneName=TEXT("WPN_SOCKET_Muzzle");
    }
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override
    { Source.Initialize(Context);Reference.Initialize(Context); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
    {
        Source.CacheBones(Context);Reference.CacheBones(Context);
        const auto& Bones=Context.AnimInstanceProxy->GetRequiredBones();
        for(auto* Bone:{&Shoulder[0],&Shoulder[1],&Front,&Rear,&Muzzle})
            if(Bones.GetReferenceSkeleton().FindBoneIndex(Bone->BoneName)!=INDEX_NONE)Bone->Initialize(Bones);
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override
    {
        Source.Update(Context);
        if(bEnabled && Weight>SMALL_NUMBER)Reference.Update(Context);
    }
    static FTransform ComponentPose(const FCompactPose& Pose,FCompactPoseBoneIndex Index)
    {
        FTransform Result=Pose[Index];
        for(auto Parent=Pose.GetParentBoneIndex(Index);Parent.GetInt()!=INDEX_NONE;Parent=Pose.GetParentBoneIndex(Parent))Result=Result*Pose[Parent];
        return Result;
    }
    virtual void Evaluate_AnyThread(FPoseContext& Output) override
    {
        Source.Evaluate(Output);
        if(!bEnabled || Weight<=SMALL_NUMBER)return;
        const auto& Bones=Output.Pose.GetBoneContainer();
        const auto& Arm=Shoulder[Side];
        if(!Arm.IsValidToEvaluate(Bones) || !Front.IsValidToEvaluate(Bones) || !Rear.IsValidToEvaluate(Bones) || !Muzzle.IsValidToEvaluate(Bones))return;
        FPoseContext Neutral(Output);Reference.Evaluate(Neutral);
        const auto Position=[&](const FBoneReference& Bone){return ComponentPose(Neutral.Pose,Bone.GetCompactPoseIndex(Bones)).GetLocation();};
        const FVector Pivot=Position(Arm),Origin=Position(Muzzle);
        const FVector Bore=(Position(Front)-Position(Rear)).GetSafeNormal();
        if(Bore.IsNearlyZero())return;
        FQuat Turn=FQuat::Identity;
        // The shoulder pivot moves the muzzle while turning. Recompute the ray
        // from that moved muzzle; no hand-only look-at or bone stretching.
        for(int32 I=0;I<4;++I)
        {
            const FVector MovedMuzzle=Pivot+Turn.RotateVector(Origin-Pivot);
            const FVector Desired=(Target-MovedMuzzle).GetSafeNormal();
            if(Desired.IsNearlyZero())return;
            Turn=(FQuat::FindBetweenNormals(Turn.RotateVector(Bore),Desired)*Turn).GetNormalized();
        }
        const float Angle=Turn.GetAngle();
        const float Limit=FMath::DegreesToRadians(6.f);
        const float Blend=FMath::Clamp(Weight,0.f,1.f)*FMath::Min(1.f,Limit/FMath::Max(Angle,SMALL_NUMBER));
        Turn=FQuat::Slerp(FQuat::Identity,Turn,Blend).GetNormalized();
        const FVector AnimatedShoulder=ComponentPose(Output.Pose,Arm.GetCompactPoseIndex(Bones)).GetLocation();
        const FTransform Delta(Turn,AnimatedShoulder-Turn.RotateVector(AnimatedShoulder));
        const FCompactPoseBoneIndex Root(0);
        Output.Pose[Root]=Output.Pose[Root]*Delta;
        Output.Pose[Root].NormalizeRotation();
    }
};
