#include "FatZombieAnimInstance.h"
#include "FatZombie.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "BoneControllers/AnimNode_ModifyBone.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Components/SkeletalMeshComponent.h"

struct FFatZombieAnimProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_SequenceEvaluator_Standalone Current;
    FAnimNode_TwoWayBlend Transition;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FAnimNode_ModifyBone LowerRecoil;
    FAnimNode_ModifyBone UpperRecoil;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;

    explicit FFatZombieAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Previous.Mode = ESnapshotSourceMode::SnapshotPin;
        Transition.A.SetLinkNode(&Previous);
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
        Nodes.Append({&Previous, &Current, &Transition, &ToComponent, &LowerRecoil, &UpperRecoil, &ToLocal});
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UFatZombieAnimInstance>(Instance);
        Previous.Snapshot = Data->PreviousPose;
        Current.SetSequence(Data->ActiveClip);
        Current.SetShouldLoop(Data->bLooping);
        // Explicit sampling produces poses, never a second damage/root-motion clock.
        Current.SetTeleportToExplicitTime(true);
        Current.SetExplicitTime(Data->ClipTime);
        Transition.Alpha = Data->PreviousPose.bIsValid ? Data->BlendAlpha : 1.f;
        const float Angle = Data->HitRotationVector.Size();
        const FVector Axis = Angle > SMALL_NUMBER ? Data->HitRotationVector / Angle : FVector::RightVector;
        LowerRecoil.Rotation = FQuat(Axis, Angle * .65f).Rotator();
        UpperRecoil.Rotation = FQuat(Axis, Angle * .35f).Rotator();
    }
};

void UFatZombieAnimInstance::TransitionTo(UAnimSequence* Clip, bool bLoop, bool bCombatClock, float BlendSeconds)
{
    if (!Clip) return;
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
    PlayRate = TargetPlayRate = 1.f;
    BlendDuration = FMath::Max(0.f, BlendSeconds);
    BlendElapsed = 0.f;
    BlendAlpha = PreviousPose.bIsValid && BlendDuration > SMALL_NUMBER ? 0.f : 1.f;
}

void UFatZombieAnimInstance::SetCombatTime(float Seconds)
{
    if (ActiveClip && bUseCombatClock) ClipTime = FMath::Clamp(Seconds, 0.f, ActiveClip->GetPlayLength());
}

void UFatZombieAnimInstance::FinishClip()
{
    if (!ActiveClip || bLooping) return;
    ClipTime = ActiveClip->GetPlayLength();
    bUseCombatClock = true;
    BlendElapsed = BlendDuration;
    BlendAlpha = 1.f;
}

void UFatZombieAnimInstance::BeginHitReaction(const FVector& WorldDirection)
{
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
    // Freeze the interrupted clip while the shared reaction clock drives the
    // additive upper-body recoil. Do not continue an interrupted attack.
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
}

FAnimInstanceProxy* UFatZombieAnimInstance::CreateAnimInstanceProxy() { return new FFatZombieAnimProxy(this); }
void UFatZombieAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
