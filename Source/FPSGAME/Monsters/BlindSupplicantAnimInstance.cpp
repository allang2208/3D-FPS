#include "BlindSupplicantAnimInstance.h"
#include "BlindSupplicantMonster.h"
#include "HumanoidKnockdownComponent.h"
#include "M07GillContactNode.h"
#include "MonsterRecoveryGroundNode.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"

namespace BlindSupplicantAnimation
{
// Every reaction has an actual M07 clip. No named-spine procedural fallback is
// needed, so this proxy never relies on FatZombie/Mutant3's Spine/Spine02 names.
struct FPresentationProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_SequenceEvaluator_Standalone Outgoing;
    FAnimNode_TwoWayBlend Source;
    FAnimNode_SequenceEvaluator_Standalone Current;
    FAnimNode_TwoWayBlend Transition;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FM07GillContactNode GillContact;
    FMonsterRecoveryGroundNode RecoveryGround;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;

    explicit FPresentationProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Previous.Mode = ESnapshotSourceMode::SnapshotPin;
        Source.A.SetLinkNode(&Previous);
        Source.B.SetLinkNode(&Outgoing);
        Transition.A.SetLinkNode(&Source);
        Transition.B.SetLinkNode(&Current);
        ToComponent.LocalPose.SetLinkNode(&Transition);
        GillContact.ComponentPose.SetLinkNode(&ToComponent);
        RecoveryGround.ComponentPose.SetLinkNode(&GillContact);
        ToLocal.ComponentPose.SetLinkNode(&RecoveryGround);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &ToLocal; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Previous, &Outgoing, &Source, &Current, &Transition, &ToComponent, &GillContact, &RecoveryGround, &ToLocal});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UBlindSupplicantAnimInstance>(Instance);
        const auto* Monster=Cast<ABlindSupplicantMonster>(Instance->TryGetPawnOwner());
        RecoveryGround.Prepare(Monster);
        GillContact.Alpha=Monster && Monster->bEnableGillBoneClearance && Monster->State!=ENurseState::Dead &&
            (!Monster->Knockdown || !Monster->Knockdown->IsControlling()) ? 1.f : 0.f;
        GillContact.MaxOpeningDegrees=Monster ? Monster->GillClearanceAngleDegrees : 18.f;
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
