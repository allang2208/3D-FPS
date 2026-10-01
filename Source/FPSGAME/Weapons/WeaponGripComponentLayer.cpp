#include "WeaponGripComponentLayer.h"
#include "WeaponGripProfile.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void FWeaponGripComponentLayer::Apply(const UWeaponGripProfile* Profile,const UAnimSequence* Clip,float Time,USkeletalMeshComponent& Mesh)
{
    const auto* Asset=Mesh.GetSkeletalMeshAsset();
    if(Profile!=CachedProfile||Clip!=CachedClip||Asset!=CachedMesh)
    {
        CachedProfile=Profile;CachedClip=Clip;CachedMesh=Asset;
        Layer=Profile?Profile->Find(Clip):nullptr;TrackBones.Reset();
        if(Layer&&Asset&&Clip->GetSkeleton()==Asset->GetSkeleton())
            for(const FWeaponGripTrack& Track:Layer->Tracks)TrackBones.Add(Asset->GetRefSkeleton().FindBoneIndex(Track.Bone));
        else Layer=nullptr;
    }
    if(!Layer||TrackBones.IsEmpty())return;
    const auto& Ref=Asset->GetRefSkeleton();
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    Local.SetNum(Pose.Num());
    for(int32 I=0;I<Pose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        Local[I]=Parent==INDEX_NONE?Pose[I]:Pose[I].GetRelativeTransform(Pose[Parent]);
    }
    for(int32 I=0;I<TrackBones.Num();++I)
    {
        if(!Local.IsValidIndex(TrackBones[I]))continue;
        const FTransform Delta=Layer->Tracks[I].Sample(FMath::Clamp(Time,0.f,Layer->Duration));
        auto& Bone=Local[TrackBones[I]];
        Bone.SetTranslation(Bone.GetTranslation()+Delta.GetTranslation());
        Bone.SetRotation((Delta.GetRotation()*Bone.GetRotation()).GetNormalized());
        Bone.SetScale3D(Bone.GetScale3D()+Delta.GetScale3D());
    }
    for(int32 I=0;I<Pose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        Pose[I]=Parent==INDEX_NONE?Local[I]:Local[I]*Pose[Parent];
    }
}
