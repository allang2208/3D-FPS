#include "LumberjackAnimInstance.h"
#include "../Characters/FPSBodyStrideTiming.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "AnimationRuntime.h"

struct FLumberjackAnimProxy final : public FAnimInstanceProxy
{
    explicit FLumberjackAnimProxy(ULumberjackAnimInstance* InInstance)
        : FAnimInstanceProxy(InInstance)
    {
    }

    UAnimSequence* Clips[8] = {};
    FPSBodyAnimation::FStrideTiming WalkStride{nullptr};
    FPSBodyAnimation::FStrideTiming CarryStride{nullptr};
    bool bStridesBuilt = false;

    ELumberjackAnimState ActiveState = ELumberjackAnimState::Idle;
    ELumberjackAnimState PrevState = ELumberjackAnimState::Idle;
    float ActiveTime = 0.f;
    float PrevTime = 0.f;
    float BlendAlpha = 1.f;
    float StrideCycles = 0.f;

    ELumberjackAnimState DesiredState = ELumberjackAnimState::Idle;
    float SpeedCmPerSec = 0.f;
    float RateScale = 1.f;
    float OutNormalizedPhase = 0.f;

    UAnimSequence* ResolveClip(ELumberjackAnimState State) const
    {
        const int32 Idx = static_cast<int32>(State);
        if (Idx >= 0 && Idx < 8 && Clips[Idx])
        {
            return Clips[Idx];
        }
        return Clips[static_cast<int32>(ELumberjackAnimState::Idle)];
    }

    static bool IsLocomotionState(ELumberjackAnimState State)
    {
        return State == ELumberjackAnimState::Walk || State == ELumberjackAnimState::CarryLogWalk;
    }

    virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
        auto* Owner = Cast<ULumberjackAnimInstance>(InAnimInstance);
        if (!Owner) return;

        Clips[static_cast<int32>(ELumberjackAnimState::Idle)] = Owner->IdleClip;
        Clips[static_cast<int32>(ELumberjackAnimState::Walk)] = Owner->WalkClip;
        Clips[static_cast<int32>(ELumberjackAnimState::ChopTree)] = Owner->ChopTreeClip;
        Clips[static_cast<int32>(ELumberjackAnimState::SplitLog)] = Owner->SplitLogClip;
        Clips[static_cast<int32>(ELumberjackAnimState::SawLog)] = Owner->SawLogClip;
        Clips[static_cast<int32>(ELumberjackAnimState::CarryLogWalk)] = Owner->CarryLogWalkClip;
        Clips[static_cast<int32>(ELumberjackAnimState::DriveWagon)] = Owner->DriveWagonClip;
        Clips[static_cast<int32>(ELumberjackAnimState::SitTavern)] = Owner->SitTavernClip;

        if (!bStridesBuilt && Clips[static_cast<int32>(ELumberjackAnimState::Walk)])
        {
            UAnimSequence* BaseWalk = Clips[static_cast<int32>(ELumberjackAnimState::Walk)];
            WalkStride = FPSBodyAnimation::FStrideTiming(BaseWalk);
            UAnimSequence* CarryWalk = Clips[static_cast<int32>(ELumberjackAnimState::CarryLogWalk)];
            CarryStride = FPSBodyAnimation::FStrideTiming(CarryWalk ? CarryWalk : BaseWalk, BaseWalk);
            bStridesBuilt = true;
        }

        DesiredState = Owner->TargetState;
        SpeedCmPerSec = Owner->MoveSpeedCmPerSec;
        RateScale = FMath::Clamp(Owner->ActionRateScale, 0.5f, 1.5f);
        Owner->ActiveNormalizedPhase = OutNormalizedPhase;
    }

    virtual void Update(float DeltaSeconds) override
    {
        const float Dt = FMath::Clamp(DeltaSeconds, 0.f, 0.25f);
        if (DesiredState != ActiveState)
        {
            PrevState = ActiveState;
            PrevTime = ActiveTime;
            ActiveState = DesiredState;
            ActiveTime = IsLocomotionState(ActiveState) ? ActiveTime : 0.f;
            BlendAlpha = 0.f;
        }

        auto AdvanceClip = [&](ELumberjackAnimState State, float& InOutTime)
        {
            UAnimSequence* Clip = ResolveClip(State);
            if (!Clip) return;
            const float Len = FMath::Max(Clip->GetPlayLength(), SMALL_NUMBER);
            if (IsLocomotionState(State))
            {
                const auto& Timing = (State == ELumberjackAnimState::CarryLogWalk) ? CarryStride : WalkStride;
                const float StrideDist = FMath::Max(60.f, Timing.Distance(165.f));
                StrideCycles = FMath::Fmod(StrideCycles + (FMath::Max(SpeedCmPerSec, 35.f) * Dt) / StrideDist, 10000.f);
                InOutTime = Timing.Sample(StrideCycles);
            }
            else
            {
                const float Rate = (State == ELumberjackAnimState::Idle || State == ELumberjackAnimState::DriveWagon || State == ELumberjackAnimState::SitTavern) ? 1.f : RateScale;
                InOutTime = FMath::Fmod(InOutTime + Dt * Rate, Len);
                if (InOutTime < 0.f) InOutTime += Len;
            }
        };

        AdvanceClip(ActiveState, ActiveTime);
        if (BlendAlpha < 1.f)
        {
            AdvanceClip(PrevState, PrevTime);
            BlendAlpha = FMath::Min(1.f, BlendAlpha + Dt / 0.18f);
        }

        if (UAnimSequence* Cur = ResolveClip(ActiveState))
        {
            const float Len = FMath::Max(Cur->GetPlayLength(), SMALL_NUMBER);
            OutNormalizedPhase = FMath::Frac(ActiveTime / Len);
        }
    }

    virtual bool Evaluate(FPoseContext& Output) override
    {
        UAnimSequence* CurClip = ResolveClip(ActiveState);
        if (!CurClip)
        {
            Output.ResetToRefPose();
            return true;
        }

        FAnimationPoseData CurData(Output);
        CurClip->GetAnimationPose(CurData, FAnimExtractContext(double(ActiveTime), false));

        if (BlendAlpha < 0.999f)
        {
            UAnimSequence* PrevClip = ResolveClip(PrevState);
            if (PrevClip && PrevClip != CurClip)
            {
                FCompactPose PrevPose;
                FBlendedCurve PrevCurve;
                UE::Anim::FStackAttributeContainer PrevAttrs;
                PrevPose.SetBoneContainer(&Output.Pose.GetBoneContainer());
                PrevCurve.InitFrom(Output.Curve);
                FAnimationPoseData PrevData(PrevPose, PrevCurve, PrevAttrs);
                PrevClip->GetAnimationPose(PrevData, FAnimExtractContext(double(PrevTime), false));

                const float SmoothAlpha = FMath::SmoothStep(0.f, 1.f, BlendAlpha);
                FCompactPose BlendedPose;
                FBlendedCurve BlendedCurve;
                UE::Anim::FStackAttributeContainer BlendedAttrs;
                BlendedPose.SetBoneContainer(&Output.Pose.GetBoneContainer());
                BlendedCurve.InitFrom(Output.Curve);
                FAnimationPoseData BlendedData(BlendedPose, BlendedCurve, BlendedAttrs);
                FAnimationRuntime::BlendTwoPosesTogether(CurData, PrevData, SmoothAlpha, BlendedData);
                Output.Pose.MoveBonesFrom(BlendedPose);
                Output.Curve.MoveFrom(BlendedCurve);
                Output.CustomAttributes.MoveFrom(BlendedAttrs);
            }
        }
        return true;
    }
};

void ULumberjackAnimInstance::SetAnimInputs(ELumberjackAnimState InState, float InSpeedCmPerSec, float InRateScale)
{
    TargetState = InState;
    MoveSpeedCmPerSec = FMath::Max(0.f, InSpeedCmPerSec);
    ActionRateScale = FMath::Clamp(InRateScale, 0.5f, 1.5f);
}

FAnimInstanceProxy* ULumberjackAnimInstance::CreateAnimInstanceProxy()
{
    return new FLumberjackAnimProxy(this);
}

void ULumberjackAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy)
{
    delete static_cast<FLumberjackAnimProxy*>(InProxy);
}
