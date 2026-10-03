#include "BlindSupplicantAnimInstance.h"
#include "BlindSupplicantMonster.h"
#include "HumanoidKnockdownComponent.h"
#include "M07GillContactNode.h"
#include "M07MembraneMotionNode.h"
#include "M07FootSupportSamples.h"
#include "MonsterRecoveryGroundNode.h"
#include "Animation/AnimInstanceProxy.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "AnimationRuntime.h"
#include "Animation/AnimationPoseData.h"

namespace BlindSupplicantAnimation
{
// Opposite knee planes can extend the blended leg farther than either source.
// Preserve the interpolated sole support, not just interpolated pelvis height.
// Only the transition pays for four foot transforms and bounded skin samples.
struct FSupportedTransition : FAnimNode_TwoWayBlend
{
    FBoneReference Feet[M07FootSupportSamples::BoneCount];
    FVector LocalSamples[UE_ARRAY_COUNT(M07FootSupportSamples::Samples)][M07FootSupportSamples::BoneCount];
    bool bPreserveSupport = false;
    bool bHasFeet = false;

    FSupportedTransition()
    {
        for (int32 I=0; I<M07FootSupportSamples::BoneCount; ++I)
            Feet[I].BoneName=M07FootSupportSamples::BoneNames[I];
    }

    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
    {
        FAnimNode_TwoWayBlend::CacheBones_AnyThread(Context);
        const auto& Bones=Context.AnimInstanceProxy->GetRequiredBones();
        bHasFeet=true;
        for (int32 I=0; I<M07FootSupportSamples::BoneCount; ++I)
        {
            Feet[I].Initialize(Bones);
            if (!Feet[I].IsValidToEvaluate(Bones)) { bHasFeet=false; continue; }
            const auto Index=Feet[I].GetCompactPoseIndex(Bones);
            FTransform Reference=Bones.GetRefPoseTransform(Index);
            for (auto Parent=Bones.GetParentBoneIndex(Index); Parent!=INDEX_NONE; Parent=Bones.GetParentBoneIndex(Parent))
                Reference*=Bones.GetRefPoseTransform(Parent);
            for (int32 S=0; S<UE_ARRAY_COUNT(M07FootSupportSamples::Samples); ++S)
                LocalSamples[S][I]=Reference.InverseTransformPosition(M07FootSupportSamples::Samples[S].ReferencePoint);
        }
    }

    double SupportHeight(const FCompactPose& Pose) const
    {
        const auto& Bones=Pose.GetBoneContainer();
        FTransform Components[M07FootSupportSamples::BoneCount];
        for (int32 I=0; I<M07FootSupportSamples::BoneCount; ++I)
        {
            const auto Index=Feet[I].GetCompactPoseIndex(Bones);
            Components[I]=Pose[Index];
            for (auto Parent=Bones.GetParentBoneIndex(Index); Parent!=INDEX_NONE; Parent=Bones.GetParentBoneIndex(Parent))
                Components[I]*=Pose[Parent];
        }
        double Minimum=TNumericLimits<double>::Max();
        for (int32 S=0; S<UE_ARRAY_COUNT(M07FootSupportSamples::Samples); ++S)
        {
            double Height=0.;
            for (int32 I=0; I<M07FootSupportSamples::BoneCount; ++I)
            {
                const double Weight=M07FootSupportSamples::Samples[S].Weights[I];
                if (Weight>0.) Height+=Components[I].TransformPosition(LocalSamples[S][I]).Z*Weight;
            }
            Minimum=FMath::Min(Minimum,Height);
        }
        return Minimum;
    }

    virtual void Evaluate_AnyThread(FPoseContext& Output) override
    {
        if (!bPreserveSupport || !bHasFeet || !FAnimWeight::IsRelevant(InternalBlendAlpha) ||
            FAnimWeight::IsFullWeight(InternalBlendAlpha))
        {
            FAnimNode_TwoWayBlend::Evaluate_AnyThread(Output);
            return;
        }
        A.Evaluate(Output);
        FPoseContext Destination(Output);
        B.Evaluate(Destination);
        const double Height=FMath::Lerp(SupportHeight(Output.Pose),SupportHeight(Destination.Pose),double(InternalBlendAlpha));
        FAnimationPoseData Blended(Output);
        const FAnimationPoseData Target(Destination);
        FAnimationRuntime::BlendTwoPosesTogetherInPlace(Blended,Target,1.f-InternalBlendAlpha);
        const double Lift=FMath::Max(0.,Height-SupportHeight(Output.Pose));
        Output.Pose[FCompactPoseBoneIndex(0)].AddToTranslation(FVector(0.,0.,Lift));
    }
};

// Every reaction has an actual M07 clip. No named-spine procedural fallback is
// needed, so this proxy never relies on FatZombie/Mutant3's Spine/Spine02 names.
struct FPresentationProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_SequenceEvaluator_Standalone Outgoing;
    FAnimNode_TwoWayBlend Source;
    FAnimNode_SequenceEvaluator_Standalone Current;
    FSupportedTransition Transition;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FM07MembraneMotionNode MembraneMotion;
    FM07GillContactNode GillContact;
    FMonsterRecoveryGroundNode RecoveryGround;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    FVector PreviousVelocity=FVector::ZeroVector;
    bool bHasVelocity=false;

    explicit FPresentationProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Previous.Mode = ESnapshotSourceMode::SnapshotPin;
        Source.A.SetLinkNode(&Previous);
        Source.B.SetLinkNode(&Outgoing);
        Transition.A.SetLinkNode(&Source);
        Transition.B.SetLinkNode(&Current);
        ToComponent.LocalPose.SetLinkNode(&Transition);
        MembraneMotion.ComponentPose.SetLinkNode(&ToComponent);
        GillContact.ComponentPose.SetLinkNode(&MembraneMotion);
        RecoveryGround.ComponentPose.SetLinkNode(&GillContact);
        ToLocal.ComponentPose.SetLinkNode(&RecoveryGround);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &ToLocal; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Previous, &Outgoing, &Source, &Current, &Transition, &ToComponent, &MembraneMotion, &GillContact, &RecoveryGround, &ToLocal});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UBlindSupplicantAnimInstance>(Instance);
        const auto* Monster=Cast<ABlindSupplicantMonster>(Instance->TryGetPawnOwner());
        RecoveryGround.Prepare(Monster);
        const bool bCoherent=Monster && Monster->bUseCoherentGillMotion && Monster->State!=ENurseState::Dead &&
            (!Monster->Knockdown || !Monster->Knockdown->IsControlling());
        FVector Acceleration=FVector::ZeroVector, Rear=FVector(0.,-1.,0.);
        if (Monster)
        {
            const FTransform Frame=Monster->GetMesh()->GetComponentTransform();
            const FVector Velocity=Monster->GetVelocity();
            if (DeltaSeconds>UE_SMALL_NUMBER)
            {
                if (bHasVelocity) Acceleration=Frame.InverseTransformVectorNoScale((Velocity-PreviousVelocity)/DeltaSeconds);
                PreviousVelocity=Velocity;
                bHasVelocity=bCoherent;
            }
            Rear=Frame.InverseTransformVectorNoScale(-Monster->GetActorForwardVector());
        }
        MembraneMotion.Prepare(DeltaSeconds,bCoherent,Acceleration,Rear);
        GillContact.Alpha=Monster && Monster->bEnableGillBoneClearance && Monster->State!=ENurseState::Dead &&
            (!Monster->Knockdown || !Monster->Knockdown->IsControlling()) ? 1.f : 0.f;
        GillContact.MaxOpeningDegrees=Monster ? Monster->GillClearanceAngleDegrees : 18.f;
        if (Monster)
        {
            const auto* Mesh=Monster->GetMesh();
            GillContact.RearDirection=Mesh->GetComponentTransform().InverseTransformVectorNoScale(-Monster->GetActorForwardVector());
            const bool bNear=Mesh->GetPredictedLODLevel()==0;
            GillContact.SampleStride=bNear?1:3;
            GillContact.SolverPasses=bNear?2:1;
        }
        Previous.Snapshot = Data->PreviousPose;
        Outgoing.SetSequence(Data->OutgoingLoop);
        Outgoing.SetShouldLoop(true);
        Outgoing.SetTeleportToExplicitTime(true);
        Outgoing.SetExplicitTime(Data->OutgoingLoopTime);
        Source.Alpha = Data->OutgoingLoop ? 1.f : 0.f;
        Current.SetSequence(Data->ActiveClip);
        Current.SetShouldLoop(Data->bLooping);
        Current.SetTeleportToExplicitTime(true);
        Current.SetExplicitTime(Data->ClipTime);
        Transition.Alpha = Data->PreviousPose.bIsValid ? Data->BlendAlpha : 1.f;
        Transition.bPreserveSupport = Monster && Data->bLooping && Monster->State!=ENurseState::Dead &&
            (!Monster->Knockdown || !Monster->Knockdown->IsControlling()) &&
            (Data->ActiveClip==Monster->IdleClip || Data->ActiveClip==Monster->SlowWalkClip ||
             Data->ActiveClip==Monster->ChaseClip || Data->ActiveClip==Monster->WalkClip);
    }
};
}

FAnimInstanceProxy* UBlindSupplicantAnimInstance::CreateAnimInstanceProxy()
{
    return new BlindSupplicantAnimation::FPresentationProxy(this);
}
void UBlindSupplicantAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy)
{
    delete Proxy;
}
