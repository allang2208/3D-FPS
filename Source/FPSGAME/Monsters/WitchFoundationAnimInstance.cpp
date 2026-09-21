#include "WitchFoundationAnimInstance.h"
#include "WitchMotionCandidate.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "BoneControllers/AnimNode_CopyBone.h"
#include "BoneControllers/AnimNode_StrideWarping.h"
#include "BoneControllers/AnimNode_FootPlacement.h"
#include "BoneControllers/AnimNode_LegIK.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

struct FWitchFoundationProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle, Walk;
    FAnimNode_TwoWayBlend Locomotion;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FAnimNode_CopyBone LeftTarget, RightTarget;
    FAnimNode_StrideWarping Stride;
    FAnimNode_FootPlacement Feet;
    FAnimNode_LegIK Legs;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;

    explicit FWitchFoundationProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Locomotion.A.SetLinkNode(&Idle); Locomotion.B.SetLinkNode(&Walk);
        ToComponent.LocalPose.SetLinkNode(&Locomotion);
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
        Nodes.Append({&Idle, &Walk, &Locomotion, &ToComponent, &LeftTarget, &RightTarget,
            &Stride, &Feet, &Legs, &ToLocal});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UWitchFoundationAnimInstance>(Instance);
        Idle.SetSequence(Data->IdleClip); Walk.SetSequence(Data->WalkClip);
        for (auto* Node : {&Idle, &Walk})
        {
            Node->SetShouldLoop(true); Node->SetTeleportToExplicitTime(true);
        }
        Idle.SetExplicitTime(Data->IdleTime); Walk.SetExplicitTime(Data->WalkTime);
        Locomotion.Alpha = Data->WalkAlpha;
        Stride.StrideScale = Data->StrideScale;
        Stride.StrideDirection = Data->StrideDirection;
        Feet.Alpha = Data->GroundAlpha;
    }
};

void UWitchFoundationAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    const auto* Character = Cast<AWitchMotionCandidate>(TryGetPawnOwner());
    if (!Character) return;
    IdleClip = Character->IdleClip; WalkClip = Character->WalkClip;
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

FAnimInstanceProxy* UWitchFoundationAnimInstance::CreateAnimInstanceProxy() { return new FWitchFoundationProxy(this); }
void UWitchFoundationAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
