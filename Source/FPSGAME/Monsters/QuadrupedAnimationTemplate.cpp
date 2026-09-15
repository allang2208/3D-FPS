#include "QuadrupedAnimationTemplate.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

UAnimSequence* UQuadrupedAnimationSet::FindSequence(FName Name) const
{
    const FQuadrupedTemplateAction* Entry = FindAction(Name);
    return Entry ? Entry->Sequence.Get() : nullptr;
}

struct FQuadrupedTemplateProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle, Walk, Run, Action;
    FAnimNode_SequenceEvaluator_Standalone WalkLeft, WalkRight, RunLeft, RunRight;
    FAnimNode_TwoWayBlend WalkSide, WalkHeading, RunSide, RunHeading;
    FAnimNode_TwoWayBlend Gaits, Locomotion, Selection, Transition;
    FAnimNode_PoseSnapshot Previous;

    explicit FQuadrupedTemplateProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Previous.Mode = ESnapshotSourceMode::SnapshotPin;
        WalkSide.A.SetLinkNode(&WalkLeft); WalkSide.B.SetLinkNode(&WalkRight);
        RunSide.A.SetLinkNode(&RunLeft); RunSide.B.SetLinkNode(&RunRight);
        WalkHeading.A.SetLinkNode(&Walk); WalkHeading.B.SetLinkNode(&WalkSide);
        RunHeading.A.SetLinkNode(&Run); RunHeading.B.SetLinkNode(&RunSide);
        Gaits.A.SetLinkNode(&WalkHeading); Gaits.B.SetLinkNode(&RunHeading);
        Locomotion.A.SetLinkNode(&Idle); Locomotion.B.SetLinkNode(&Gaits);
        Selection.A.SetLinkNode(&Locomotion); Selection.B.SetLinkNode(&Action);
        Transition.A.SetLinkNode(&Previous); Transition.B.SetLinkNode(&Selection);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &Transition; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Idle, &Walk, &Run, &Action, &WalkLeft, &WalkRight, &RunLeft, &RunRight,
            &WalkSide, &WalkHeading, &RunSide, &RunHeading, &Gaits, &Locomotion, &Selection, &Previous, &Transition});
    }
    static void SetPose(FAnimNode_SequenceEvaluator_Standalone& Node, UAnimSequence* Clip, float Seconds, bool bLoop)
    {
        Node.SetSequence(Clip);
        Node.SetShouldLoop(bLoop);
        // Do not extract root motion or dispatch the source package's notifies.
        Node.SetTeleportToExplicitTime(true);
        Node.SetExplicitTime(Seconds);
    }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const auto* Data = CastChecked<UQuadrupedTemplateAnimInstance>(Instance);
        const auto* Set = Data->AnimationSet.Get();
        UAnimSequence* IdleClip = Set ? Set->FindSequence(TEXT("Idle")) : nullptr;
        UAnimSequence* WalkClip = Set ? Set->FindSequence(TEXT("Walk")) : nullptr;
        UAnimSequence* RunClip = Set ? Set->FindSequence(TEXT("Run")) : nullptr;
        SetPose(Idle, IdleClip, Data->IdleTime, true);
        SetPose(Walk, WalkClip, WalkClip ? FMath::Fmod(Data->GaitPhase + Set->WalkPhaseOffset, 1.f) * WalkClip->GetPlayLength() : 0.f, true);
        SetPose(Run, RunClip, RunClip ? FMath::Fmod(Data->GaitPhase + Set->RunPhaseOffset, 1.f) * RunClip->GetPlayLength() : 0.f, true);
        auto SetTurnPose = [&](FAnimNode_SequenceEvaluator_Standalone& Node, FName Name, UAnimSequence* Straight, float Offset)
        {
            UAnimSequence* Clip = Set ? Set->FindSequence(Name) : nullptr;
            if (!Clip || !Straight || Clip->GetSkeleton() != Straight->GetSkeleton()) Clip = Straight;
            SetPose(Node, Clip, Clip ? FMath::Fmod(Data->GaitPhase + Offset, 1.f) * Clip->GetPlayLength() : 0.f, true);
        };
        SetTurnPose(WalkLeft, TEXT("WalkTurnLeft"), WalkClip, Set ? Set->WalkPhaseOffset : 0.f);
        SetTurnPose(WalkRight, TEXT("WalkTurnRight"), WalkClip, Set ? Set->WalkPhaseOffset : 0.f);
        SetTurnPose(RunLeft, TEXT("RunTurnLeft"), RunClip, Set ? Set->RunPhaseOffset : 0.f);
        SetTurnPose(RunRight, TEXT("RunTurnRight"), RunClip, Set ? Set->RunPhaseOffset : 0.f);
        // Positive UE yaw turns right. All directional variants share the same
        // cycle phase, so steering changes body shape without restarting feet.
        WalkSide.Alpha = RunSide.Alpha = Data->TurnAlpha >= 0.f ? 1.f : 0.f;
        WalkHeading.Alpha = RunHeading.Alpha = FMath::Abs(Data->TurnAlpha);
        SetPose(Action, Data->ActiveDefinition.Sequence, Data->ActionTime, Data->ActiveDefinition.bLoop);
        Gaits.Alpha = Data->WalkRunAlpha;
        Locomotion.Alpha = Data->MoveAlpha;
        Selection.Alpha = Data->ActiveAction.IsNone() ? 0.f : 1.f;
        Previous.Snapshot = Data->PreviousPose;
        Transition.Alpha = Data->PreviousPose.bIsValid ? Data->TransitionAlpha : 1.f;
    }
};

void UQuadrupedTemplateAnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();
    ActiveAction = NAME_None;
    ActiveDefinition = FQuadrupedTemplateAction();
    PreviousPose.Reset();
    IdleTime = GaitPhase = ActionTime = 0.f;
    TransitionAlpha = 1.f;
    bTerminalPose = bUseExternalClock = false;
    TurnAlpha = 0.f; bHasOwnerYaw = false;
}

bool UQuadrupedTemplateAnimInstance::SetAnimationSet(UQuadrupedAnimationSet* NewSet)
{
    if (!NewSet || !NewSet->ReferenceMesh || !GetSkelMeshComponent()) return false;
    USkeletalMesh* CurrentMesh = GetSkelMeshComponent()->GetSkeletalMeshAsset();
    if (!CurrentMesh || CurrentMesh->GetSkeleton() != NewSet->ReferenceMesh->GetSkeleton()) return false;
    for (const FName Name : {FName(TEXT("Idle")), FName(TEXT("Walk")), FName(TEXT("Run"))})
    {
        UAnimSequence* Clip = NewSet->FindSequence(Name);
        if (!Clip || Clip->GetSkeleton() != CurrentMesh->GetSkeleton()) return false;
    }
    if (bTerminalPose) return false;
    BeginPoseTransition(0.15f);
    AnimationSet = NewSet;
    ActiveAction = NAME_None;
    ActiveDefinition = FQuadrupedTemplateAction();
    IdleTime = GaitPhase = ActionTime = 0.f;
    TurnAlpha = 0.f; bHasOwnerYaw = false;
    return true;
}

void UQuadrupedTemplateAnimInstance::BeginPoseTransition(float Seconds)
{
    PreviousPose.Reset();
    if (AnimationSet && GetSkelMeshComponent()) GetSkelMeshComponent()->SnapshotPose(PreviousPose);
    TransitionDuration = FMath::Max(0.f, Seconds);
    TransitionTime = 0.f;
    TransitionAlpha = PreviousPose.bIsValid && TransitionDuration > SMALL_NUMBER ? 0.f : 1.f;
}

bool UQuadrupedTemplateAnimInstance::PlayTemplateAction(FName ActionName, bool bExternalClock)
{
    if (!AnimationSet || bTerminalPose) return false;
    const FQuadrupedTemplateAction* Entry = AnimationSet->FindAction(ActionName);
    if (!Entry || !Entry->Sequence || Entry->Sequence->GetSkeleton() != AnimationSet->ReferenceMesh->GetSkeleton()) return false;
    BeginPoseTransition(Entry->BlendSeconds);
    ActiveDefinition = *Entry;
    ActiveAction = ActionName;
    ActionTime = 0.f;
    bTerminalPose = Entry->bTerminal;
    bUseExternalClock = bExternalClock;
    return true;
}

void UQuadrupedTemplateAnimInstance::SetActionTime(float SourceSeconds)
{
    if (!bUseExternalClock || ActiveAction.IsNone() || !ActiveDefinition.Sequence) return;
    const float Length = ActiveDefinition.Sequence->GetPlayLength();
    ActionTime = ActiveDefinition.bLoop && Length > SMALL_NUMBER
        ? FMath::Fmod(FMath::Max(0.f, SourceSeconds), Length)
        : FMath::Clamp(SourceSeconds, 0.f, Length);
}

void UQuadrupedTemplateAnimInstance::FinishPoseTransition()
{
    TransitionTime = TransitionDuration;
    TransitionAlpha = 1.f;
}

bool UQuadrupedTemplateAnimInstance::ResumeLocomotion(float BlendSeconds)
{
    if (bTerminalPose) return false;
    if (ActiveAction.IsNone()) return true;
    BeginPoseTransition(BlendSeconds);
    ActiveAction = NAME_None;
    ActiveDefinition = FQuadrupedTemplateAction();
    ActionTime = 0.f;
    bUseExternalClock = false;
    return true;
}

void UQuadrupedTemplateAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if (!AnimationSet) return;
    const float Dt = FMath::Max(0.f, DeltaSeconds);
    const AActor* Owner = GetOwningActor();
    const float DesiredSpeed = bUseOwnerVelocity && Owner ? Owner->GetVelocity().Size2D() : FMath::Max(0.f, ManualSpeed);
    Speed = FMath::FInterpTo(Speed, DesiredSpeed, Dt, 10.f);
    const float WalkSpeed = FMath::Max(1.f, AnimationSet->WalkSpeed);
    const float RunSpeed = FMath::Max(WalkSpeed + 1.f, AnimationSet->RunSpeed);
    MoveAlpha = FMath::Clamp(Speed / WalkSpeed, 0.f, 1.f);
    // Keep the source gallop's gathering, suspension and back extension intact
    // at pursuit speed. Walk/run mixing is only a brief gait-change band.
    const float RunStart = FMath::Max(WalkSpeed, RunSpeed * AnimationSet->RunBlendStartRatio);
    const float RunFull = FMath::Max(RunStart + 1.f, RunSpeed * AnimationSet->RunBlendFullRatio);
    const float GaitBlend = FMath::Clamp((Speed - RunStart) / (RunFull - RunStart), 0.f, 1.f);
    WalkRunAlpha = GaitBlend * GaitBlend * (3.f - 2.f * GaitBlend);
    if (Owner && Dt > SMALL_NUMBER)
    {
        const float Yaw = Owner->GetActorRotation().Yaw;
        const float YawRate = bHasOwnerYaw ? FMath::FindDeltaAngleDegrees(PreviousOwnerYaw, Yaw) / Dt : 0.f;
        const float DesiredTurn = ActiveAction.IsNone() && Speed > 10.f
            ? FMath::Clamp(YawRate / FMath::Max(1.f, AnimationSet->FullTurnYawRate), -1.f, 1.f) * MoveAlpha : 0.f;
        TurnAlpha = FMath::FInterpTo(TurnAlpha, DesiredTurn, Dt, 8.f);
        PreviousOwnerYaw = Yaw; bHasOwnerYaw = true;
    }
    UAnimSequence* IdleClip = AnimationSet->FindSequence(TEXT("Idle"));
    UAnimSequence* WalkClip = AnimationSet->FindSequence(TEXT("Walk"));
    UAnimSequence* RunClip = AnimationSet->FindSequence(TEXT("Run"));
    if (IdleClip && IdleClip->GetPlayLength() > SMALL_NUMBER)
        IdleTime = FMath::Fmod(IdleTime + Dt, IdleClip->GetPlayLength());
    if (WalkClip && RunClip)
    {
        const float WalkStride = WalkSpeed * FMath::Max(.01f, WalkClip->GetPlayLength());
        const float RunStride = RunSpeed * FMath::Max(.01f, RunClip->GetPlayLength());
        const float Stride = FMath::Lerp(WalkStride, RunStride, WalkRunAlpha);
        GaitPhase = FMath::Fmod(GaitPhase + Speed * Dt / Stride, 1.f);
    }
    if (!ActiveAction.IsNone() && ActiveDefinition.Sequence && !bUseExternalClock)
    {
        const float Length = ActiveDefinition.Sequence->GetPlayLength();
        ActionTime += Dt * FMath::Max(.01f, ActiveDefinition.PlayRate);
        if (ActiveDefinition.bLoop && Length > SMALL_NUMBER)
            ActionTime = FMath::Fmod(ActionTime, Length);
        else if (ActionTime >= Length)
        {
            ActionTime = Length;
            if (!bTerminalPose && !ActiveDefinition.bHoldLastPose)
            {
                const FName Next = ActiveDefinition.NextAction;
                if (Next.IsNone() || !PlayTemplateAction(Next, false)) ResumeLocomotion();
            }
        }
    }
    TransitionTime += Dt;
    const float T = TransitionDuration > SMALL_NUMBER ? FMath::Clamp(TransitionTime / TransitionDuration, 0.f, 1.f) : 1.f;
    TransitionAlpha = T * T * (3.f - 2.f * T);
}

FAnimInstanceProxy* UQuadrupedTemplateAnimInstance::CreateAnimInstanceProxy() { return new FQuadrupedTemplateProxy(this); }
void UQuadrupedTemplateAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }

AQuadrupedAnimationTemplate::AQuadrupedAnimationTemplate()
{
    PrimaryActorTick.bCanEverTick = true;
    Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("QuadrupedMesh"));
    SetRootComponent(Mesh);
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    Mesh->SetAnimInstanceClass(UQuadrupedTemplateAnimInstance::StaticClass());
}

void AQuadrupedAnimationTemplate::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    if (AnimationSet && AnimationSet->ReferenceMesh) Mesh->SetSkeletalMesh(AnimationSet->ReferenceMesh);
}

void AQuadrupedAnimationTemplate::BeginPlay()
{
    Super::BeginPlay();
    if (auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(Mesh->GetAnimInstance()))
    {
        Anim->SetAnimationSet(AnimationSet);
        Anim->bUseOwnerVelocity = bUseOwnerVelocity;
        Anim->ManualSpeed = ManualSpeed;
        if (!InitialAction.IsNone()) Anim->PlayTemplateAction(InitialAction);
    }
}

void AQuadrupedAnimationTemplate::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(Mesh->GetAnimInstance()))
    {
        Anim->bUseOwnerVelocity = bUseOwnerVelocity;
        Anim->ManualSpeed = ManualSpeed;
    }
}

bool AQuadrupedAnimationTemplate::PlayTemplateAction(FName ActionName, bool bExternalClock)
{
    auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(Mesh->GetAnimInstance());
    return Anim && Anim->PlayTemplateAction(ActionName, bExternalClock);
}

void AQuadrupedAnimationTemplate::SetActionTime(float SourceSeconds)
{
    if (auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(Mesh->GetAnimInstance())) Anim->SetActionTime(SourceSeconds);
}

bool AQuadrupedAnimationTemplate::ResumeLocomotion()
{
    auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(Mesh->GetAnimInstance());
    return Anim && Anim->ResumeLocomotion();
}
