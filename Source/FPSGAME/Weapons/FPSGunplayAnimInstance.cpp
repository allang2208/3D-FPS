#include "FPSGunplayAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Animation/BoneReference.h"
#include "AnimationRuntime.h"
#include "BonePose.h"
#include "CustomBoneIndexArray.h"
#include "Components/SkeletalMeshComponent.h"
#include "PistolDualAimNode.h"
#include "SteelGauntletPoseNode.h"
#include "GripPoseLayer.h"
#include "WeaponGripProfile.h"
#include "WeaponGripProfileNode.h"
#include "Super90SupportArmNode.h"

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

// 单手副手枪沿用主手枪这张图：求值后把姿态**在组件空间**里绕镜面反射。
// 镜面由 MirrorPlane 给出（角色每帧按"物体空间里的相机右轴"换算），对任意机位/开镜
// 旋转都成立；不能用固定的 EAxis::X——开镜标定后的旋转带俯仰和横滚，X 面不再等于
// 相机竖直面，枪会歪、并被推穿近裁剪面。
// 全骨架统一反射，枪械子树（WPN_root 以下）跟着被镜像的右手走，落点就是左手，
// 握持关系自动保持。组件保持正缩放，贴图/刻字/绕序都不翻面。
struct FLoneLeftHandMirrorNode : FAnimNode_Base
{
    FPoseLink Source;
    bool bEnabled = false;
    // 骨架里有武器根骨才为真；否则角色退回镜像场景节点。
    bool bReady = false;
    // 物体空间的镜面法线（单位向量）。角色每帧写入，指向相机的左/右轴在网格空间的方向。
    FVector MirrorPlane = FVector::RightVector;
    // 每帧复用的组件空间缓存，避免动画线程上重复分配。
    TArray<FTransform> SnapshotSpace, WriteSpace;

    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override { Source.Initialize(Context); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
    {
        Source.CacheBones(Context);
        // 只要骨架里还有 WPN_root 就说明这是可镜像的武器骨架；实际反射不依赖它。
        const FBoneContainer& Bones = Context.AnimInstanceProxy->GetRequiredBones();
        bReady = Bones.GetReferenceSkeleton().FindBoneIndex(TEXT("WPN_root")) != INDEX_NONE;
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override { Source.Update(Context); }
    virtual void Evaluate_AnyThread(FPoseContext& Output) override;
};

// 绕任意平面反射组件空间变换。N 是镜面法线（物体空间，单位向量）。
// 位置：P' = P - 2*(P·N)*N；旋转：M·R·M，M 为反射矩阵（此处用四元数等价式）。
static FORCEINLINE FVector MirrorPointAboutPlane(const FVector& P, const FVector& N)
{
    return P - 2.f * FVector::DotProduct(P, N) * N;
}

// 反射只翻法线方向上的分量；旋转的镜像是 R' = M·R·M。R 的轴是特征值 1 的方向，
// 故 M·R·M 的轴就是 M·a、角度取反，得到下面的轴角等价式。
static FORCEINLINE FQuat MirrorQuatAboutPlane(const FQuat& Q, const FVector& N)
{
    FVector Axis; float Angle;
    Q.ToAxisAndAngle(Axis, Angle);
    const FVector MirroredAxis = MirrorPointAboutPlane(Axis, N).GetSafeNormal();
    // 单位旋转或退化轴：保持原样，避免用零轴构造非归一化四元数。
    if (MirroredAxis.IsNearlyZero() || FMath::IsNearlyZero(Angle))
        return FQuat(Q).GetNormalized();
    return FQuat(MirroredAxis, -Angle);
}

void FLoneLeftHandMirrorNode::Evaluate_AnyThread(FPoseContext& Output)
{
    Source.Evaluate(Output);
    if (!bEnabled || !bReady) return;
    FCompactPose& Pose = Output.Pose;
    const FBoneContainer& Bones = Pose.GetBoneContainer();
    const int32 Num = Pose.GetNumBones();
    if (Num <= 0) return;

    const FVector N = MirrorPlane.GetSafeNormal();
    if (N.IsNearlyZero()) return;

    // 全骨架统一反射：每根骨的组件空间变换都换成镜面另一侧，握持关系自动保持
    // （枪跟着被镜像的右手走，落点就是左手）。不需要再把枪械子树单独重摆。
    SnapshotSpace.SetNumUninitialized(Num);
    for (int32 I = 0; I < Num; ++I)
    {
        const FCompactPoseBoneIndex Index(I);
        const FCompactPoseBoneIndex Parent = Bones.GetParentBoneIndex(Index);
        SnapshotSpace[I] = Parent.IsValid() ? Pose[Index] * SnapshotSpace[Parent.GetInt()] : Pose[Index];
    }

    // 先在组件空间反射，再换算回局部空间写回。
    WriteSpace.SetNumUninitialized(Num);
    for (int32 I = 0; I < Num; ++I)
    {
        const FCompactPoseBoneIndex Index(I);
        const FCompactPoseBoneIndex Parent = Bones.GetParentBoneIndex(Index);
        const FTransform Mirrored(MirrorQuatAboutPlane(SnapshotSpace[I].GetRotation(), N),
            MirrorPointAboutPlane(SnapshotSpace[I].GetTranslation(), N),
            SnapshotSpace[I].GetScale3D());
        WriteSpace[I] = Mirrored;
        Pose[Index] = Parent.IsValid() ? Mirrored * WriteSpace[Parent.GetInt()].Inverse() : Mirrored;
    }
}

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
    FWeaponGripProfileNode DualAimReferenceProfile;
    FPistolDualAimNode DualAim;
    FSteelGauntletPoseNode SteelGauntletPose;
    FSuper90SupportArmNode Super90SupportArm;
    FLoneLeftHandMirrorNode LoneLeftHandMirror;
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
        DualAimReferenceProfile.Source.SetLinkNode(&DualAimReference);
        DualAim.Reference.SetLinkNode(&DualAimReferenceProfile);
        SteelGauntletPose.Source.SetLinkNode(&DualAim);
        Super90SupportArm.Source.SetLinkNode(&SteelGauntletPose);
        LoneLeftHandMirror.Source.SetLinkNode(&Super90SupportArm);
    }

    virtual FAnimNode_Base* GetCustomRootNode() override { return &LoneLeftHandMirror; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Idle, &Sprint, &SprintLoop, &SprintMotionBlend, &SprintBlend, &Aim, &Action, &AimBlend, &ActionBlend, &CartridgePose, &DualAimReference, &DualAimReferenceProfile, &DualAim, &SteelGauntletPose, &Super90SupportArm, &LoneLeftHandMirror,
            &IdleGrip, &SprintGrip, &AimGrip, &ActionGrip,
            &IdleProfile, &AimProfile, &ActionProfile, &SprintProfile, &SprintLoopProfile});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        UFPSGunplayAnimInstance* Data = CastChecked<UFPSGunplayAnimInstance>(Instance);
        LoneLeftHandMirror.bEnabled = Data->bMirrorLeftHand;
        // 镜面法线由角色按"相机右轴在网格物体空间的方向"每帧给出，跟着开镜标定旋转走。
        LoneLeftHandMirror.MirrorPlane = Data->LeftHandMirrorPlane;
        // 骨架能否镜像在骨骼缓存时就确定了，实时回告角色（否则退回镜像场景节点）。
        Data->bLeftHandMirrorReady = LoneLeftHandMirror.bReady;
        DualAim.bEnabled=Data->bDualPistolAim;
        DualAim.Side=FMath::Clamp(Data->DualPistolSide,0,1);
        DualAim.Weight=Data->DualPistolAimAlpha;
        DualAim.ADSWeight=Data->LonePistolADSAlpha;
        DualAim.EyeDistance=Data->LonePistolEyeDistance;
        DualAim.OpticMount=Data->LonePistolOpticMount;
        DualAim.SightRear=Data->LonePistolSightRear;
        DualAim.SightFront=Data->LonePistolSightFront;
        DualAim.SightUp=Data->LonePistolSightUp;
        if(DualAim.OpticBone.BoneName!=Data->LonePistolSightBone)
        {
            DualAim.OpticBone.BoneName=Data->LonePistolSightBone;
            if(!DualAim.OpticBone.BoneName.IsNone())DualAim.OpticBone.Initialize(GetRequiredBones());
        }
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
        const float IdleTime = LoopTime(Data->IdleClip, Data->BaseTime);
        const float AimTime = Data->AimClip == Data->IdleClip ? IdleTime : 0.f;
        Idle.SetExplicitTime(IdleTime);
        DualAimReference.SetExplicitTime(LoopTime(Data->IdleClip, Data->BaseTime));
        // Shared-grip ADS must sample the same frame on both sides of the blend.
        Aim.SetExplicitTime(AimTime);
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
        // Match the visible idle, including sparse native-grip corrections.
        Profile(DualAimReferenceProfile,Data->IdleClip,IdleTime);
        if(Data->LonePistolADSAlpha<=SMALL_NUMBER)DualAimReferenceProfile.Profile=nullptr;
        Profile(AimProfile,Data->AimClip?Data->AimClip:Data->IdleClip,AimTime);
        Profile(ActionProfile,Data->ActionClip?Data->ActionClip:Data->IdleClip,Data->ActionTime);
        if(Data->ActionGripProfile)ActionProfile.Profile=Data->ActionGripProfile;
        Profile(SprintProfile,Data->SprintClip?Data->SprintClip:Data->IdleClip,Data->SprintTime);
        Profile(SprintLoopProfile,Data->SprintLoopClip?Data->SprintLoopClip:Data->IdleClip,Data->SprintLoopTime);
        SteelGauntletPose.Configure(*Data);
        Super90SupportArm.Configure(*GetSkelMeshComponent());
    }
};

FAnimInstanceProxy* UFPSGunplayAnimInstance::CreateAnimInstanceProxy() { return new FFPSGunplayAnimProxy(this); }
void UFPSGunplayAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
