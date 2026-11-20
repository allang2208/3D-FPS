#include "SmithHammerAnimInstance.h"

#include "ArtisanDefenseComponent.h"
#include "SmithHammerTiming.h"
#include "../Characters/FPSBodyStrideTiming.h"
#include "../Monsters/UnknownHumanoidTurnPose.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AnimInstanceProxy.h"
#include "AnimationRuntime.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Pawn.h"
#include "TwoBoneIK.h"

// Measured right palm in WPN_root space from the SourceGripV16 hammer rig.
const FTransform USmithHammerAnimInstance::HammerInRightHand = FTransform(
    FQuat(-.06894719, .01100870, .97410500, .21504544).GetNormalized(), FVector(-4.41886, 4.93759, 29.90152)).Inverse();

namespace SmithHammerAnimation
{
    using FBone = FCompactPoseBoneIndex;

    FBone FindBone(const FBoneContainer& Bones, FName Name)
    {
        const int32 Index = Bones.GetPoseBoneIndexForBoneName(Name);
        return Index != INDEX_NONE ? Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Index)) : FBone(INDEX_NONE);
    }

    FTransform ComponentTransform(const FCompactPose& Pose, FBone Bone)
    {
        FTransform Result = Pose[Bone];
        const FBoneContainer& Bones = Pose.GetBoneContainer();
        for (FBone Parent = Bones.GetParentBoneIndex(Bone); Parent != INDEX_NONE; Parent = Bones.GetParentBoneIndex(Parent))
            Result *= Pose[Parent];
        return Result;
    }

    void FitSupportPalm(FCompactPose& Pose, FBone Left, const FTransform& Target)
    {
        const FBoneContainer& Bones = Pose.GetBoneContainer();
        const FBone Elbow = Bones.GetParentBoneIndex(Left);
        if (Elbow == INDEX_NONE) return;
        const FBone Upper = Bones.GetParentBoneIndex(Elbow);
        if (Upper == INDEX_NONE) return;
        const FBone Clavicle = Bones.GetParentBoneIndex(Upper);
        if (Clavicle == INDEX_NONE) return;
        const FTransform Parent = ComponentTransform(Pose, Clavicle);
        FTransform Arm = Pose[Upper] * Parent;
        FTransform Forearm = Pose[Elbow] * Arm;
        FTransform Palm = Pose[Left] * Forearm;
        const FVector Pole = Forearm.GetLocation();
        AnimationCore::SolveTwoBoneIK(Arm, Forearm, Palm, Pole, Target.GetLocation(), false, 1., 1.);
        Palm.SetRotation(Target.GetRotation());
        Pose[Upper] = Arm.GetRelativeTransform(Parent);
        Pose[Elbow] = Forearm.GetRelativeTransform(Arm);
        Pose[Left] = Palm.GetRelativeTransform(Forearm);
    }

    struct FAimedSwing : FAnimNode_SequenceEvaluator_Standalone
    {
        FBone Spine{INDEX_NONE}, Right{INDEX_NONE}, Left{INDEX_NONE};
        float Pitch = 0.f;
        FVector PitchAxis = -FVector::ForwardVector;
        bool bClose = false;
        virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
        {
            FAnimNode_SequenceEvaluator_Standalone::CacheBones_AnyThread(Context);
            const FBoneContainer& Bones = Context.AnimInstanceProxy->GetRequiredBones();
            Spine = FindBone(Bones, TEXT("spine_01"));
            Right = FindBone(Bones, TEXT("hand_r"));
            Left = FindBone(Bones, TEXT("hand_l"));
        }
        void SmoothFrontalHead(FCompactPose& Pose, float Time) const
        {
            // The hand twists interpolate in opposing directions on frames 13–15.
            // At their half frames the equipped head departs the strike by 17–25 cm.
            const float Frame = Time * 60.f;
            if (bClose || Frame <= 13.f || Frame >= 15.f || Right == INDEX_NONE || Left == INDEX_NONE) return;
            const int32 Index = FMath::FloorToInt(Frame) - 10;
            const auto& Keys = SmithHammerTiming::FrontHeadKeys;
            const FVector Goal = FMath::Lerp(Keys[Index].Head, Keys[Index + 1].Head, FMath::Frac(Frame))
                .RotateAngleAxis(90.f, FVector::UpVector);
            const FTransform Palm = ComponentTransform(Pose, Right);
            const FTransform Hammer = USmithHammerAnimInstance::HammerInRightHand * Palm;
            const FVector Current = Hammer.TransformPosition(FVector(-.09, .10, 93.54));
            const FQuat Correction = FQuat::FindBetweenNormals((Current - Palm.GetLocation()).GetSafeNormal(),
                (Goal - Palm.GetLocation()).GetSafeNormal());
            const FBone Parent = Pose.GetBoneContainer().GetParentBoneIndex(Right);
            const FQuat ParentRotation = ComponentTransform(Pose, Parent).GetRotation();
            Pose[Right].SetRotation((ParentRotation.Inverse() * Correction * Palm.GetRotation()).GetNormalized());
            FTransform Support = ComponentTransform(Pose, Left);
            Support.SetLocation(Palm.GetLocation() + Correction.RotateVector(Support.GetLocation() - Palm.GetLocation()));
            Support.SetRotation((Correction * Support.GetRotation()).GetNormalized());
            FitSupportPalm(Pose, Left, Support);
        }
        virtual void Evaluate_AnyThread(FPoseContext& Output) override
        {
            FAnimNode_SequenceEvaluator_Standalone::Evaluate_AnyThread(Output);
            SmoothFrontalHead(Output.Pose, GetExplicitTime());
            if (Spine == INDEX_NONE || FMath::IsNearlyZero(Pitch)) return;
            const FBone Parent = Output.Pose.GetBoneContainer().GetParentBoneIndex(Spine);
            const FQuat ParentRotation = ComponentTransform(Output.Pose, Parent).GetRotation();
            // The body's -90 degree mesh yaw maps -X to the guard's right axis.
            const FQuat Tilt(PitchAxis, FMath::DegreesToRadians(Pitch));
            auto& Local = Output.Pose[Spine];
            Local.SetRotation((ParentRotation.Inverse() * Tilt * ParentRotation * Local.GetRotation()).GetNormalized());
        }
    };

    // Each donor already has fitted fingers and a sliding/rolling support palm. During a
    // crossfade the arm chains alone would move that palm off the interpolated hammer.
    struct FHeldBlend : FAnimNode_TwoWayBlend
    {
        FBone Right{INDEX_NONE}, Left{INDEX_NONE};

        virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
        {
            FAnimNode_TwoWayBlend::CacheBones_AnyThread(Context);
            const FBoneContainer& Bones = Context.AnimInstanceProxy->GetRequiredBones();
            Right = FindBone(Bones, TEXT("hand_r"));
            Left = FindBone(Bones, TEXT("hand_l"));
        }

        FTransform HammerFrame(const FCompactPose& Pose) const
        {
            return USmithHammerAnimInstance::HammerInRightHand * ComponentTransform(Pose, Right);
        }

        FTransform SupportGrip(const FCompactPose& Pose) const
        {
            return ComponentTransform(Pose, Left).GetRelativeTransform(HammerFrame(Pose));
        }

        virtual void Evaluate_AnyThread(FPoseContext& Output) override
        {
            const float Weight = InternalBlendAlpha;
            if (Right == INDEX_NONE || Left == INDEX_NONE || !FAnimWeight::IsRelevant(Weight) || FAnimWeight::IsFullWeight(Weight))
            {
                FAnimNode_TwoWayBlend::Evaluate_AnyThread(Output);
                return;
            }
            A.Evaluate(Output);
            FPoseContext Other(Output);
            B.Evaluate(Other);
            const FTransform From = SupportGrip(Output.Pose), To = SupportGrip(Other.Pose);
            FTransform Grip;
            Grip.Blend(From, To, Weight);
            // Travel around the cylindrical haft, retaining the donor radius and axial slide.
            const FVector P = From.GetLocation(), Q = To.GetLocation();
            const double Start = FMath::Atan2(P.Y, P.X);
            const double Angle = Start + Weight * FMath::FindDeltaAngleRadians(Start, FMath::Atan2(Q.Y, Q.X));
            const double Radius = FMath::Lerp(P.Size2D(), Q.Size2D(), double(Weight));
            Grip.SetLocation(FVector(Radius * FMath::Cos(Angle), Radius * FMath::Sin(Angle), Grip.GetTranslation().Z));

            FAnimationPoseData Blended(Output);
            const FAnimationPoseData Destination(Other);
            FAnimationRuntime::BlendTwoPosesTogetherInPlace(Blended, Destination, 1.f - Weight);
            const FTransform Target = Grip * HammerFrame(Output.Pose);
            FitSupportPalm(Output.Pose, Left, Target);
        }
    };
}

struct FSmithHammerAnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Ready, Walk;
    SmithHammerAnimation::FAimedSwing Swing;
    SmithHammerAnimation::FHeldBlend Locomotion, Action;
    FUnknownTurnPose TurnFeet;
    TWeakObjectPtr<UArtisanDefenseComponent> Defense;
    TOptional<FPSBodyAnimation::FStrideTiming> Stride;
    float WalkCycles = 0.f, LastSwingStart = 0.f;

    explicit FSmithHammerAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Locomotion.A.SetLinkNode(&Ready);
        Locomotion.B.SetLinkNode(&Walk);
        Action.A.SetLinkNode(&Locomotion);
        Action.B.SetLinkNode(&Swing);
        TurnFeet.Source.SetLinkNode(&Action);
        Locomotion.Alpha = Action.Alpha = 0.f;
        Ready.SetShouldLoop(true);
        Walk.SetShouldLoop(true);
        Swing.SetShouldLoop(false);
        Ready.SetTeleportToExplicitTime(true);
        Walk.SetTeleportToExplicitTime(true);
        Swing.SetTeleportToExplicitTime(true);
    }

    virtual FAnimNode_Base* GetCustomRootNode() override { return &TurnFeet; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Ready, &Walk, &Swing, &Locomotion, &Action, &TurnFeet});
    }

    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        APawn* Pawn = Instance->TryGetPawnOwner();
        if (!Pawn) return;
        if (!Defense.IsValid()) Defense = Pawn->FindComponentByClass<UArtisanDefenseComponent>();
        const auto* Guard = Defense.Get();
        if (!Guard) return;

        // Replication, movement and streaming are sampled on the game thread. The graph
        // evaluates only sequences and times prepared here, even when it runs in parallel.
        const bool bFirstPose = !Stride.IsSet();
        if (bFirstPose)
        {
            UAnimSequence* Gait = Guard->Clips.FindRef(EArtisanGuardState::Approach);
            UAnimSequence* Idle = Guard->Clips.FindRef(EArtisanGuardState::Ready);
            UAnimSequence* Attack = Guard->Clips.FindRef(EArtisanGuardState::Attack);
            if (!Gait || !Idle || !Attack) return;
            Ready.SetSequence(Idle);
            Walk.SetSequence(Gait);
            Swing.SetSequence(Attack);
            Stride.Emplace(Gait);
        }
        const float Dt = FMath::Max(DeltaSeconds, 0.f);
        const UWorld* World = Pawn->GetWorld();
        const AGameStateBase* GS = World->GetGameState();
        const double Now = GS ? GS->GetServerWorldTimeSeconds() : World->GetTimeSeconds();
        const float IdleDuration = FMath::Max(Ready.GetSequence()->GetPlayLength(), UE_SMALL_NUMBER);
        Ready.SetExplicitTime(float(FMath::Fmod(Now, double(IdleDuration))));

        const float BodyScale = FMath::Max(.01f, float(FMath::Abs(Pawn->GetActorScale3D().X)));
        const float Speed = float(Pawn->GetVelocity().Size2D()) / BodyScale;
        const bool bAttack = Guard->State == EArtisanGuardState::Attack;
        if (const auto* Mesh = Instance->GetSkelMeshComponent())
            TurnFeet.Prepare(*Mesh, Speed, true, !bAttack, Dt);
        // This in-place take has three footfall pairs and a measured 441 cm/s planted toe speed.
        const float SourceSpeed = Stride->Speed(441.f);
        // At low speed shorten the visible step before slowing its cadence. Distance still
        // advances the feet, including while braking on the return to the work station.
        const float DesiredStride = FMath::Clamp(Speed / (.68f * SourceSpeed), 0.f, 1.f);
        Locomotion.Alpha = bFirstPose ? DesiredStride : FMath::FInterpConstantTo(Locomotion.Alpha, DesiredStride, Dt, 1.f / .13f);
        const float DistancePerPair = SourceSpeed * Stride->Duration() * FMath::Max(.12f, Locomotion.Alpha);
        const float PairCount = float(FMath::Max(Stride->Left.Num(), 1));
        WalkCycles = FMath::Fmod(WalkCycles + Speed * Dt / FMath::Max(1.f, DistancePerPair), PairCount);
        Walk.SetExplicitTime(Stride->Sample(WalkCycles));

        if (!GS && !Pawn->HasAuthority()) return;
        if (bAttack)
        {
            LastSwingStart = Guard->StateStartedAt;
            UAnimSequence* Clip = Guard->bCloseHammer ? Guard->HammerCloseClip.Get() : Guard->Clips.FindRef(EArtisanGuardState::Attack).Get();
            if (Swing.GetSequence() != Clip) Swing.SetSequence(Clip);
            Swing.Pitch = Guard->HammerPitch;
            Swing.bClose = Guard->bCloseHammer;
            Swing.PitchAxis = SmithHammerTiming::AimAxis(Guard->bCloseHammer).RotateAngleAxis(90.f, FVector::UpVector);
        }
        if (bAttack || Action.Alpha > 0.f)
        {
            const float Age = FMath::Max(0.f, float(Now - LastSwingStart));
            Swing.SetExplicitTime(SmithHammerTiming::SampleClip(Age, Guard->HammerClipContact, Swing.GetSequence()->GetPlayLength()));
            if (bAttack)
            {
                const float Entry = FMath::SmoothStep(0.f, .10f, Age);
                const float Recovery = FMath::SmoothStep(0.f, .12f, SmithHammerTiming::End - Age);
                Action.Alpha = Entry * Recovery;
            }
            else Action.Alpha = FMath::FInterpConstantTo(Action.Alpha, 0.f, Dt, 1.f / .10f);
        }
    }
};

FAnimInstanceProxy* USmithHammerAnimInstance::CreateAnimInstanceProxy() { return new FSmithHammerAnimProxy(this); }
void USmithHammerAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
