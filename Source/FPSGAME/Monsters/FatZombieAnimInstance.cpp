#include "FatZombieAnimInstance.h"
#include "NurseZombie.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "BoneControllers/AnimNode_ModifyBone.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Components/SkeletalMeshComponent.h"

/** Landing support must not inherit a floating air pose during its crossfade. */
struct FMonsterGroundedTransition : FAnimNode_TwoWayBlend
{
    FBoneReference UpperBodyRoot;
    bool bGroundLowerBody = false;

    FMonsterGroundedTransition()
    {
        UpperBodyRoot.BoneName = TEXT("Spine02");
        // The destination legs are required even on the first frame (alpha 0).
        bAlwaysUpdateChildren = true;
    }

    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
    {
        FAnimNode_TwoWayBlend::CacheBones_AnyThread(Context);
        UpperBodyRoot.Initialize(Context.AnimInstanceProxy->GetRequiredBones());
    }

    virtual void Evaluate_AnyThread(FPoseContext& Output) override
    {
        const auto& Bones = Output.Pose.GetBoneContainer();
        if (!bGroundLowerBody || !UpperBodyRoot.IsValidToEvaluate(Bones))
        {
            FAnimNode_TwoWayBlend::Evaluate_AnyThread(Output);
            return;
        }
        B.Evaluate(Output);
        if (FAnimWeight::IsFullWeight(InternalBlendAlpha)) return;
        FPoseContext Source(Output);
        A.Evaluate(Source);
        const FCompactPoseBoneIndex Spine = UpperBodyRoot.GetCompactPoseIndex(Bones);
        for (const FCompactPoseBoneIndex Bone : Output.Pose.ForEachBoneIndex())
        {
            FCompactPoseBoneIndex Parent = Bone;
            while (Parent != INDEX_NONE && Parent != Spine) Parent = Bones.GetParentBoneIndex(Parent);
            if (Parent == Spine)
            {
                const FTransform Destination = Output.Pose[Bone];
                Output.Pose[Bone].Blend(Source.Pose[Bone], Destination, InternalBlendAlpha);
            }
        }
        // Curves/attributes remain those of the landing clip; these in-place
        // sequences have no gameplay notifies or root-motion authority.
    }
};

struct FFatZombieAnimProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_SequenceEvaluator_Standalone Outgoing;
    FAnimNode_TwoWayBlend Source;
    FAnimNode_SequenceEvaluator_Standalone Current;
    FMonsterGroundedTransition Transition;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FAnimNode_ModifyBone LowerRecoil;
    FAnimNode_ModifyBone UpperRecoil;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;

    explicit FFatZombieAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Previous.Mode = ESnapshotSourceMode::SnapshotPin;
        Source.A.SetLinkNode(&Previous);
        Source.B.SetLinkNode(&Outgoing);
        Transition.A.SetLinkNode(&Source);
        Transition.B.SetLinkNode(&Current);
        ToComponent.LocalPose.SetLinkNode(&Transition);
        LowerRecoil.ComponentPose.SetLinkNode(&ToComponent);
        UpperRecoil.ComponentPose.SetLinkNode(&LowerRecoil);
        ToLocal.ComponentPose.SetLinkNode(&UpperRecoil);
        LowerRecoil.BoneToModify.BoneName = TEXT("Spine02");
        UpperRecoil.BoneToModify.BoneName = TEXT("Spine");
        for (auto* Node : {&LowerRecoil, &UpperRecoil})
        {
            Node->RotationMode = BMM_Additive;
            Node->RotationSpace = BCS_ComponentSpace;
            Node->Alpha = 1.f;
        }
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &ToLocal; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Previous, &Outgoing, &Source, &Current, &Transition, &ToComponent, &LowerRecoil, &UpperRecoil, &ToLocal});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UFatZombieAnimInstance>(Instance);
        Previous.Snapshot = Data->PreviousPose;
        Outgoing.SetSequence(Data->OutgoingLoop);
        Outgoing.SetShouldLoop(true);
        Outgoing.SetTeleportToExplicitTime(true);
        Outgoing.SetExplicitTime(Data->OutgoingLoopTime);
        Source.Alpha = Data->OutgoingLoop ? 1.f : 0.f;
        Current.SetSequence(Data->ActiveClip);
        Current.SetShouldLoop(Data->bLooping);
        // Explicit sampling produces poses, never a second damage/root-motion clock.
        Current.SetTeleportToExplicitTime(true);
        Current.SetExplicitTime(Data->ClipTime);
        Transition.Alpha = Data->PreviousPose.bIsValid ? Data->BlendAlpha : 1.f;
        Transition.bGroundLowerBody = Data->bGroundLowerBody;
        const float Angle = Data->HitRotationVector.Size();
        const FVector Axis = Angle > SMALL_NUMBER ? Data->HitRotationVector / Angle : FVector::RightVector;
        LowerRecoil.Rotation = FQuat(Axis, Angle * .65f).Rotator();
        UpperRecoil.Rotation = FQuat(Axis, Angle * .35f).Rotator();
    }
};

void UFatZombieAnimInstance::TransitionTo(UAnimSequence* Clip, bool bLoop, bool bCombatClock, float BlendSeconds,
    const FMonsterClipTransition& Settings)
{
    if (!Clip) return;
    // A fully established locomotion source can keep stepping during the fade.
    // Interrupted blends/reactions must instead start at the visible snapshot.
    OutgoingLoop = Settings.bContinueOutgoingLoop && ActiveClip && bLooping &&
        BlendAlpha >= 1.f-KINDA_SMALL_NUMBER && !bPlayingHitClip && HitRotationVector.IsNearlyZero() ? ActiveClip : nullptr;
    OutgoingLoopTime = ClipTime;
    OutgoingLoopRate = PlayRate;
    bGroundLowerBody = Settings.bGroundLowerBody;
    bPlayingHitClip = false;
    bRewindingParry = false;
    PendingHitClip = nullptr;
    HitClipTimeOffset = 0.f;
    if (ActiveClip && bLooping) LoopTimes.Add(TWeakObjectPtr<UAnimSequence>(ActiveClip), ClipTime);
    // Capture the actual last blended pose, so an interrupted transition does
    // not jump back to the start/end frame of its previous source animation.
    PreviousPose.Reset();
    if (ActiveClip && GetSkelMeshComponent()) GetSkelMeshComponent()->SnapshotPose(PreviousPose);
    // The snapshot already includes recoil; do not add it again during recovery/death.
    HitRotationVector = HitStartRotation = HitPeakRotation = FVector::ZeroVector;
    ActiveClip = Clip;
    bLooping = bLoop;
    bUseCombatClock = bCombatClock;
    ClipTime = bLoop ? LoopTimes.FindRef(TWeakObjectPtr<UAnimSequence>(Clip)) : 0.f;
    if (Settings.StartTime >= 0.f) ClipTime = FMath::Clamp(Settings.StartTime, 0.f, Clip->GetPlayLength());
    PlayRate = TargetPlayRate = FMath::Max(0.f, Settings.InitialPlayRate);
    BlendDuration = FMath::Max(0.f, BlendSeconds);
    BlendElapsed = 0.f;
    BlendAlpha = PreviousPose.bIsValid && BlendDuration > SMALL_NUMBER ? 0.f : 1.f;
}

void UFatZombieAnimInstance::SetCombatTime(float Seconds)
{
    if (ActiveClip && bUseCombatClock && !bPlayingHitClip) ClipTime = FMath::Clamp(Seconds, 0.f, ActiveClip->GetPlayLength());
}

void UFatZombieAnimInstance::FinishClip()
{
    if (!ActiveClip || bLooping) return;
    HoldClipAtTime(ActiveClip->GetPlayLength());
}

void UFatZombieAnimInstance::HoldClipAtTime(float Seconds)
{
    if (!ActiveClip || bLooping) return;
    ClipTime = FMath::Clamp(Seconds, 0.f, ActiveClip->GetPlayLength());
    bUseCombatClock = true;
    BlendElapsed = BlendDuration;
    BlendAlpha = 1.f;
}

void UFatZombieAnimInstance::BeginHitReaction(UAnimSequence* ReactionClip, const FVector& WorldDirection, bool bParried, float BlendSeconds)
{
    const auto* Zombie = Cast<ANurseZombie>(TryGetPawnOwner());
    if (ReactionClip && bParried && Zombie && ActiveClip == Zombie->AttackClip && !bPlayingHitClip)
    {
        // Keep the actual attack and its interruption position. Rewind only its
        // pose; the attack's damage window has already been consumed/cancelled.
        PendingHitClip = ReactionClip;
        ParryRewindStartTime = ClipTime;
        HitClipTimeOffset = .3f;
        bRewindingParry = true;
        bPlayingHitClip = true;
        bUseCombatClock = true;
        OutgoingLoop = nullptr;
        HitRotationVector = HitStartRotation = HitPeakRotation = FVector::ZeroVector;
        return;
    }
    if (ReactionClip)
    {
        // Replace the attack evaluator immediately. Keeping the attack as the
        // base pose with a small spine offset did not present a stagger action.
        TransitionTo(ReactionClip, false, true, BlendSeconds);
        bPlayingHitClip = true;
        HitClipTimeOffset = bParried ? -.1f : 0.f;
        return;
    }
    const auto* Mesh = GetSkelMeshComponent();
    if (!Mesh) return;
    FVector Away = WorldDirection.GetSafeNormal2D();
    if (Away.IsNearlyZero()) Away = -Mesh->GetOwner()->GetActorForwardVector();
    const FVector WorldAxis = FVector::CrossProduct(FVector::UpVector, Away).GetSafeNormal();
    const FVector MeshAxis = Mesh->GetComponentTransform().InverseTransformVectorNoScale(WorldAxis).GetSafeNormal();
    HitStartRotation = HitRotationVector;
    HitPeakRotation = MeshAxis * FMath::DegreesToRadians(18.f);
}

void UFatZombieAnimInstance::SetHitReactionTime(float Elapsed, float Remaining)
{
    if (bRewindingParry)
    {
        constexpr float RewindSeconds = .3f;
        ClipTime = FMath::Max(0.f, ParryRewindStartTime - FMath::Clamp(Elapsed, 0.f, RewindSeconds));
        if (Elapsed < RewindSeconds) return;
        UAnimSequence* ReactionClip = PendingHitClip;
        // Capture the last visible reverse pose for a short, continuous handoff.
        TransitionTo(ReactionClip, false, true, .08f);
        bPlayingHitClip = true;
        HitClipTimeOffset = RewindSeconds;
    }
    if (bPlayingHitClip && ActiveClip)
    {
        const float HitElapsed = FMath::Max(0.f, Elapsed - HitClipTimeOffset);
        if (BlendDuration > SMALL_NUMBER)
        {
            // Controlled animations return early from NativeUpdateAnimation,
            // so their transition must use this same reaction clock as well.
            BlendElapsed = HitElapsed;
            const float T = FMath::Clamp(HitElapsed / BlendDuration, 0.f, 1.f);
            BlendAlpha = T * T * (3.f - 2.f * T);
        }
        // The authored clip recoils in .1 s, holds through .6 s and recovers
        // over .3 s. A long control extends the hold, never the attack.
        const float Time = HitElapsed < .1f ? HitElapsed : (Remaining > .3f ? .1f : .6f + .3f - FMath::Max(0.f, Remaining));
        ClipTime = FMath::Clamp(Time, 0.f, ActiveClip->GetPlayLength());
        return;
    }
    // Reuse the shared reaction clock: quick recoil, hold during stun, ease out.
    // Repeated hits start from the visible offset and never accumulate displacement.
    if (Elapsed < .1f)
    {
        const float T = FMath::Clamp(Elapsed / .1f, 0.f, 1.f);
        HitRotationVector = FMath::Lerp(HitStartRotation, HitPeakRotation, T * T * (3.f - 2.f * T));
    }
    else HitRotationVector = HitPeakRotation * FMath::Pow(FMath::Clamp(Remaining / .45f, 0.f, 1.f), 1.5f);
}

void UFatZombieAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if (!ActiveClip) return;
    // The shared reaction clock owns the dedicated hit clip while controlled.
    if (const auto* Zombie = Cast<ANurseZombie>(TryGetPawnOwner()); Zombie && Zombie->State == ENurseState::Stagger) return;
    const float Dt = FMath::Max(0.f, DeltaSeconds);
    if (!bUseCombatClock)
    {
        PlayRate = FMath::FInterpTo(PlayRate, TargetPlayRate, Dt, 8.f);
        const float Length = ActiveClip->GetPlayLength();
        ClipTime += Dt * PlayRate;
        ClipTime = bLooping && Length > SMALL_NUMBER ? FMath::Fmod(ClipTime, Length) : FMath::Min(ClipTime, Length);
    }
    BlendElapsed += Dt;
    const float T = BlendDuration > SMALL_NUMBER ? FMath::Clamp(BlendElapsed / BlendDuration, 0.f, 1.f) : 1.f;
    BlendAlpha = T * T * (3.f - 2.f * T);
    if (OutgoingLoop)
    {
        const float Length = OutgoingLoop->GetPlayLength();
        OutgoingLoopTime = Length > SMALL_NUMBER ? FMath::Fmod(OutgoingLoopTime + Dt*OutgoingLoopRate, Length) : 0.f;
        if (BlendAlpha >= 1.f) OutgoingLoop = nullptr;
    }
}

FAnimInstanceProxy* UFatZombieAnimInstance::CreateAnimInstanceProxy() { return new FFatZombieAnimProxy(this); }
void UFatZombieAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
