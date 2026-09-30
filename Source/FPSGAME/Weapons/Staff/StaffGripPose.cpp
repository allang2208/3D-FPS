#include "StaffGripPose.h"
#include "StaffAuthoredCastElbow20260930.h"
#include "StaffAuthoredPrimaryV28.h"
#include "ReferenceSkeleton.h"
#include "Engine/SkeletalMesh.h"

namespace StaffGripPose
{
// Retain the accepted V13 grasp/carry and V28 primary attack. Only the cast
// keys redistribute excess elbow roll; no outfit-dependent pose correction.
namespace Authored = StaffAuthoredCastElbow20260930;
int32 VariantForMesh(const FString& MeshPath)
{
    for(int32 I=1;I<Authored::VariantCount;++I)
        if(MeshPath.Contains(Authored::VariantNames[I]))return I;
    return 0;
}
static void Build(const FReferenceSkeleton& S,const TArray<FTransform>& Ref,int32 Variant,FGripData& Data)
{
    Data=FGripData();Data.HandInGrip=Authored::HandInGrip[Variant];
    Data.Hand=S.FindBoneIndex(TEXT("hand_r"));Data.Lower=S.FindBoneIndex(TEXT("lowerarm_r"));
    const int32 Upper=S.FindBoneIndex(TEXT("upperarm_r"));
    const int32 Right=S.FindBoneIndex(TEXT("clavicle_r")),Left=S.FindBoneIndex(TEXT("clavicle_l"));
    Data.Shoulder=Right;Data.Upper=Upper;
    for(int32 I=Data.Hand;I!=INDEX_NONE;I=S.GetParentIndex(I))Data.HandParents.Insert(I,0);
    if(Upper>=0&&Data.Lower>=0&&Data.Hand>=0)
    {
        const FVector A=Ref[Data.Lower].GetLocation()-Ref[Upper].GetLocation();
        const FVector B=Ref[Data.Hand].GetLocation()-Ref[Data.Lower].GetLocation();
        Data.ElbowHinge=Ref[Upper].GetRotation().UnrotateVector((A^B).GetSafeNormal());
    }
    for(int32 I=0;I<Ref.Num();++I)
    {
        if(Right>=0&&(I==Right||S.BoneIsChildOf(I,Right)))Data.RightChain.Add(I);
        if(Left>=0&&(I==Left||S.BoneIsChildOf(I,Left)))Data.LeftChain.Add(I);
    }
    for(int32 Clip=0;Clip<Authored::PoseCount;++Clip)
    {
        auto& Local=Data.Local[Clip];Local=S.GetRefBonePose();
        for(const auto& Bone:Authored::Poses[Variant][Clip])
        {
            const int32 I=S.FindBoneIndex(Bone.Name);if(I<0)continue;
            const int32 Parent=S.GetParentIndex(I);
            // Authoring uses normalized cm transforms; the existing M4 asset
            // retains its original parent scale. Convert translations once.
            const FVector ParentScale=Parent>=0?Ref[Parent].GetScale3D():FVector::OneVector;
            Local[I].SetLocation(Bone.Position/ParentScale);
            Local[I].SetRotation(Bone.Rotation.GetNormalized());
        }
    }
    for(int32 Clip=0;Clip<StaffAuthoredPrimaryV28::PoseCount;++Clip)
    {
        auto& Local=Data.Local[Authored::PoseCount+Clip];Local=S.GetRefBonePose();
        for(const auto& Bone:StaffAuthoredPrimaryV28::Poses[Variant][Clip])
        {
            const int32 I=S.FindBoneIndex(Bone.Name);if(I<0)continue;
            const int32 Parent=S.GetParentIndex(I);
            const FVector ParentScale=Parent>=0?Ref[Parent].GetScale3D():FVector::OneVector;
            Local[I].SetLocation(Bone.Position/ParentScale);
            Local[I].SetRotation(Bone.Rotation.GetNormalized());
        }
    }
}
const FGripData& Get(USkeletalMesh* Mesh,const TArray<FTransform>& Reference,int32 Variant)
{
    static TWeakObjectPtr<USkeletalMesh> CachedMesh;
    static FGripData Data[Authored::VariantCount];
    static int32 Revision=0;
    if(Revision!=20260930||CachedMesh.Get()!=Mesh)
    {
        CachedMesh=Mesh;
        for(int32 I=0;I<Authored::VariantCount;++I)Build(Mesh->GetRefSkeleton(),Reference,I,Data[I]);
        Revision=20260930;
    }
    return Data[FMath::Clamp(Variant,0,Authored::VariantCount-1)];
}
FTransform BlendLocal(const FGripData& Data,const FStaffCastPose& Motion,int32 Bone)
{
    FTransform Result=FTransform::Identity;float Accumulated=0.f;
    float CarryWeight=0.f;for(int32 I=0;I<6;++I)CarryWeight+=Motion.ArmWeights[I];
    for(int32 Clip=0;Clip<FStaffCastPose::ArmPoseCount;++Clip)
    {
        const float Weight=Motion.ArmWeights[Clip];if(Weight<=0.f)continue;
        if(Accumulated==0.f)Result=Data.Local[Clip][Bone];
        else
        {
            float U=Weight/(Accumulated+Weight);
            // Lead with shoulder, let elbow extension trail slightly. Use this
            // identical local blend for both visible bones and the shaft grip.
            if(Clip>=6)
            {
                const float Lead=Bone==Data.Shoulder?.16f:Bone==Data.Upper?.12f:Bone==Data.Lower?-.06f:0.f;
                U+=Lead*(1.f-CarryWeight)*FMath::Sin(PI*U);
            }
            FTransform Mixed;Mixed.Blend(Result,Data.Local[Clip][Bone],U);Result=Mixed;
        }
        Accumulated+=Weight;
    }
    return Result;
}
FTransform ContactFromArm(const FGripData& Data,const FStaffCastPose& Motion)
{
    if(Data.HandParents.IsEmpty())return Motion.Contact;
    FTransform Hand=FTransform::Identity;
    for(const int32 Bone:Data.HandParents)Hand=BlendLocal(Data,Motion,Bone)*Hand;
    Hand.SetScale3D(FVector::OneVector);
    return Data.HandInGrip.Inverse()*Hand;
}
}
