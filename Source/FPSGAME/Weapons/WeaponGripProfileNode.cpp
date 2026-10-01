#include "WeaponGripProfileNode.h"
#include "WeaponGripProfile.h"
#include "Animation/AnimSequence.h"

void FWeaponGripProfileNode::CacheBones_AnyThread(const FAnimationCacheBonesContext& Context)
{
    Source.CacheBones(Context);CachedProfile=nullptr;CachedClip=nullptr;Layer=nullptr;Bones.Reset();
}

void FWeaponGripProfileNode::Evaluate_AnyThread(FPoseContext& Output)
{
    Source.Evaluate(Output);
    const FBoneContainer& Required=Output.Pose.GetBoneContainer();
    if(Profile!=CachedProfile||Clip!=CachedClip)
    {
        CachedProfile=Profile;CachedClip=Clip;Layer=Profile?Profile->Find(Clip):nullptr;Bones.Reset();
        if(Layer&&Clip->GetSkeleton()==Required.GetSkeletonAsset())
            for(const FWeaponGripTrack& Track:Layer->Tracks)
            {
                FBoneReference& Bone=Bones.AddDefaulted_GetRef();Bone.BoneName=Track.Bone;Bone.Initialize(Required);
            }
        else Layer=nullptr;
    }
    if(!Layer)return;
    for(int32 I=0;I<Bones.Num();++I)
    {
        if(!Bones[I].IsValidToEvaluate(Required))continue;
        const FTransform Delta=Layer->Tracks[I].Sample(FMath::Clamp(Time,0.f,Layer->Duration));
        FTransform& Local=Output.Pose[Bones[I].GetCompactPoseIndex(Required)];
        Local.SetTranslation(Local.GetTranslation()+Delta.GetTranslation());
        Local.SetRotation((Delta.GetRotation()*Local.GetRotation()).GetNormalized());
        Local.SetScale3D(Local.GetScale3D()+Delta.GetScale3D());
    }
}
