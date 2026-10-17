#include "NightWardenAnimInstance.h"
#include "NightWardenMonster.h"
#include "NightWardenFootPlantNode.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "GameFramework/CharacterMovementComponent.h"

struct FNightWardenAnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle, Walk, Attack;
    FAnimNode_PoseSnapshot Entry;
    FAnimNode_TwoWayBlend Locomotion, WindupEntry, State;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FNightWardenFootPlantNode Feet;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    explicit FNightWardenAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Locomotion.A.SetLinkNode(&Idle); Locomotion.B.SetLinkNode(&Walk);
        Idle.SetShouldLoop(true); Walk.SetShouldLoop(true);
        Idle.SetTeleportToExplicitTime(true); Walk.SetTeleportToExplicitTime(true);
        Attack.SetShouldLoop(false); Attack.SetTeleportToExplicitTime(true);
        Entry.Mode = ESnapshotSourceMode::SnapshotPin;
        WindupEntry.A.SetLinkNode(&Entry); WindupEntry.B.SetLinkNode(&Attack);
        State.A.SetLinkNode(&Locomotion); State.B.SetLinkNode(&WindupEntry);
        ToComponent.LocalPose.SetLinkNode(&State); Feet.ComponentPose.SetLinkNode(&ToComponent); ToLocal.ComponentPose.SetLinkNode(&Feet);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &ToLocal; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override { Nodes.Append({&Idle, &Walk, &Attack, &Entry, &Locomotion, &WindupEntry, &State, &ToComponent, &Feet, &ToLocal}); }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UNightWardenAnimInstance>(Instance);
        Idle.SetSequence(Data->IdleClip); Idle.SetExplicitTime(Data->IdleTime);
        Walk.SetSequence(Data->WalkClip); Walk.SetExplicitTime(Data->WalkTime);
        Locomotion.Alpha = Data->WalkAlpha;
        Attack.SetSequence(Data->AttackClip); Attack.SetExplicitTime(Data->AttackTime);
        Entry.Snapshot = Data->EntryPose;
        WindupEntry.Alpha = Data->EntryPose.bIsValid ? Data->EntryAlpha : 1.f;
        State.Alpha = Data->AttackAlpha;
        Feet.Prepare(Cast<ANightWardenMonster>(Data->TryGetPawnOwner()), Data->WalkTime,
            Data->WalkAlpha*(1.f-Data->AttackAlpha), DeltaSeconds);
    }
};

void UNightWardenAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    const auto* Warden = Cast<ANightWardenMonster>(TryGetPawnOwner());
    if (!Warden) return;
    IdleClip = Warden->IdleClip; WalkClip = Warden->WalkClip;
    AttackClip = Warden->AttackClip;
    const bool Attacking = Warden->IsAttacking();
    if (Attacking && LastAttackSerial != Warden->CurrentAttackSerial())
    {
        SnapshotPose(EntryPose);
        LastAttackSerial = Warden->CurrentAttackSerial();
        EntryAlpha = FMath::Clamp(Warden->AttackPresentationTime() / .16f, 0.f, 1.f);
    }
    if (!Attacking && bWasAttacking) IdleTime = 0.f;
    bWasAttacking = Attacking;
    AttackTime = Warden->AttackPresentationTime();
    EntryAlpha = FMath::Min(1.f, EntryAlpha + DeltaSeconds / .16f);
    AttackAlpha = FMath::FInterpConstantTo(AttackAlpha, Attacking ? 1.f : 0.f, DeltaSeconds, 1.f / .16f);
    const float Speed = Warden->GetCharacterMovement()->IsMovingOnGround()
        ? Warden->GetVelocity().Size2D() : 0.f;
    const float Scale = FMath::Max(.01f, static_cast<float>(FMath::Abs(Warden->GetActorScale3D().X)));
    const float Rate = Speed / FMath::Max(1.f, Warden->SourceWalkSpeed * Scale);
    // Velocity, not the AI request, advances the cycle. A blocked or stopped
    // character has no minimum playback rate and keeps its stride phase.
    if (WalkClip && WalkClip->GetPlayLength() > 0.f)
        WalkTime = FMath::Fmod(WalkTime + DeltaSeconds * Rate, WalkClip->GetPlayLength());
    if (IdleClip && IdleClip->GetPlayLength() > 0.f)
        IdleTime = FMath::Fmod(IdleTime + DeltaSeconds, IdleClip->GetPlayLength());
    const float TargetAlpha = FMath::Clamp((Speed - 2.f) / 16.f, 0.f, 1.f);
    WalkAlpha = FMath::FInterpConstantTo(WalkAlpha, TargetAlpha, DeltaSeconds, 1.f / .18f);
}

FAnimInstanceProxy* UNightWardenAnimInstance::CreateAnimInstanceProxy() { return new FNightWardenAnimProxy(this); }
void UNightWardenAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
