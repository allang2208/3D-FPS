#include "M25AnimInstance.h"
#include "VortexCofferM25.h"
#include "M25BiteComponent.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "GameFramework/CharacterMovementComponent.h"

struct FM25AnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle, Crawl, Bite, Hit, Death;
    FAnimNode_TwoWayBlend Locomotion, AttackPose, HitPose, FinalPose;

    explicit FM25AnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Locomotion.A.SetLinkNode(&Idle);
        Locomotion.B.SetLinkNode(&Crawl);
        AttackPose.A.SetLinkNode(&Locomotion);
        AttackPose.B.SetLinkNode(&Bite);
        HitPose.A.SetLinkNode(&AttackPose);
        HitPose.B.SetLinkNode(&Hit);
        FinalPose.A.SetLinkNode(&HitPose);
        FinalPose.B.SetLinkNode(&Death);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &FinalPose; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({ &Idle, &Crawl, &Bite, &Hit, &Death, &Locomotion, &AttackPose, &HitPose, &FinalPose });
    }
    static void Sample(FAnimNode_SequenceEvaluator_Standalone& Node, UAnimSequence* Clip, float Time, bool bLoop = true)
    {
        Node.SetSequence(Clip);
        Node.SetShouldLoop(bLoop);
        Node.SetTeleportToExplicitTime(true);
        Node.SetExplicitTime(Time);
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Anim = CastChecked<UM25AnimInstance>(Instance);
        const auto* Monster = Cast<AVortexCofferM25>(Anim->TryGetPawnOwner());
        if (!Monster) return;
        Sample(Idle, Monster->IdleClip, Anim->IdleTime);
        Sample(Crawl, Monster->MoveClip, Anim->CrawlTime);
        Locomotion.Alpha = Monster->MoveClip ? Anim->LocomotionWeight : 0.f;
        Sample(Bite, Monster->BiteClip ? Monster->BiteClip.Get() : Monster->IdleClip.Get(), Anim->BiteTime, false);
        AttackPose.Alpha = Monster->BiteClip ? Anim->BiteWeight : 0.f;
        Sample(Hit, Monster->HitClip ? Monster->HitClip.Get() : Monster->IdleClip.Get(), Anim->HitTime, false);
        HitPose.Alpha = Monster->HitClip ? Anim->HitWeight : 0.f;
        Sample(Death, Monster->DeathClip ? Monster->DeathClip.Get() : Monster->IdleClip.Get(), Anim->DeathTime, false);
        FinalPose.Alpha = Monster->DeathClip ? Anim->DeathWeight : 0.f;
    }
};

UM25AnimInstance::UM25AnimInstance()
{
    RootMotionMode = ERootMotionMode::IgnoreRootMotion;
}

void UM25AnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();
    IdleTime = CrawlTime = LocomotionWeight = 0.f;
    bCrawling = false;
    BiteTime = BiteWeight = 0.f;
    HitTime = HitWeight = DeathTime = DeathWeight = 0.f;
}

void UM25AnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    const auto* Monster = Cast<AVortexCofferM25>(TryGetPawnOwner());
    if (!Monster) return;
    if (Monster->Dead())
    {
        DeathTime = Monster->DeathClip ? FMath::Min(Monster->DeathAnimationTime(), Monster->DeathClip->GetPlayLength()) : 0.f;
        DeathWeight = FMath::Clamp(Monster->DeathAnimationTime() / .16f, 0.f, 1.f);
        return;
    }
    if (Monster->Controlled()) HitTime = Monster->HitAnimationTime();
    HitWeight = FMath::FInterpConstantTo(HitWeight, Monster->Controlled() ? 1.f : 0.f,
        DeltaSeconds, Monster->Controlled() ? 1.f / .06f : 1.f / .14f);
    if (!Monster->Controlled() && Monster->Bite && Monster->Bite->IsBusy())
    {
        BiteTime = Monster->Bite->AnimationTime();
        BiteWeight = Monster->Bite->AnimationWeight();
    }
    else BiteWeight = FMath::FInterpConstantTo(BiteWeight, 0.f, DeltaSeconds, 1.f / .14f);
    const float Speed = Monster->GetVelocity().Size2D();
    const bool Grounded = Monster->GetCharacterMovement()->IsMovingOnGround();
    bCrawling = Grounded && Speed > (bCrawling ? .3f : 1.f);
    LocomotionWeight = FMath::FInterpConstantTo(LocomotionWeight, bCrawling ? 1.f : 0.f, DeltaSeconds, 4.f);
    if (Monster->IdleClip)
        IdleTime = FMath::Fmod(IdleTime + DeltaSeconds, FMath::Max(.01f, Monster->IdleClip->GetPlayLength()));
    // Retain phase when stopped; advancing it from velocity keeps the in-place
    // tendril cycle matched to CharacterMovement instead of applying root motion twice.
    if (Grounded && Monster->MoveClip)
    {
        const float Rate = Speed / FMath::Max(1.f, Monster->AnimationWalkSpeed);
        CrawlTime = FMath::Fmod(CrawlTime + DeltaSeconds * Rate, FMath::Max(.01f, Monster->MoveClip->GetPlayLength()));
    }
}

FAnimInstanceProxy* UM25AnimInstance::CreateAnimInstanceProxy() { return new FM25AnimProxy(this); }
void UM25AnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
