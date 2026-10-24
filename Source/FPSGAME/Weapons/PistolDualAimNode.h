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
    FBoneReference Shoulder[2], Front, Rear, Muzzle, GunRoot, OpticBone;
    FVector Target=FVector::ZeroVector;
    float Weight=0.f;
    int32 Side=0;
    bool bEnabled=false;
    float ADSWeight=0.f,EyeDistance=30.f;
    FTransform OpticMount=FTransform::Identity;
    FVector SightRear=FVector::ZeroVector,SightFront=FVector::ForwardVector,SightUp=FVector::UpVector;

    FPistolDualAimNode()
    {
        Shoulder[0].BoneName=TEXT("upperarm_r");Shoulder[1].BoneName=TEXT("upperarm_l");
        Front.BoneName=TEXT("WPN_FrontSight");Rear.BoneName=TEXT("WPN_RearSight");Muzzle.BoneName=TEXT("WPN_SOCKET_Muzzle");
        GunRoot.BoneName=TEXT("WPN_root");
    }
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override
    { Source.Initialize(Context);Reference.Initialize(Context); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
    {
        Source.CacheBones(Context);Reference.CacheBones(Context);
        const auto& Bones=Context.AnimInstanceProxy->GetRequiredBones();
        for(auto* Bone:{&Shoulder[0],&Shoulder[1],&Front,&Rear,&Muzzle,&GunRoot,&OpticBone})
            if(Bones.GetReferenceSkeleton().FindBoneIndex(Bone->BoneName)!=INDEX_NONE)Bone->Initialize(Bones);
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override
    {
        Source.Update(Context);
        if(bEnabled && (Weight>SMALL_NUMBER || ADSWeight>SMALL_NUMBER))Reference.Update(Context);
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
        if(!bEnabled || (Weight<=SMALL_NUMBER && ADSWeight<=SMALL_NUMBER))return;
        const auto& Bones=Output.Pose.GetBoneContainer();
        const auto& Arm=Shoulder[Side];
        if(!Arm.IsValidToEvaluate(Bones) || !Front.IsValidToEvaluate(Bones) || !Rear.IsValidToEvaluate(Bones) || !Muzzle.IsValidToEvaluate(Bones))return;
        FPoseContext Neutral(Output);Reference.Evaluate(Neutral);
        if(ADSWeight>SMALL_NUMBER)
        {
            FVector R,F,U;
            if(!OpticBone.BoneName.IsNone())
            {
                if(!OpticBone.IsValidToEvaluate(Bones))return;
                const FTransform Mount=OpticMount*ComponentPose(Neutral.Pose,OpticBone.GetCompactPoseIndex(Bones));
                R=Mount.TransformPosition(SightRear);F=Mount.TransformPosition(SightFront);
                U=Mount.TransformVector(SightUp).GetSafeNormal();
            }
            else
            {
                if(!GunRoot.IsValidToEvaluate(Bones))return;
                R=ComponentPose(Neutral.Pose,Rear.GetCompactPoseIndex(Bones)).GetLocation();
                F=ComponentPose(Neutral.Pose,Front.GetCompactPoseIndex(Bones)).GetLocation();
                U=ComponentPose(Neutral.Pose,GunRoot.GetCompactPoseIndex(Bones)).GetRotation().GetAxisZ();
            }
            const FVector Axis=(F-R).GetSafeNormal();
            if(Axis.IsNearlyZero() || FVector::CrossProduct(Axis,U).IsNearlyZero())return;
            // The component retains the authored hip basis (-90 yaw). Solve
            // here in that basis; external recoil/jump/crouch remain additive.
            const FQuat CameraToMesh=FRotator(0.f,90.f,0.f).Quaternion();
            const FQuat Align=(CameraToMesh*FRotationMatrix::MakeFromXZ(Axis,U).ToQuat().Inverse()).GetNormalized();
            const float Alpha=FMath::Clamp(ADSWeight,0.f,1.f);
            const FQuat Blended=FQuat::Slerp(FQuat::Identity,Align,Alpha);
            const FVector Eye=CameraToMesh.RotateVector(FVector(EyeDistance,0.f,0.f));
            const FTransform Alignment(Blended,FMath::Lerp(R,Eye,Alpha)-Blended.RotateVector(R));
            const FCompactPoseBoneIndex Root(0);
            Output.Pose[Root]=Output.Pose[Root]*Alignment;
            Output.Pose[Root].NormalizeRotation();
            Neutral.Pose[Root]=Neutral.Pose[Root]*Alignment;
            Neutral.Pose[Root].NormalizeRotation();
        }
        if(Weight<=SMALL_NUMBER)return;
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
