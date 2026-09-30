#include "MonsterCombatComponent.h"
#include "NurseZombie.h"
#include "FatZombieAnimInstance.h"
#include "../Combat/CombatStatusFormula.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"

float UMonsterCombatComponent::StunSecondsRemaining() const
{
    return GetWorld()?float(FMath::Max(0.0,ExplicitStunUntil-GetWorld()->GetTimeSeconds())):0.f;
}

void UMonsterCombatComponent::RegisterExplicitStun(float Seconds)
{
    if(Seconds>0.f && GetWorld())
        ExplicitStunUntil=FMath::Max(ExplicitStunUntil,double(GetWorld()->GetTimeSeconds())+Seconds);
    bStunned=StunSecondsRemaining()>0.f;
}

bool UMonsterCombatComponent::IsImmobileReaction() const
{
    const auto* Status=SwayStatus.Get();
    return Status && (Status->IsFrozen() || Status->IsPetrified());
}

void UMonsterCombatComponent::LoadHumanoidStun()
{
    const auto* N=Cast<ANurseZombie>(GetOwner());
    if(!N || !N->GetMesh()->GetSkeletalMeshAsset())return;
    if(N->ActorHasTag(TEXT("Witch")) && !N->ActorHasTag(TEXT("WitchRebuilt")))return;
    const FString Role=N->ActorHasTag(TEXT("WitchRebuilt"))?TEXT("Witch"):
        N->ActorHasTag(TEXT("Mutant3"))?TEXT("Mutant3"):N->ActorHasTag(TEXT("FatZombie"))?TEXT("FatZombie"):TEXT("Nurse");
    if(!DizzyClip)
    {
        const FString Name=TEXT("A_")+Role+TEXT("_Dizzy");
        DizzyClip=LoadObject<UAnimSequence>(nullptr,*(TEXT("/Game/Monsters/HumanoidStun/")+Role+TEXT("/")+Name+TEXT(".")+Name));
    }
    if(DizzyClip && DizzyClip->GetSkeleton()!=N->GetMesh()->GetSkeletalMeshAsset()->GetSkeleton())DizzyClip=nullptr;
}

void UMonsterCombatComponent::ClearHumanoidStun()
{
    bSwayArmed=bPlayingSway=bLeavingSway=false;
    SwayTime=SwayBlendTime=0.f;
}

bool UMonsterCombatComponent::BeginHumanoidStun(float Duration)
{
    SwayEntrySeconds=bParryReaction?.45f:.14f;
    // Adding stun/freeze/petrify invokes BeginReaction, so refresh here rather
    // than scanning the actor's component array on every presentation frame.
    SwayStatus=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
    const bool bImmobilePose=IsImmobileReaction();
    const float StunRemaining=StunSecondsRemaining();
    const bool bEligible=bStunned && DizzyClip && FMath::Min(Duration,StunRemaining)>=SwayEntrySeconds+.3f;
    if(bPlayingSway && bStunned && !bImmobilePose && !bParryReaction)
    {
        // Refresh control without restarting the impact or the loop's phase.
        if(bLeavingSway && StunRemaining>.22f){PlayHumanoidStunClip(DizzyClip,.12f);bLeavingSway=false;}
        bSwayArmed=true;
        return true;
    }
    ClearHumanoidStun();
    bSwayArmed=bEligible;
    return false;
}

void UMonsterCombatComponent::PlayHumanoidStunClip(UAnimSequence* Clip,float BlendSeconds)
{
    auto* N=Cast<ANurseZombie>(GetOwner());
    if(!N || !Clip)return;
    auto* Mesh=N->GetMesh();
    FPoseSnapshot Pose;Mesh->SnapshotPose(Pose);
    // Fat/Mutant/Witch already derive from this player; keep their native class.
    // Nurse's ordinary state presentation restores its single-node player later.
    auto* Animation=Cast<UFatZombieAnimInstance>(Mesh->GetAnimInstance());
    if(!Animation)
    {
        Mesh->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
        Animation=Cast<UFatZombieAnimInstance>(Mesh->GetAnimInstance());
    }
    if(Animation)
    {
        Animation->RecoverFromSnapshot(Clip,Pose,BlendSeconds);
        Animation->SetControlledBlendTime(0.f);
    }
    SwayBlendTime=0.f;
}

bool UMonsterCombatComponent::UpdateHumanoidStun(float Elapsed,float Remaining)
{
    auto* N=Cast<ANurseZombie>(GetOwner());
    if(!bSwayArmed || !N || N->State!=ENurseState::Stagger || !DizzyClip)return false;
    if(IsImmobileReaction())
    {
        if(bPlayingSway)
        {
            bPlayingSway=bLeavingSway=false;
            SwayTime=SwayBlendTime=0.f;
            N->StartHitPresentation(HitClip,FMath::Max(.01f,Remaining));
        }
        return false;
    }
    if(!bPlayingSway)
    {
        if(!bStunned){bSwayArmed=false;return false;}
        if(Elapsed<SwayEntrySeconds)return false;
        PlayHumanoidStunClip(DizzyClip,.16f);
        bPlayingSway=true;SwayTime=0.f;
    }
    // A later toughness break may outlast the stun. Stop swaying at the actual
    // stun expiry, then breathe in idle while the remaining physical lock ends.
    Remaining=FMath::Min(Remaining,StunSecondsRemaining());
    if(!bLeavingSway && Remaining<=.22f && N->IdleClip)
    {
        PlayHumanoidStunClip(N->IdleClip,FMath::Max(.01f,Remaining));
        bLeavingSway=true;
    }
    if(auto* Animation=Cast<UFatZombieAnimInstance>(N->GetMesh()->GetAnimInstance()))
    {
        // Sample looping time explicitly: this is presentation, not a second
        // stun/attack timer, and it never changes the collision capsule.
        const float Time=bLeavingSway?FMath::Fmod(SwayBlendTime,FMath::Max(.01f,N->IdleClip->GetPlayLength())):
            FMath::Fmod(SwayTime*FMath::Clamp(DizzyPlayRate,.25f,2.f),FMath::Max(.01f,DizzyClip->GetPlayLength()));
        Animation->SetCombatTime(Time);
        Animation->SetControlledBlendTime(SwayBlendTime);
    }
    return true;
}
