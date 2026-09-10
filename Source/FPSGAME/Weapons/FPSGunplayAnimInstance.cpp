#include "FPSGunplayAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"

struct FFPSGunplayAnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle;
    FAnimNode_SequenceEvaluator_Standalone Aim;
    FAnimNode_SequenceEvaluator_Standalone Action;
    FAnimNode_TwoWayBlend AimBlend;
    FAnimNode_TwoWayBlend ActionBlend;

    explicit FFPSGunplayAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        AimBlend.A.SetLinkNode(&Idle);
        AimBlend.B.SetLinkNode(&Aim);
        ActionBlend.A.SetLinkNode(&AimBlend);
        ActionBlend.B.SetLinkNode(&Action);
    }

    virtual FAnimNode_Base* GetCustomRootNode() override { return &ActionBlend; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Idle, &Aim, &Action, &AimBlend, &ActionBlend});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const UFPSGunplayAnimInstance* Data = CastChecked<UFPSGunplayAnimInstance>(Instance);
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
