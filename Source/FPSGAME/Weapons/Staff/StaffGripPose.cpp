#include "StaffGripPose.h"
#include "StaffAuthoredReleaseAnatomy20261001.h"
#include "StaffAuthoredPrimaryV28.h"
#include "StaffAuthoredChargeFlow20261001.h"
#include "ReferenceSkeleton.h"
#include "Engine/SkeletalMesh.h"

namespace StaffGripPose
{
// Carry/grasp and primary attack are retained. All casting keys share the
// anatomical shoulder/elbow chain used by the settled charge pose.
namespace Authored = StaffAuthoredReleaseAnatomy20261001;
int32 VariantForMesh(const FString& MeshPath)
{
    for(int32 I=1;I<Authored::VariantCount;++I)
        if(MeshPath.Contains(Authored::VariantNames[I]))return I;
    return 0;
}
static void Build(const FReferenceSkeleton& S,const TArray<FTransform>& Ref,int32 Variant,FGripData& Data,bool bCharge)
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
    if(bCharge)
    {
        namespace Charge=StaffAuthoredChargeFlow20261001;
        Data.HandInGrip=Charge::HandInGrip[Variant];
        for(int32 Clip=0;Clip<Charge::KeyCount;++Clip)
        {
            auto& Local=Data.Local[Authored::PoseCount+Clip];Local=S.GetRefBonePose();
            for(int32 Bone=0;Bone<Charge::BoneCount;++Bone)
            {
                const int32 I=S.FindBoneIndex(Charge::Names[Bone]);if(I<0)continue;
                const int32 Parent=S.GetParentIndex(I);
                const FVector ParentScale=Parent>=0?Ref[Parent].GetScale3D():FVector::OneVector;
                const auto& Key=Charge::Poses[Variant][Clip][Bone];
                Local[I].SetLocation(Key.Position/ParentScale);
                Local[I].SetRotation(Key.Rotation.GetNormalized());
            }
        }
    }
}
const FGripData& Get(USkeletalMesh* Mesh,const TArray<FTransform>& Reference,int32 Variant,bool bCharge)
{
    static TWeakObjectPtr<USkeletalMesh> FamilyMesh;
    static FGripData Families[2][Authored::VariantCount];
    static int32 FamilyRevision=0;
    static int32 ReleaseRevision=0;
    if(FamilyRevision!=StaffAuthoredChargeFlow20261001::Revision||ReleaseRevision!=Authored::Revision||FamilyMesh.Get()!=Mesh)
    {
        FamilyMesh=Mesh;
        for(int32 Bank=0;Bank<2;++Bank)
            for(int32 I=0;I<Authored::VariantCount;++I)Build(Mesh->GetRefSkeleton(),Reference,I,Families[Bank][I],Bank==1);
        FamilyRevision=StaffAuthoredChargeFlow20261001::Revision;ReleaseRevision=Authored::Revision;
    }
    return Families[bCharge?1:0][FMath::Clamp(Variant,0,Authored::VariantCount-1)];
}
FTransform BlendLocal(const FGripData& Data,const FStaffCastPose& Motion,int32 Bone,bool bCharge)
{
    bool bPrimaryKeys=false;
    if(Bone==Data.Lower&&!bCharge)for(int32 I=6;I<FStaffCastPose::ArmPoseCount;++I)bPrimaryKeys|=Motion.ArmWeights[I]>0.f;
    if(Bone==Data.Lower&&!bPrimaryKeys)
    {
        namespace Charge=StaffAuthoredChargeFlow20261001;
        int32 Variant=0;
        for(int32 I=0;I<Charge::VariantCount;++I)
            if(Data.HandInGrip.Equals(Charge::HandInGrip[I])){Variant=I;break;}
        FTransform Entry=FTransform::Identity;float EntryWeight=0.f;
        for(const int32 Clip:{0,5})
        {
            const float W=Motion.ArmWeights[Clip];if(W<=0.f)continue;
            if(EntryWeight==0.f)Entry=Data.Local[Clip][Bone];
            else {FTransform Mixed;Mixed.Blend(Entry,Data.Local[Clip][Bone],W/(EntryWeight+W));Entry=Mixed;}
            EntryWeight+=W;
        }
        double Flexion=0.,Roll=0.;float KeyWeight=0.f;
        for(int32 Clip=1;Clip<=4;++Clip)
        {
            const float W=Motion.ArmWeights[Clip];
            Flexion+=W*Authored::ElbowAngles[Variant][Clip][0];
            Roll+=W*Authored::ElbowAngles[Variant][Clip][1];KeyWeight+=W;
        }
        if(bCharge)for(int32 Key=0;Key<Charge::KeyCount;++Key)
        {
            const float W=Motion.ArmWeights[6+Key];
            Flexion+=W*Charge::ElbowAngles[Variant][Key][0];
            Roll+=W*Charge::ElbowAngles[Variant][Key][1];KeyWeight+=W;
        }
        if(KeyWeight<=0.f)return Entry;
        FTransform Charged=Data.Local[1][Bone];
        // Flex around the native elbow hinge, then pronate around the forearm.
        // Arbitrary local quaternion folding couples those two joint motions.
        Charged.SetRotation((FQuat(Data.ElbowHinge,Flexion/KeyWeight)*Authored::LowerRestRotation*
            FQuat(Authored::ForearmAxisLocal,Roll/KeyWeight)).GetNormalized());
        if(EntryWeight<=0.f)return Charged;
        FTransform Mixed;Mixed.Blend(Entry,Charged,KeyWeight/(EntryWeight+KeyWeight));return Mixed;
    }
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
            if(Clip>=6&&!bCharge)
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
FTransform ContactFromArm(const FGripData& Data,const FStaffCastPose& Motion,bool bCharge)
{
    if(Data.HandParents.IsEmpty())return Motion.Contact;
    FTransform Hand=FTransform::Identity;
    for(const int32 Bone:Data.HandParents)Hand=BlendLocal(Data,Motion,Bone,bCharge)*Hand;
    Hand.SetScale3D(FVector::OneVector);
    return Data.HandInGrip.Inverse()*Hand;
}
}
