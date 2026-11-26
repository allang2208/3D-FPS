#include "FPSBodyWeaponMeshComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
void UFPSBodyWeaponMeshComponent::PublishMechanicalPose(const TArray<FTransform>& Pose)
{
    if(Pose.Num()!=GetEditableComponentSpaceTransforms().Num())return;
    const auto* Asset=GetSkeletalMeshAsset();
    const bool Eligible=Asset&&!Asset->IsCompiling()&&!IsComponentTickEnabled()&&!IsRunningParallelEvaluation()
        &&!LeaderPoseComponent.IsValid()&&GetCollisionEnabled()==ECollisionEnabled::NoCollision
        &&!IsSimulatingPhysics()&&GetClothingSimulationInstances().IsEmpty()
        &&GetMeshDeformerInstances().DeformerInstances.IsEmpty()&&Asset->GetMorphTargets().IsEmpty()
        &&!GetExternalMorphSetsArray().ContainsByPredicate([](const auto& Sets){return !Sets.IsEmpty();})
        &&!IsRenderStateDirty()&&GetMeshObject()!=nullptr;
    bool Same=Eligible&&LastPublishedMesh.Get()==Asset&&LastPublishedObject==GetMeshObject()
        &&LastPublishedLOD==GetPredictedLODLevel()&&LastPublishedRevision==GetBoneTransformRevisionNumber();
    if(Same)
    {
        const auto& Current=GetComponentSpaceTransforms();Same=Current.Num()==Pose.Num();
        for(int32 I=0;Same&&I<Pose.Num();++I)Same=Pose[I].Equals(Current[I],0.);
    }
    if(Same&&bPoseHistorySettled){++UnchangedPoseSkipCount;return;}
    // Submit one equal pose on a later frame before reusing it, so previous-pose
    // velocity history settles. Never quantize transforms or skip moving poses.
    bPoseHistorySettled=Same&&LastPublishedFrame!=GFrameCounter;
    GetEditableComponentSpaceTransforms()=Pose;
    bNeedToFlipSpaceBaseBuffers=true;
    Super::FinalizeBoneTransform();
    UpdateChildTransforms();MarkRenderDynamicDataDirty();
    LastPublishedMesh=GetSkeletalMeshAsset();LastPublishedObject=GetMeshObject();
    LastPublishedRevision=GetBoneTransformRevisionNumber();LastPublishedFrame=GFrameCounter;
    LastPublishedLOD=GetPredictedLODLevel();
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
