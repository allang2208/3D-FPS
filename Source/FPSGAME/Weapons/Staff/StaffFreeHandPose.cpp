#include "StaffFreeHandPose.h"
#include "StaffAuthoredLeftGaitV16.h"
#include "Engine/SkeletalMesh.h"
#include "ReferenceSkeleton.h"

namespace StaffFreeHandPose
{
using namespace StaffLeftGaitV16;
struct FArmBone
{
    int32 Index=INDEX_NONE;
    FTransform Local[2][Samples];
};

void Apply(USkeletalMesh* Mesh,const TArray<FTransform>& Reference,
    TArray<FTransform>& LocalPose,float StridePhase,float MoveWeight,float RunWeight,float MotionTime)
{
    if(MoveWeight<=UE_SMALL_NUMBER)return;
    static TWeakObjectPtr<USkeletalMesh> CachedMesh;
    static TArray<FArmBone> Bones;
    static int32 CachedRevision=0;
    // Live Coding retains existing function statics. Refresh the pose table
    // after a source revision even when the same arms asset is still loaded.
    if(CachedRevision!=16||CachedMesh.Get()!=Mesh)
    {
        CachedMesh=Mesh;Bones.Reset(BoneCount);
        const auto& Skeleton=Mesh->GetRefSkeleton();
        for(int32 B=0;B<BoneCount;++B)
        {
            const int32 I=Skeleton.FindBoneIndex(Names[B]);if(I==INDEX_NONE)continue;
            const int32 Parent=Skeleton.GetParentIndex(I);
            const FVector Scale=Parent>=0?Reference[Parent].GetScale3D():FVector::OneVector;
            auto& Bone=Bones.AddDefaulted_GetRef();Bone.Index=I;
            for(int32 Cycle=0;Cycle<2;++Cycle)for(int32 Frame=0;Frame<Samples;++Frame)
            {
                const auto& Key=Cycles[Cycle][Frame][B];
                Bone.Local[Cycle][Frame]=Skeleton.GetRefBonePose()[I];
                Bone.Local[Cycle][Frame].SetLocation(Key.Position/Scale);
                Bone.Local[Cycle][Frame].SetRotation(Key.Rotation.GetNormalized());
            }
        }
        CachedRevision=16;
    }
    const float Sample=FMath::Fmod(StridePhase/(2.f*PI)*Samples+Samples,static_cast<float>(Samples));
    const int32 A=FMath::FloorToInt(Sample),B=(A+1)%Samples;
    const float Alpha=Sample-A;
    // Slow, bounded amplitude variation removes identical repeated silhouettes.
    // It does not retime the gait or inject random per-frame finger jitter.
    const float Variation=.972f+.018f*FMath::Sin(MotionTime*.71f)+.010f*FMath::Sin(MotionTime*1.13f+.8f);
    const float Weight=MoveWeight*Variation;
    for(const auto& Bone:Bones)
    {
        FTransform Walk,Run,Gait,Mixed;
        Walk.Blend(Bone.Local[0][A],Bone.Local[0][B],Alpha);
        Run.Blend(Bone.Local[1][A],Bone.Local[1][B],Alpha);
        Gait.Blend(Walk,Run,RunWeight);
        Mixed.Blend(LocalPose[Bone.Index],Gait,Weight);
        LocalPose[Bone.Index]=Mixed;
    }
}
}
