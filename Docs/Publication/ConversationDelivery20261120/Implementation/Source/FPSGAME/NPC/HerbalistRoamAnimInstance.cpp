#include "HerbalistRoamAnimInstance.h"

#include "Animation/AnimationPoseData.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstanceProxy.h"
#include "AnimationRuntime.h"

namespace
{
struct FHerbalistRoamProxy final : FAnimSingleNodeInstanceProxy
{
    explicit FHerbalistRoamProxy(UAnimInstance* Owner) : FAnimSingleNodeInstanceProxy(Owner) {}

    const UAnimSequence* Walk = nullptr;
    float Seconds = 0.f;
    float Weight = 0.f;

    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimSingleNodeInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Anim = CastChecked<UHerbalistRoamAnimInstance>(Instance);
        Walk = Anim->Walk;
        Seconds = Anim->WalkSeconds;
        Weight = Anim->WalkWeight;
    }

    virtual bool Evaluate(FPoseContext& Output) override
    {
        if (!Walk || Weight < ZERO_ANIMWEIGHT_THRESH)
            return FAnimSingleNodeInstanceProxy::Evaluate(Output);

        FAnimationPoseData Result(Output);
        const FAnimExtractContext Context(double(Seconds), false, {}, true);
        if (Weight >= 1.f - ZERO_ANIMWEIGHT_THRESH)
        {
            Walk->GetAnimationPose(Result, Context);
            return true;
        }
        FAnimSingleNodeInstanceProxy::Evaluate(Output);
        FPoseContext Walking(Output);
        FAnimationPoseData WalkPose(Walking);
        Walk->GetAnimationPose(WalkPose, Context);
        FAnimationRuntime::BlendTwoPosesTogetherInPlace(Result, WalkPose, 1.f - Weight);
        return true;
    }
};
}

FAnimInstanceProxy* UHerbalistRoamAnimInstance::CreateAnimInstanceProxy()
{
    return new FHerbalistRoamProxy(this);
}
