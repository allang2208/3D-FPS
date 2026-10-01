#include "FPSGunplayAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Animation/BoneReference.h"
#include "Components/SkeletalMeshComponent.h"
#include "PistolDualAimNode.h"
#include "SteelGauntletPoseNode.h"
#include "GripPoseLayer.h"
#include "WeaponGripProfile.h"
#include "WeaponGripProfileNode.h"

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
    FAnimNode_SequenceEvaluator_Standalone Sprint;
    FAnimNode_SequenceEvaluator_Standalone SprintLoop;
    FAnimNode_TwoWayBlend SprintMotionBlend;
    FAnimNode_TwoWayBlend SprintBlend;
    FAnimNode_TwoWayBlend AimBlend;
    FAnimNode_TwoWayBlend ActionBlend;
    FDW715CartridgePose CartridgePose;
    FAnimNode_SequenceEvaluator_Standalone DualAimReference;
    FPistolDualAimNode DualAim;
    FSteelGauntletPoseNode SteelGauntletPose;
    // GripLayer56: one layer per channel, before the channels are blended.
    FGripPoseLayerNode IdleGrip, SprintGrip, AimGrip, ActionGrip;
    FWeaponGripProfileNode IdleProfile, AimProfile, ActionProfile, SprintProfile, SprintLoopProfile;

    explicit FFPSGunplayAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        IdleGrip.Source.SetLinkNode(&Idle);
        IdleProfile.Source.SetLinkNode(&IdleGrip);
        SprintBlend.A.SetLinkNode(&IdleProfile);
        SprintProfile.Source.SetLinkNode(&Sprint);
        SprintLoopProfile.Source.SetLinkNode(&SprintLoop);
        SprintMotionBlend.A.SetLinkNode(&SprintProfile);
        SprintMotionBlend.B.SetLinkNode(&SprintLoopProfile);
        SprintGrip.Source.SetLinkNode(&SprintMotionBlend);
        SprintBlend.B.SetLinkNode(&SprintGrip);
        AimBlend.A.SetLinkNode(&SprintBlend);
        AimGrip.Source.SetLinkNode(&Aim);
        AimProfile.Source.SetLinkNode(&AimGrip);
        AimBlend.B.SetLinkNode(&AimProfile);
        ActionBlend.A.SetLinkNode(&AimBlend);
        ActionGrip.Source.SetLinkNode(&Action);
        ActionProfile.Source.SetLinkNode(&ActionGrip);
        ActionBlend.B.SetLinkNode(&ActionProfile);
        CartridgePose.Source.SetLinkNode(&ActionBlend);
        DualAim.Source.SetLinkNode(&CartridgePose);
        DualAim.Reference.SetLinkNode(&DualAimReference);
        SteelGauntletPose.Source.SetLinkNode(&DualAim);
    }

    virtual FAnimNode_Base* GetCustomRootNode() override { return &SteelGauntletPose; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Idle, &Sprint, &SprintLoop, &SprintMotionBlend, &SprintBlend, &Aim, &Action, &AimBlend, &ActionBlend, &CartridgePose, &DualAimReference, &DualAim, &SteelGauntletPose,
            &IdleGrip, &SprintGrip, &AimGrip, &ActionGrip,
            &IdleProfile, &AimProfile, &ActionProfile, &SprintProfile, &SprintLoopProfile});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const UFPSGunplayAnimInstance* Data = CastChecked<UFPSGunplayAnimInstance>(Instance);
        DualAim.bEnabled=Data->bDualPistolAim;
        DualAim.Side=FMath::Clamp(Data->DualPistolSide,0,1);
        DualAim.Weight=Data->DualPistolAimAlpha;
        if(DualAim.bEnabled)DualAim.Target=GetSkelMeshComponent()->GetComponentTransform().InverseTransformPosition(Data->DualPistolAimTargetWorld);
        DualAimReference.SetSequence(Data->IdleClip);
        DualAimReference.SetExplicitTime(0.f);
        CartridgePose.bEnabled = Data->bRevolver;
        CartridgePose.LiveRounds = Data->RevolverLiveRounds;
        CartridgePose.Cartridges = Data->RevolverCartridges;
        Idle.SetSequence(Data->IdleClip);
        Aim.SetSequence(Data->AimClip ? Data->AimClip : Data->IdleClip);
        Action.SetSequence(Data->ActionClip ? Data->ActionClip : Data->IdleClip);
        Sprint.SetSequence(Data->SprintClip ? Data->SprintClip : Data->IdleClip);
        Sprint.SetExplicitTime(Data->SprintTime);
        SprintLoop.SetSequence(Data->SprintLoopClip ? Data->SprintLoopClip : Data->IdleClip);
        SprintLoop.SetExplicitTime(Data->SprintLoopTime);
        SprintMotionBlend.Alpha = Data->SprintLoopClip ? Data->SprintLoopAlpha : 0.f;
        // Locomotion precedes ADS and action blending: reload/fire own their contacts.
        SprintBlend.Alpha = Data->SprintClip ? Data->SprintAlpha : 0.f;
        const auto LoopTime = [](UAnimSequence* Clip, float Time)
        {
            return Clip && Clip->GetPlayLength() > SMALL_NUMBER ? FMath::Fmod(Time, Clip->GetPlayLength()) : 0.0f;
        };
        Idle.SetExplicitTime(LoopTime(Data->IdleClip, Data->BaseTime));
        DualAimReference.SetExplicitTime(LoopTime(Data->IdleClip, Data->BaseTime));
        // A stable aim reference makes entering ADS deterministic. Breathing is a separate small pose layer.
        Aim.SetExplicitTime(0.0f);
        Action.SetExplicitTime(Data->ActionTime);
        AimBlend.Alpha = Data->AimAlpha;
        ActionBlend.Alpha = Data->ActionClip ? Data->ActionAlpha : 0.0f;
        const auto Grip = [](FGripPoseLayerNode& Node, bool bEnabled, UAnimSequence* Base, UAnimSequence* Family, UAnimSequence* Clip)
        {
            Node.bEnabled = bEnabled && Base && Family;
            Node.BaseRef = Base; Node.FamilyRef = Family; Node.Clip = Clip;
        };
        Grip(IdleGrip, Data->bGripIdle, Data->GripIdleBase, Data->GripIdleFamily, Data->IdleClip);
        Grip(SprintGrip, Data->bGripSprint && Data->SprintClip, Data->GripIdleBase, Data->GripIdleFamily, Data->SprintClip);
        Grip(AimGrip, Data->bGripAim, Data->GripAimBase, Data->GripAimFamily, Data->AimClip);
        Grip(ActionGrip, Data->bGripAction, Data->bGripActionAim ? Data->GripAimBase : Data->GripIdleBase,
            Data->bGripActionAim ? Data->GripAimFamily : Data->GripIdleFamily, Data->ActionClip);
        const auto Profile=[Data](FWeaponGripProfileNode& Node,UAnimSequence* Clip,float Time)
        {
            Node.Profile=Data->GripProfile;Node.Clip=Clip;Node.Time=Time;
        };
        Profile(IdleProfile,Data->IdleClip,LoopTime(Data->IdleClip,Data->BaseTime));
        Profile(AimProfile,Data->AimClip?Data->AimClip:Data->IdleClip,0.f);
        Profile(ActionProfile,Data->ActionClip?Data->ActionClip:Data->IdleClip,Data->ActionTime);
        Profile(SprintProfile,Data->SprintClip?Data->SprintClip:Data->IdleClip,Data->SprintTime);
        Profile(SprintLoopProfile,Data->SprintLoopClip?Data->SprintLoopClip:Data->IdleClip,Data->SprintLoopTime);
        SteelGauntletPose.Configure(*Data);
    }
};

FAnimInstanceProxy* UFPSGunplayAnimInstance::CreateAnimInstanceProxy() { return new FFPSGunplayAnimProxy(this); }
void UFPSGunplayAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
