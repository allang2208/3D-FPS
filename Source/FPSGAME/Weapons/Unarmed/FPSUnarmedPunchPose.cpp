#include "FPSUnarmedIdleComponent.h"
#include "UnarmedAuthoredPunch20261002.h"
#include "../Staff/StaffQuickCombatMotion.h"
#include "Camera/CameraComponent.h"
#include "Engine/SkeletalMesh.h"

void UFPSUnarmedArmsMeshComponent::CachePunchPose()
{
    namespace Motion=UnarmedAuthoredPunch20261002;
    auto* Mesh=GetSkeletalMeshAsset();
    if(!Mesh||(PunchMesh.Get()==Mesh&&PunchRevision==Motion::Revision))return;
    PunchMesh=Mesh;PunchRevision=Motion::Revision;PunchEntry.Reset();
    const auto& Skeleton=Mesh->GetRefSkeleton();
    for(int32 Side=0;Side<2;++Side)
    {
        PunchBones[Side].Reset();
        const int32 Root=Skeleton.FindBoneIndex(Side==0?TEXT("clavicle_l"):TEXT("clavicle_r"));
        for(int32 I=0;I<Reference.Num();++I)
            if(Root>=0&&(I==Root||Skeleton.BoneIsChildOf(I,Root)))PunchBones[Side].Add(I);
        for(int32 Key=0;Key<Motion::KeyCount;++Key)
        {
            PunchKeys[Side][Key]=Skeleton.GetRefBonePose();
            for(int32 B=0;B<Motion::BoneCount;++B)
            {
                const int32 I=Skeleton.FindBoneIndex(Motion::Names[B]);if(I<0)continue;
                const int32 Parent=Skeleton.GetParentIndex(I);
                const FVector Scale=Parent>=0?Reference[Parent].GetScale3D():FVector::OneVector;
                const auto& Bone=Motion::Poses[Side][Key][B];
                PunchKeys[Side][Key][I].SetLocation(Bone.Position/Scale);
                PunchKeys[Side][Key][I].SetRotation(Bone.Rotation.GetNormalized());
            }
        }
    }
}

void UFPSUnarmedArmsMeshComponent::CapturePunchEntry()
{
    CacheIdlePose();CachePunchPose();
    const auto* Camera=Cast<UCameraComponent>(GetAttachParent());
    const auto* Mesh=GetSkeletalMeshAsset();
    const auto& Source=GetComponentSpaceTransforms();
    if(!Camera||!Mesh||Source.Num()!=Reference.Num())return;
    const auto& Skeleton=Mesh->GetRefSkeleton();
    auto InCamera=Reference;
    for(const int32 I:ArmBones)
        InCamera[I]=(Source[I]*GetComponentTransform()).GetRelativeTransform(Camera->GetComponentTransform());
    PunchEntry=Skeleton.GetRefBonePose();
    const int32 LeftRoot=Skeleton.FindBoneIndex(TEXT("clavicle_l")),RightRoot=Skeleton.FindBoneIndex(TEXT("clavicle_r"));
    for(const int32 I:ArmBones)
    {
        const int32 Parent=Skeleton.GetParentIndex(I);
        const FTransform Local=Parent>=0?InCamera[I].GetRelativeTransform(InCamera[Parent]):InCamera[I];
        PunchEntry[I].SetRotation(Local.GetRotation().GetNormalized());
        // Keep segment lengths native; only the shoulder girdle can translate.
        if(I==LeftRoot||I==RightRoot)PunchEntry[I].SetLocation(Local.GetLocation());
    }
    for(int32 Side=0;Side<2;++Side)EntryJoints[Side]=CurrentJoints[Side];
}

void UFPSUnarmedArmsMeshComponent::ApplyPunchPose(TArray<FTransform>& LocalPose)
{
    if(PunchAge<0.f)return;
    namespace Motion=UnarmedAuthoredPunch20261002;
    CachePunchPose();
    if(LocalPose.Num()!=Reference.Num()||PunchBones[PunchSide].IsEmpty())return;
    if(PunchEntry.Num()!=LocalPose.Num())
    {
        PunchEntry=LocalPose;
        for(int32 Side=0;Side<2;++Side)EntryJoints[Side]=CurrentJoints[Side];
    }
    int32 A=0;
    while(A<Motion::KeyCount-2&&PunchAge>=Motion::Times[A+1])++A;
    const float T=FMath::Clamp((PunchAge-Motion::Times[A])/(Motion::Times[A+1]-Motion::Times[A]),0.f,1.f);
    const float Weight=T*T*T*(T*(T*6.f-15.f)+10.f);
    const float Return=FMath::SmoothStep(StaffQuickCombatMotion::Recover,Motion::Times[Motion::KeyCount-1],PunchAge);
    for(const int32 I:PunchBones[PunchSide])
    {
        FTransform Target;
        Target.Blend(A==0?PunchEntry[I]:PunchKeys[PunchSide][A][I],PunchKeys[PunchSide][A+1][I],Weight);
        Target.BlendWith(LocalPose[I],Return);LocalPose[I]=Target;
    }
    const int32 Lower=LowerBones[PunchSide];
    if(Lower>=0)
    {
        const auto& Definition=Motion::JointDefinitions[PunchSide];
        const auto& JA=Motion::Joints[PunchSide][A][PunchSide];
        const auto& JB=Motion::Joints[PunchSide][A+1][PunchSide];
        const FVector2D Start=A==0?EntryJoints[PunchSide]:FVector2D(JA.Flex,JA.Roll);
        const FVector2D Strike=FMath::Lerp(Start,FVector2D(JB.Flex,JB.Roll),Weight);
        const FVector2D Joint=FMath::Lerp(Strike,CurrentJoints[PunchSide],Return);
        LocalPose[Lower].SetRotation((FQuat(Definition.ElbowHinge,Joint.X)*Definition.LowerRestRotation*
            FQuat(Definition.ForearmAxis,Joint.Y)).GetNormalized());
    }
}
