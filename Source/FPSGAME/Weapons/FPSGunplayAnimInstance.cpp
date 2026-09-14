#include "FPSGunplayAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Animation/BoneReference.h"

// Apply cartridge visibility after blending so a partially loaded cylinder
// never gains live rounds from the idle pose. Baked extraction stays intact.
struct FDW715CartridgePose : FAnimNode_Base
{
    FPoseLink Source;
    FBoneReference Cases[6], Rounds[6];
    bool bEnabled = false;
    int32 LiveRounds = 6, Cartridges = 6;
    FDW715CartridgePose()
    {
        for (int32 I = 0; I < 6; ++I)
        {
            Cases[I].BoneName = *FString::Printf(TEXT("WPN_Case_%d"), I);
            Rounds[I].BoneName = *FString::Printf(TEXT("WPN_Round_%d"), I);
        }
    }
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override { Source.Initialize(Context); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
    {
        Source.CacheBones(Context);
        const auto& Bones = Context.AnimInstanceProxy->GetRequiredBones();
        for (int32 I = 0; I < 6; ++I)
        {
            if (Bones.GetReferenceSkeleton().FindBoneIndex(Cases[I].BoneName) != INDEX_NONE) Cases[I].Initialize(Bones);
            if (Bones.GetReferenceSkeleton().FindBoneIndex(Rounds[I].BoneName) != INDEX_NONE) Rounds[I].Initialize(Bones);
        }
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override { Source.Update(Context); }
    virtual void Evaluate_AnyThread(FPoseContext& Output) override
    {
        Source.Evaluate(Output);
        if (!bEnabled) return;
        const auto& Bones = Output.Pose.GetBoneContainer();
        for (int32 I = 0; I < 6; ++I)
        {
            if (I >= Cartridges && Cases[I].IsValidToEvaluate(Bones))
                Output.Pose[Cases[I].GetCompactPoseIndex(Bones)].SetScale3D(FVector::ZeroVector);
            if (I >= LiveRounds && Rounds[I].IsValidToEvaluate(Bones))
                Output.Pose[Rounds[I].GetCompactPoseIndex(Bones)].SetScale3D(FVector::ZeroVector);
        }
    }
};

struct FFPSGunplayAnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle;
    FAnimNode_SequenceEvaluator_Standalone Aim;
    FAnimNode_SequenceEvaluator_Standalone Action;
    FAnimNode_TwoWayBlend AimBlend;
    FAnimNode_TwoWayBlend ActionBlend;
    FDW715CartridgePose CartridgePose;

    explicit FFPSGunplayAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        AimBlend.A.SetLinkNode(&Idle);
        AimBlend.B.SetLinkNode(&Aim);
        ActionBlend.A.SetLinkNode(&AimBlend);
        ActionBlend.B.SetLinkNode(&Action);
        CartridgePose.Source.SetLinkNode(&ActionBlend);
    }

    virtual FAnimNode_Base* GetCustomRootNode() override { return &CartridgePose; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Idle, &Aim, &Action, &AimBlend, &ActionBlend, &CartridgePose});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const UFPSGunplayAnimInstance* Data = CastChecked<UFPSGunplayAnimInstance>(Instance);
        CartridgePose.bEnabled = Data->bRevolver;
        CartridgePose.LiveRounds = Data->RevolverLiveRounds;
        CartridgePose.Cartridges = Data->RevolverCartridges;
        Idle.SetSequence(Data->IdleClip);
        Aim.SetSequence(Data->AimClip ? Data->AimClip : Data->IdleClip);
        Action.SetSequence(Data->ActionClip ? Data->ActionClip : Data->IdleClip);
        const auto LoopTime = [](UAnimSequence* Clip, float Time)
        {
            return Clip && Clip->GetPlayLength() > SMALL_NUMBER ? FMath::Fmod(Time, Clip->GetPlayLength()) : 0.0f;
        };
        Idle.SetExplicitTime(LoopTime(Data->IdleClip, Data->BaseTime));
        // A stable aim reference makes entering ADS deterministic. Breathing is a separate small pose layer.
        Aim.SetExplicitTime(0.0f);
        Action.SetExplicitTime(Data->ActionTime);
        AimBlend.Alpha = Data->AimAlpha;
        ActionBlend.Alpha = Data->ActionClip ? Data->ActionAlpha : 0.0f;
    }
};

FAnimInstanceProxy* UFPSGunplayAnimInstance::CreateAnimInstanceProxy() { return new FFPSGunplayAnimProxy(this); }
void UFPSGunplayAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
