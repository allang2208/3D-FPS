#include "StaffQuickCombatPose.h"
#include "StaffAuthoredQuickPunch20261001.h"
#include "StaffQuickCombatMotion.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace StaffQuickCombatPose
{
namespace
{
    // The local player owns one active staff rig, as with StaffGripPose's cache.
    struct FQuickPoseCache
    {
        TWeakObjectPtr<USkeletalMesh> Mesh;
        TWeakObjectPtr<USkeletalMeshComponent> Owner;
        TArray<int32> Bones;
        TArray<FTransform> Keys[StaffAuthoredQuickPunch20261001::KeyCount];
        TArray<FTransform> Reference,Entry;
        uint32 Serial=0;
    };
    FQuickPoseCache& Cache(USkeletalMeshComponent& Arms)
    {
        static FQuickPoseCache Data;
        static int32 CachedRevision=0;
        auto* Mesh=Arms.GetSkeletalMeshAsset();
        if(CachedRevision!=StaffAuthoredQuickPunch20261001::Revision||Data.Mesh.Get()!=Mesh)
        {
            Data=FQuickPoseCache();Data.Mesh=Mesh;
            CachedRevision=StaffAuthoredQuickPunch20261001::Revision;
            if(!Mesh)return Data;
            const auto& Skeleton=Mesh->GetRefSkeleton();
            Data.Reference=Skeleton.GetRefBonePose();
            for(int32 I=0;I<Data.Reference.Num();++I)
            {
                const int32 Parent=Skeleton.GetParentIndex(I);
                if(Parent>=0)Data.Reference[I]=Data.Reference[I]*Data.Reference[Parent];
            }
            for(int32 B=0;B<StaffAuthoredQuickPunch20261001::BoneCount;++B)
            {
                const int32 I=Skeleton.FindBoneIndex(StaffAuthoredQuickPunch20261001::Names[B]);
                Data.Bones.Add(I);
            }
            for(int32 K=0;K<StaffAuthoredQuickPunch20261001::KeyCount;++K)
            {
                Data.Keys[K]=Skeleton.GetRefBonePose();
                for(int32 B=0;B<Data.Bones.Num();++B)
                {
                    const int32 I=Data.Bones[B];if(I==INDEX_NONE)continue;
                    const int32 Parent=Skeleton.GetParentIndex(I);
                    const auto& Key=StaffAuthoredQuickPunch20261001::Poses[K][B];
                    Data.Keys[K][I].SetLocation(Key.Position/(Parent>=0?Data.Reference[Parent].GetScale3D():FVector::OneVector));
                    Data.Keys[K][I].SetRotation(Key.Rotation.GetNormalized());
                }
            }
        }
        return Data;
    }
}

void CaptureEntry(USkeletalMeshComponent& Arms,uint32 Serial)
{
    auto& Data=Cache(Arms);
    auto* Camera=Arms.GetOwner()?Arms.GetOwner()->FindComponentByClass<UCameraComponent>():nullptr;
    const auto* Mesh=Arms.GetSkeletalMeshAsset();
    const auto& Pose=Arms.GetComponentSpaceTransforms();
    if(!Camera||!Mesh||Pose.Num()!=Data.Reference.Num())return;
    const auto& Skeleton=Mesh->GetRefSkeleton();
    const int32 Root=Skeleton.FindBoneIndex(TEXT("clavicle_l"));
    auto InCamera=Data.Reference;
    for(const int32 I:Data.Bones)if(I!=INDEX_NONE)
        InCamera[I]=(Pose[I]*Arms.GetComponentTransform()).GetRelativeTransform(Camera->GetComponentTransform());
    Data.Entry=Skeleton.GetRefBonePose();
    for(const int32 I:Data.Bones)if(I!=INDEX_NONE)
    {
        const int32 Parent=Skeleton.GetParentIndex(I);
        const auto Local=Parent>=0?InCamera[I].GetRelativeTransform(InCamera[Parent]):InCamera[I];
        Data.Entry[I].SetRotation(Local.GetRotation().GetNormalized());
        // All segments keep native translations. Only the girdle moves in camera space.
        if(I==Root)Data.Entry[I].SetLocation(Local.GetLocation());
    }
    Data.Owner=&Arms;Data.Serial=Serial;
}

void Apply(USkeletalMeshComponent& Arms,const TArray<FTransform>& Reference,
    TArray<FTransform>& LocalPose,float Age,uint32 Serial)
{
    using namespace StaffAuthoredQuickPunch20261001;
    auto& Data=Cache(Arms);
    if(LocalPose.Num()!=Reference.Num()||Data.Bones.IsEmpty())return;
    if(Data.Owner.Get()!=&Arms||Data.Serial!=Serial||Data.Entry.Num()!=LocalPose.Num())
    {Data.Owner=&Arms;Data.Serial=Serial;Data.Entry=LocalPose;}
    int32 A=0;
    while(A<KeyCount-2&&Age>=Times[A+1])++A;
    const float T=FMath::Clamp((Age-Times[A])/FMath::Max(.001f,Times[A+1]-Times[A]),0.f,1.f);
    const float Weight=T*T*T*(T*(T*6.f-15.f)+10.f);
    const float Return=FMath::SmoothStep(StaffQuickCombatMotion::Recover,Times[KeyCount-1],Age);
    for(const int32 I:Data.Bones)if(I!=INDEX_NONE)
    {
        FTransform Target,Mixed;
        Target.Blend(A==0?Data.Entry[I]:Data.Keys[A][I],Data.Keys[A+1][I],Weight);
        // Return to the actual current carry/gait rather than a frozen final key.
        Mixed.Blend(Target,LocalPose[I],Return);
        LocalPose[I]=Mixed;
    }
}
}
