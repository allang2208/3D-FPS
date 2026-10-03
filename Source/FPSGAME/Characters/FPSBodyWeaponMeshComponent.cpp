#include "FPSBodyWeaponMeshComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
void UFPSBodyWeaponMeshComponent::PublishMechanicalPose(const TArray<FTransform>& Pose)
{
    if(Pose.Num()!=GetEditableComponentSpaceTransforms().Num())return;
    GetEditableComponentSpaceTransforms()=Pose;
    bNeedToFlipSpaceBaseBuffers=true;
    Super::FinalizeBoneTransform();
    UpdateChildTransforms();MarkRenderDynamicDataDirty();
}
void UFPSBodyWeaponMeshComponent::CaptureHoldTransition(float Seconds)
{
    const auto* Mesh=GetSkeletalMeshAsset();if(!Mesh)return;
    const auto& Ref=Mesh->GetRefSkeleton();const auto& Pose=GetComponentSpaceTransforms();
    TransitionLocal.SetNum(Pose.Num());
    for(int32 I=0;I<Pose.Num();++I)
    {const int32 P=Ref.GetParentIndex(I);TransitionLocal[I]=P>=0?Pose[I].GetRelativeTransform(Pose[P]):Pose[I];}
    TransitionAge=0.f;TransitionSeconds=Seconds;
}
void UFPSBodyWeaponMeshComponent::AdvanceHoldTransition(float Delta)
{TransitionAge=FMath::Min(TransitionSeconds,TransitionAge+FMath::Max(0.f,Delta));}
void UFPSBodyWeaponMeshComponent::FinalizeBoneTransform()
{
    if(auto* Single=GetSingleNodeInstance())
        GripLayer.Apply(GripProfile,Cast<UAnimSequence>(Single->GetCurrentAsset()),GetPosition(),*this);
    if(IsHoldTransitionActive()&&GetSkeletalMeshAsset())
    {
        auto& Pose=GetEditableComponentSpaceTransforms();
        if(TransitionLocal.Num()==Pose.Num())
        {
            const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();const auto Incoming=Pose;
            const float Weight=FMath::SmoothStep(0.f,1.f,TransitionAge/FMath::Max(.001f,TransitionSeconds));
            for(int32 I=0;I<Pose.Num();++I)
            {
                const int32 Parent=Ref.GetParentIndex(I);
                const FTransform Target=Parent>=0?Incoming[I].GetRelativeTransform(Incoming[Parent]):Incoming[I];
                FTransform Local;Local.Blend(TransitionLocal[I],Target,Weight);
                Pose[I]=Parent>=0?Local*Pose[Parent]:Local;
            }
        }
    }
    Super::FinalizeBoneTransform();
}
