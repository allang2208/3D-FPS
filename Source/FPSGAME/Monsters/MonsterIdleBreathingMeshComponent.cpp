#include "MonsterIdleBreathingMeshComponent.h"
#include "BlindSupplicantMonster.h"
#include "FatZombie.h"
#include "FleshHandMonster.h"
#include "HandBrainMonster.h"
#include "HundredEyedSlagMonster.h"
#include "InfectedDogMonster.h"
#include "MonsterCombatComponent.h"
#include "Mutant3.h"
#include "NurseZombie.h"
#include "PoisonMaggotMonster.h"
#include "SpitterZombie.h"
#include "WitchRebuiltMonster.h"
#include "WolfMonster.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
enum class EBreathingBody : uint8 { None, Humanoid, Hand, Brain, Maggot, Canine, Slag };

EBreathingBody BodyFor(const AActor* Owner)
{
    if (!Owner || Owner->IsA<ABlindSupplicantMonster>()) return EBreathingBody::None;
    if (Owner->IsA<AHundredEyedSlagMonster>()) return EBreathingBody::Slag;
    if (Owner->IsA<AFleshHandMonster>()) return EBreathingBody::Hand;
    if (Owner->IsA<AHandBrainMonster>()) return EBreathingBody::Brain;
    if (Owner->IsA<APoisonMaggotMonster>()) return EBreathingBody::Maggot;
    if (Owner->IsA<AWolfMonster>()) return EBreathingBody::Canine;
    if (Owner->IsA<ANurseZombie>()) return EBreathingBody::Humanoid;
    return EBreathingBody::None;
}

bool IsIdle(const ACharacter* Owner, EBreathingBody Body)
{
    switch (Body)
    {
    case EBreathingBody::Humanoid: return CastChecked<ANurseZombie>(Owner)->State == ENurseState::Idle;
    case EBreathingBody::Hand: return CastChecked<AFleshHandMonster>(Owner)->State == EFleshHandState::Idle;
    case EBreathingBody::Brain: return CastChecked<AHandBrainMonster>(Owner)->State == EHandBrainState::Idle;
    case EBreathingBody::Maggot: return CastChecked<APoisonMaggotMonster>(Owner)->State == EPoisonMaggotState::Idle;
    case EBreathingBody::Canine: return CastChecked<AWolfMonster>(Owner)->State == EWolfState::Idle;
    case EBreathingBody::Slag: return CastChecked<AHundredEyedSlagMonster>(Owner)->State == ESlagState::Idle;
    default: return false;
    }
}

// Read only the original evaluated local pose, so repeated refreshes never
// accumulate the breathing additions already present in the display buffer.
FTransform OriginalComponentPose(const TArray<FTransform>& LocalPose,
    const FReferenceSkeleton& Skeleton, int32 Index)
{
    FTransform Result = LocalPose[Index];
    for (int32 Parent = Skeleton.GetParentIndex(Index); Parent != INDEX_NONE;
        Parent = Skeleton.GetParentIndex(Parent)) Result = Result * LocalPose[Parent];
    return Result;
}
}

void UMonsterIdleBreathingMeshComponent::AddBone(std::initializer_list<const TCHAR*> Names,
    float Pitch, float Expansion, float Delay, float Sway, bool bKeepChildren)
{
    auto& Track = BreathingBones.AddDefaulted_GetRef();
    for (const TCHAR* Name : Names) Track.Candidates.Add(FName(Name));
    Track.PitchDegrees = Pitch; Track.Expansion = Expansion;
    Track.Delay = Delay; Track.SwayDegrees = Sway; Track.bKeepChildren = bKeepChildren;
}

void UMonsterIdleBreathingMeshComponent::ConfigureBreathing(ACharacter* Character)
{
    bConfigured = true;
    Combat = Character->FindComponentByClass<UMonsterCombatComponent>();
    const auto Profile = BodyFor(Character);
    Body = uint8(Profile);
    Seed = float(GetTypeHash(Character->GetFName()) % 65536u) / 65536.f;
    switch (Profile)
    {
    case EBreathingBody::Humanoid:
    {
        float Pitch = .45f, Expansion = .008f;
        Period = 3.8f;
        if (Character->IsA<AFatZombie>()) { Period = 4.5f; Pitch = .7f; Expansion = .013f; }
        else if (Character->IsA<AMutant3>()) { Period = 2.9f; Pitch = .65f; Expansion = .009f; }
        else if (Character->IsA<ASpitterZombie>()) { Period = 3.4f; Pitch = .55f; Expansion = .010f; }
        else if (Character->IsA<AWitchRebuiltMonster>()) { Period = 4.1f; Pitch = .35f; Expansion = .006f; }
        if (Character->IsA<AWitchRebuiltMonster>())
            AddBone({TEXT("spine_05"), TEXT("spine_04"), TEXT("spine_03")}, Pitch, Expansion);
        else AddBone({TEXT("spine_03"), TEXT("Spine"), TEXT("spine_02"), TEXT("chest")}, Pitch, Expansion);
        AddBone({TEXT("neck_01"), TEXT("neck"), TEXT("Neck"), TEXT("Head"), TEXT("head")}, .16f, 0.f, .35f, .09f, false);
        break;
    }
    case EBreathingBody::Slag:
        Period = 5.2f;
        AddBone({TEXT("chest")}, .32f, .008f, 0.f, .045f);
        AddBone({TEXT("carapace"), TEXT("head"), TEXT("neck")}, .12f, 0.f, .5f, .065f);
        break;
    case EBreathingBody::Canine:
        // Wolf and zombie-dog IdleBreathe already supply the main chest cycle.
        Period = Character->IsA<AInfectedDogMonster>() ? 2.9f : 3.2f;
        AddBone({TEXT("Wolf_-Spine1"), TEXT("chest"), TEXT("spine_02"), TEXT("Spine1"), TEXT("Chest")}, .16f, .004f, 0.f, .045f);
        AddBone({TEXT("Wolf_-Neck"), TEXT("neck_01"), TEXT("Neck"), TEXT("neck"), TEXT("head")}, .12f, 0.f, .35f, .08f, false);
        break;
    case EBreathingBody::Maggot:
        Period = 3.3f;
        AddBone({TEXT("body_03")}, .10f, .009f);
        AddBone({TEXT("body_05")}, .13f, .010f, .35f, .04f);
        AddBone({TEXT("body_07")}, .11f, .008f, .7f, .04f);
        break;
    case EBreathingBody::Brain:
        Period = 4.8f;
        AddBone({TEXT("neck")}, .2f, .006f, 0.f, .05f);
        AddBone({TEXT("cranium")}, .14f, .003f, .45f, .06f);
        break;
    case EBreathingBody::Hand:
    {
        const bool bSmall = CastChecked<AFleshHandMonster>(Character)->bMinion;
        Period = bSmall ? 2.8f : 4.2f;
        AddBone({TEXT("palm")}, bSmall ? .12f : .18f, bSmall ? .002f : .003f);
        AddBone({TEXT("index_metacarpal"), TEXT("index_01")}, bSmall ? .12f : .2f, 0.f, .35f, .04f, false);
        AddBone({TEXT("ring_metacarpal"), TEXT("ring_01")}, bSmall ? .1f : .16f, 0.f, .7f, .04f, false);
        break;
    }
    default: break;
    }
    Period *= FMath::Lerp(.94f, 1.06f, Seed);
}

void UMonsterIdleBreathingMeshComponent::CacheBones()
{
    auto* Mesh = GetSkeletalMeshAsset();
    if (!Mesh || Mesh == CachedMesh.Get()) return;
    CachedMesh = Mesh;
    const auto& Skeleton = Mesh->GetRefSkeleton();
    for (auto& Track : BreathingBones)
    {
        Track.Index = INDEX_NONE; Track.Descendants.Reset();
        for (const FName Candidate : Track.Candidates)
        {
            Track.Index = Skeleton.FindBoneIndex(Candidate);
            if (Track.Index != INDEX_NONE) break;
        }
        if (Track.Index == INDEX_NONE || Track.bKeepChildren) continue;
        for (int32 I = Track.Index + 1; I < Skeleton.GetNum(); ++I)
        {
            for (int32 Parent = Skeleton.GetParentIndex(I); Parent != INDEX_NONE;
                Parent = Skeleton.GetParentIndex(Parent))
                if (Parent == Track.Index) { Track.Descendants.Add(I); break; }
        }
    }
}

void UMonsterIdleBreathingMeshComponent::FinalizeBoneTransform()
{
    auto* Character = Cast<ACharacter>(GetOwner());
    // No preview/studio animation, dedicated-server work or change to M-07 poses.
    if (!Character || !GetWorld() || !GetWorld()->IsGameWorld() || GetNetMode() == NM_DedicatedServer)
    {
        Super::FinalizeBoneTransform();
        return;
    }
    if (!bConfigured) ConfigureBreathing(Character);
    // Independent of idle/locomotion/attack clips, including M-07's custom proxy.
    const bool bGunHitFeedback = ApplyGunHitFeedback();
    if (EBreathingBody(Body) == EBreathingBody::None)
    {
        Super::FinalizeBoneTransform();
        return;
    }
    CacheBones();
    const auto* Execution = Combat.Get();
    const auto* Movement = Character->GetCharacterMovement();
    const bool bHardOff = !Execution || !Character->IsActorTickEnabled() || Character->IsHidden()
        || Execution->IsDead() || Execution->IsControlled() || Execution->IsKnockedDown()
        || bPauseAnims || IsSimulatingPhysics() || !Movement || !Movement->IsMovingOnGround();
    const bool bIdle = !bHardOff && IsIdle(Character, EBreathingBody(Body)) && !Execution->IsBusy()
        && Character->GetVelocity().SizeSquared() < 9.f;
    const double Time = GetWorld()->GetTimeSeconds();
    const float Dt = PreviousTime < 0.0 ? GetWorld()->GetDeltaSeconds() : float(FMath::Max(0.0, Time - PreviousTime));
    PreviousTime = Time;
    if (bHardOff || bGunHitFeedback) IdleWeight = 0.f;
    else
    {
        const float Target = bIdle ? 1.f : 0.f;
        const float Duration = bIdle ? .35f : .12f;
        IdleWeight = FMath::Lerp(IdleWeight, Target, 1.f - FMath::Exp(-Dt / Duration));
    }
    const auto* Mesh = GetSkeletalMeshAsset();
    if (Mesh && IdleWeight > .001f)
    {
        auto& Pose = GetEditableComponentSpaceTransforms();
        const auto& LocalPose = GetBoneSpaceTransforms();
        const auto& Skeleton = Mesh->GetRefSkeleton();
        if (Pose.Num() == Skeleton.GetNum() && LocalPose.Num() == Skeleton.GetNum())
        {
            const double Phase = Time * (2.0 * PI / Period) + double(Seed) * 2.0 * PI
                + .10 * FMath::Sin(Time * .29 + double(Seed) * 7.0);
            const float Micro = .7f * FMath::PerlinNoise1D(float(Time * .45 + double(Seed) * 43.0))
                + .3f * FMath::PerlinNoise1D(float(Time * .81 + double(Seed) * 79.0));
            const auto& Component = GetComponentTransform();
            const FVector PitchAxis = Component.InverseTransformVectorNoScale(Character->GetActorRightVector()).GetSafeNormal();
            const FVector SwayAxis = Component.InverseTransformVectorNoScale(Character->GetActorForwardVector()).GetSafeNormal();
            for (const auto& Track : BreathingBones)
            {
                if (Track.Index == INDEX_NONE) continue;
                const FTransform Before = OriginalComponentPose(LocalPose, Skeleton, Track.Index);
                const double P = Phase - Track.Delay;
                const float Breath = float((FMath::Sin(P) + .12 * FMath::Sin(2.0 * P - .45)) / 1.12);
                const float Pitch = FMath::DegreesToRadians(Track.PitchDegrees * Breath * IdleWeight);
                const float Sway = FMath::DegreesToRadians(Track.SwayDegrees * Micro * IdleWeight);
                FTransform After = Before;
                After.SetRotation((FQuat(PitchAxis, Pitch) * FQuat(SwayAxis, Sway) * Before.GetRotation()).GetNormalized());
                const FVector Depth = Before.GetRotation().UnrotateVector(SwayAxis).GetAbs();
                const FVector Expansion = (FVector(.25f) + Depth * .75f) * (Track.Expansion * Breath * IdleWeight);
                After.SetScale3D(Before.GetScale3D() * (FVector::OneVector + Expansion));
                Pose[Track.Index] = After;
                // Component-space edits leave all unselected branches at their
                // incoming pose. Neck/finger motion alone follows its descendants.
                // Roots, pelvises, legs, feet and prop-bearing arms are not moved.
                for (const int32 Child : Track.Descendants)
                {
                    const FTransform Original = OriginalComponentPose(LocalPose, Skeleton, Child);
                    Pose[Child] = Original.GetRelativeTransform(Before) * After;
                }
            }
        }
    }
    Super::FinalizeBoneTransform();
}
