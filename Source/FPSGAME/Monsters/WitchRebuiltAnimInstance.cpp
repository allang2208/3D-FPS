#include "WitchRebuiltAnimInstance.h"
#include "WitchRebuiltMonster.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "BoneControllers/AnimNode_CopyBone.h"
#include "BoneControllers/AnimNode_StrideWarping.h"
#include "BoneControllers/AnimNode_FootPlacement.h"
#include "BoneControllers/AnimNode_LegIK.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

struct FWitchRebuiltProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle, Walk, Turn, Action;
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_TwoWayBlend IdleTurn, ActionTransition, State;
    FAnimNode_TwoWayBlend Locomotion;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FAnimNode_CopyBone LeftTarget, RightTarget;
    FAnimNode_StrideWarping Stride;
    FAnimNode_FootPlacement Feet;
    FAnimNode_LegIK Legs;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;

    explicit FWitchRebuiltProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        IdleTurn.A.SetLinkNode(&Idle); IdleTurn.B.SetLinkNode(&Turn);
        Locomotion.A.SetLinkNode(&IdleTurn); Locomotion.B.SetLinkNode(&Walk);
        Previous.Mode = ESnapshotSourceMode::SnapshotPin;
        State.A.SetLinkNode(&Locomotion); State.B.SetLinkNode(&Action);
        ActionTransition.A.SetLinkNode(&Previous); ActionTransition.B.SetLinkNode(&State);
        ToComponent.LocalPose.SetLinkNode(&ActionTransition);
        LeftTarget.ComponentPose.SetLinkNode(&ToComponent);
        RightTarget.ComponentPose.SetLinkNode(&LeftTarget);
        Stride.ComponentPose.SetLinkNode(&RightTarget);
        Feet.ComponentPose.SetLinkNode(&Stride);
        Legs.ComponentPose.SetLinkNode(&Feet);
        ToLocal.ComponentPose.SetLinkNode(&Legs);
        LeftTarget.SourceBone.BoneName = TEXT("foot_l"); LeftTarget.TargetBone.BoneName = TEXT("ik_foot_l");
        RightTarget.SourceBone.BoneName = TEXT("foot_r"); RightTarget.TargetBone.BoneName = TEXT("ik_foot_r");
        for (auto* Copy : {&LeftTarget, &RightTarget})
        {
            Copy->bCopyTranslation = true; Copy->bCopyRotation = true;
            Copy->ControlSpace = BCS_ComponentSpace; Copy->Alpha = 1.f;
        }
        Stride.Mode = EWarpingEvaluationMode::Manual;
        Stride.bDisableIfMissingRootMotion = false;
        Stride.PelvisBone.BoneName = TEXT("pelvis");
        Stride.IKFootRootBone.BoneName = TEXT("ik_foot_root");
        Stride.Alpha = 1.f;
        Feet.PlantSpeedMode = EWarpingEvaluationMode::Manual;
        Feet.PelvisBone.BoneName = TEXT("pelvis");
        Feet.IKFootRootBone.BoneName = TEXT("ik_foot_root");
        Feet.PlantSettings.LockType = EFootPlacementLockType::PivotAroundBall;
        // Curves retain source-world toe speed, so the support threshold uses source units.
        Feet.PlantSettings.SpeedThreshold = 60.f;
        Feet.PlantSettings.UnalignmentSpeedThreshold = 200.f;
        Feet.PlantSettings.UnplantRadius = 22.f;
        Feet.PlantSettings.DistanceToGround = 8.f;
        Feet.PelvisSettings.MaxOffset = 22.f;
        Feet.PelvisSettings.MaxOffsetHorizontal = 8.f;
        Feet.TraceSettings.MaxGroundPenetration = 1.f;
        Feet.TraceSettings.SweepRadius = 3.f;
        Feet.Alpha = 1.f;
        Legs.Alpha = 1.f;
        Legs.SoftPercentLength = .97f;
        Legs.SoftAlpha = 1.f;
        for (const TCHAR* Side : {TEXT("l"), TEXT("r")})
        {
            const FString S(Side);
            auto& Warp = Stride.FootDefinitions.AddDefaulted_GetRef();
            Warp.IKFootBone.BoneName = FName(*(TEXT("ik_foot_") + S));
            Warp.FKFootBone.BoneName = FName(*(TEXT("foot_") + S));
            Warp.ThighBone.BoneName = FName(*(TEXT("thigh_") + S));
            auto& Plant = Feet.LegDefinitions.AddDefaulted_GetRef();
            Plant.IKFootBone = Warp.IKFootBone; Plant.FKFootBone = Warp.FKFootBone;
            Plant.BallBone.BoneName = FName(*(TEXT("ball_") + S));
            Plant.NumBonesInLimb = 2;
            Plant.SpeedCurveName = FName(*(TEXT("FootSpeed_") + S));
            auto& Leg = Legs.LegsDefinition.AddDefaulted_GetRef();
            Leg.IKFootBone = Warp.IKFootBone; Leg.FKFootBone = Warp.FKFootBone;
            Leg.NumBonesInLimb = 2;
            // Preserve the source knee plane; foot orientation is aligned by FootPlacement.
            Leg.bEnableKneeTwistCorrection = true;
        }
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &ToLocal; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Idle, &Walk, &Turn, &Action, &Previous, &IdleTurn, &ActionTransition, &State, &Locomotion, &ToComponent, &LeftTarget, &RightTarget,
            &Stride, &Feet, &Legs, &ToLocal});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UWitchRebuiltAnimInstance>(Instance);
        Idle.SetSequence(Data->IdleClip); Walk.SetSequence(Data->WalkClip);
        Turn.SetSequence(Data->TurnClip ? Data->TurnClip : Data->IdleClip);
        Action.SetSequence(Data->ActiveClip); Action.SetShouldLoop(false);
        Action.SetTeleportToExplicitTime(true); Action.SetExplicitTime(Data->ClipTime);
        Previous.Snapshot = Data->PreviousPose;
        ActionTransition.Alpha = Data->PreviousPose.bIsValid ? Data->BlendAlpha : 1.f;
        State.Alpha = Data->bLooping ? 0.f : 1.f;
        IdleTurn.Alpha = Data->TurnAlpha; Turn.SetExplicitTime(Data->TurnTime);
        for (auto* Node : {&Idle, &Walk, &Turn})
        {
            Node->SetShouldLoop(true); Node->SetTeleportToExplicitTime(true);
        }
        Idle.SetExplicitTime(Data->IdleTime); Walk.SetExplicitTime(Data->WalkTime);
        Locomotion.Alpha = Data->WalkAlpha;
        Stride.StrideScale = Data->bLooping ? FMath::Lerp(1.f, Data->StrideScale, Data->BlendAlpha) : 1.f;
        Stride.StrideDirection = Data->StrideDirection;
        Feet.Alpha = Data->GroundAlpha;
    }
};

void UWitchRebuiltAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    const auto* Character = Cast<AWitchRebuiltMonster>(TryGetPawnOwner());
    if (!Character) return;
    IdleClip = Character->IdleClip; WalkClip = Character->WalkClip;
    const float Yaw = Character->GetActorRotation().Yaw;
    const float YawRate = bHasYaw ? FMath::FindDeltaAngleDegrees(PreviousYaw, Yaw) / FMath::Max(.001f, DeltaSeconds) : 0.f;
    PreviousYaw = Yaw; bHasYaw = true;
    TurnClip = YawRate < 0.f ? Character->TurnLeftClip : Character->TurnRightClip;
    const float DesiredTurn = Character->GetVelocity().Size2D() < 8.f ? FMath::Clamp(FMath::Abs(YawRate) / 45.f, 0.f, 1.f) : 0.f;
    TurnAlpha = FMath::FInterpTo(TurnAlpha, DesiredTurn, DeltaSeconds, 10.f);
    if (TurnClip) TurnTime = FMath::Fmod(TurnTime + DeltaSeconds * FMath::Clamp(FMath::Abs(YawRate) / 60.f, .5f, 1.6f), TurnClip->GetPlayLength());
    // The shared stagger clock advances the hit evaluator, including its entrance blend.
    if (Character->State == ENurseState::Stagger) BlendAlpha = FMath::Clamp(ClipTime / .15f, 0.f, 1.f);
    const float Dt = FMath::Max(0.f, DeltaSeconds);
    const float Speed = Character->GetVelocity().Size2D();
    WalkAlpha = FMath::FInterpTo(WalkAlpha, FMath::Clamp(Speed / 15.f, 0.f, 1.f), Dt, 7.f);
    StrideScale = FMath::Lerp(1.f, Character->WalkStrideScale, WalkAlpha);
    const float Rate = Speed / FMath::Max(1.f, Character->SourceWalkSpeed * Character->WalkStrideScale);
    if (WalkClip) WalkTime = FMath::Fmod(WalkTime + Dt * Rate, FMath::Max(.01f, WalkClip->GetPlayLength()));
    if (IdleClip) IdleTime = FMath::Fmod(IdleTime + Dt, FMath::Max(.01f, IdleClip->GetPlayLength()));
    GroundAlpha = FMath::FInterpTo(GroundAlpha, Character->GetCharacterMovement()->IsMovingOnGround() ? 1.f : 0.f, Dt, 12.f);
    StrideDirection = GetSkelMeshComponent()->GetComponentTransform().InverseTransformVectorNoScale(Character->GetActorForwardVector());
}

FAnimInstanceProxy* UWitchRebuiltAnimInstance::CreateAnimInstanceProxy() { return new FWitchRebuiltProxy(this); }
void UWitchRebuiltAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
