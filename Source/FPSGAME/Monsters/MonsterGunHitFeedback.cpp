#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "FatZombie.h"
#include "HundredEyedSlagMonster.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "HAL/IConsoleManager.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

namespace
{
TAutoConsoleVariable<int32> CVarMonsterGunHitFeedback(
    TEXT("fps.MonsterGunHitFeedback"), 1, TEXT("Local gunshot pose feedback, without stagger. 0=off, 1=on."));
TAutoConsoleVariable<float> CVarMonsterGunHitStrength(
    TEXT("fps.MonsterGunHitFeedback.Strength"), 1.f, TEXT("Gunshot pose feedback strength, 0..2."));

// The incoming evaluated local pose is the source on every refresh. Never
// integrate recoil back into that pose or into yesterday's display transforms.
FTransform IncomingComponentPose(const TArray<FTransform>& Local,
    const FReferenceSkeleton& Skeleton, int32 Bone)
{
    FTransform Result = Local[Bone];
    for (int32 Parent = Skeleton.GetParentIndex(Bone); Parent != INDEX_NONE;
        Parent = Skeleton.GetParentIndex(Parent)) Result = Result * Local[Parent];
    return Result;
}

bool GunHitBoneProfile(FName BoneName, bool bPhysicalBody, float& Degrees, bool& bPinChildren)
{
    const FString Name = BoneName.ToString().ToLower();
    // Decorative deformation/IK bones and the main body anchor retain their pose.
    if (Name == TEXT("root") || Name == TEXT("pelvis") || Name == TEXT("hips")
        || Name == TEXT("base") || Name.EndsWith(TEXT("-pelvis"))
        || Name.Contains(TEXT("twist")) || Name.Contains(TEXT("ik_"))
        || Name.Contains(TEXT("weapon")) || Name.Contains(TEXT("socket"))
        || Name.Contains(TEXT("staff")) || Name.Contains(TEXT("skirt"))
        || Name.Contains(TEXT("robe")) || Name.Contains(TEXT("cloth"))) return false;

    bPinChildren = false;
    if (Name.Contains(TEXT("thigh")) || Name.Contains(TEXT("upperleg"))
        || Name.Contains(TEXT("calf")) || Name.Contains(TEXT("lowerleg"))
        || Name.Contains(TEXT("foot")) || Name.Contains(TEXT("ankle")))
    {
        // A small skin/joint flinch, keeping the distal support chain in place.
        Degrees = 1.15f; bPinChildren = true; return true;
    }
    if (Name.Contains(TEXT("head")) || Name.Contains(TEXT("neck"))
        || Name.Contains(TEXT("cranium"))) { Degrees = 4.5f; return true; }
    if (Name.Contains(TEXT("spine")) || Name.Contains(TEXT("chest"))
        || Name.Contains(TEXT("carapace"))) { Degrees = 3.2f; return true; }
    if (Name.Contains(TEXT("body_"))) { Degrees = 2.5f; return true; }
    if (Name.Contains(TEXT("upperarm")) || Name.Contains(TEXT("lowerarm"))
        || Name.Contains(TEXT("upper_arm")) || Name.Contains(TEXT("lower_arm"))
        || Name.Contains(TEXT("forearm")) || Name.Contains(TEXT("clavicle"))
        || Name.Contains(TEXT("shoulder"))) { Degrees = 3.5f; return true; }
    if (Name.Contains(TEXT("palm")) || Name.Contains(TEXT("metacarpal")))
    { Degrees = 2.5f; return true; }
    // Dedicated rigs also expose meaningful joint names through their Physics Asset.
    Degrees = 2.5f;
    return bPhysicalBody;
}
}

void UMonsterIdleBreathingMeshComponent::CacheGunHitBones()
{
    auto* Mesh = GetSkeletalMeshAsset();
    auto* Physics = GetPhysicsAsset();
    if (!Mesh || (Mesh == GunHitMesh.Get() && Physics == GunHitPhysicsAsset.Get())) return;
    GunHitMesh = Mesh; GunHitPhysicsAsset = Physics;
    GunHitBones.Reset(); GunHitPulses.Reset(); PreviousGunHitTracks.Reset();
    const auto& Skeleton = Mesh->GetRefSkeleton();
    GunHitBoneLookup.Init(INDEX_NONE, Skeleton.GetNum());
    TSet<FName> PhysicalBones;
    if (Physics)
        for (const auto& HitBodySetup : Physics->SkeletalBodySetups)
            if (HitBodySetup) PhysicalBones.Add(HitBodySetup->BoneName);
    for (int32 Bone = 1; Bone < Skeleton.GetNum(); ++Bone)
    {
        float Degrees = 0.f; bool bPinChildren = false;
        const FName Name = Skeleton.GetBoneName(Bone);
        if (!GunHitBoneProfile(Name, PhysicalBones.Contains(Name), Degrees, bPinChildren)) continue;
        GunHitBoneLookup[Bone] = GunHitBones.Num();
        auto& Track = GunHitBones.AddDefaulted_GetRef();
        Track.Index = Bone; Track.Degrees = Degrees; Track.bPinChildren = bPinChildren;
        if (bPinChildren) continue;
        for (int32 Child = Bone + 1; Child < Skeleton.GetNum(); ++Child)
            for (int32 Parent = Skeleton.GetParentIndex(Child); Parent != INDEX_NONE;
                Parent = Skeleton.GetParentIndex(Parent))
                if (Parent == Bone) { Track.Descendants.Add(Child); break; }
    }
}

void UMonsterIdleBreathingMeshComponent::AddGunHitFeedback(
    const FHitResult& Hit, const FVector& ShotDirection, float Damage)
{
    auto* World = GetWorld();
    auto* Execution = GetOwner() ? GetOwner()->FindComponentByClass<UMonsterCombatComponent>() : nullptr;
    if (!World || !World->IsGameWorld() || GetNetMode() == NM_DedicatedServer
        || CVarMonsterGunHitFeedback.GetValueOnGameThread() == 0 || !Execution
        || Execution->IsDead() || Execution->IsControlled() || Execution->IsKnockedDown()
        || bPauseAnims || IsSimulatingPhysics()) return;
    const float Strength = FMath::Clamp(CVarMonsterGunHitStrength.GetValueOnGameThread(), 0.f, 2.f);
    if (Strength <= 0.f) return;
    CacheGunHitBones();
    const auto* Mesh = GetSkeletalMeshAsset();
    if (!Mesh || GunHitBones.IsEmpty()) return;
    const auto& Skeleton = Mesh->GetRefSkeleton();
    int32 TrackIndex = INDEX_NONE;
    for (int32 Bone = Skeleton.FindBoneIndex(Hit.BoneName); Bone != INDEX_NONE;
        Bone = Skeleton.GetParentIndex(Bone))
        if (GunHitBoneLookup[Bone] != INDEX_NONE) { TrackIndex = GunHitBoneLookup[Bone]; break; }
    // Hits on the character capsule carry no bone name. Resolve the nearest
    // cached anatomical joint at this contact; no mesh scan or tick-time query.
    if (TrackIndex == INDEX_NONE)
    {
        float BestDistance = TNumericLimits<float>::Max();
        for (int32 Track = 0; Track < GunHitBones.Num(); ++Track)
        {
            const float Distance = FVector::DistSquared(Hit.ImpactPoint,
                GetBoneLocation(Skeleton.GetBoneName(GunHitBones[Track].Index)));
            if (Distance < BestDistance) { BestDistance = Distance; TrackIndex = Track; }
        }
    }
    const auto& Track = GunHitBones[TrackIndex];
    const FVector Direction = ShotDirection.GetSafeNormal();
    if (Direction.IsNearlyZero()) return;
    const FVector Pivot = GetBoneLocation(Skeleton.GetBoneName(Track.Index));
    FVector Lever = Hit.ImpactPoint - Pivot;
    // Centered/front-on contacts still bend along the bullet's travel direction.
    const FVector Up = GetOwner()->GetActorUpVector();
    if (Lever.SizeSquared() < 9.f || FMath::Abs(FVector::DotProduct(Lever.GetSafeNormal(), Direction)) > .94f)
        Lever = Up;
    FVector Axis = FVector::CrossProduct(Lever.GetSafeNormal(), Direction).GetSafeNormal();
    if (Axis.IsNearlyZero()) Axis = FVector::CrossProduct(GetOwner()->GetActorRightVector(), Direction).GetSafeNormal();
    if (Axis.IsNearlyZero()) return;

    const bool bSlag = GetOwner()->IsA<AHundredEyedSlagMonster>();
    const bool bHeavy = bSlag || GetOwner()->IsA<AFatZombie>();
    const float MassScale = bSlag ? .55f : bHeavy ? .72f : 1.f;
    const double Time = World->GetTimeSeconds();
    GunHitPulses.RemoveAll([Time](const auto& Pulse) { return Time - Pulse.StartTime >= Pulse.Duration; });
    if (GunHitPulses.Num() == 4) GunHitPulses.RemoveAt(0);
    auto& Pulse = GunHitPulses.AddDefaulted_GetRef();
    Pulse.Track = TrackIndex; Pulse.AxisWorld = Axis; Pulse.StartTime = Time;
    Pulse.Duration = bHeavy ? .30f : .26f;
    Pulse.Radians = FMath::DegreesToRadians(Track.Degrees * MassScale * Strength
        * FMath::Clamp(.85f + Damage / 160.f, .85f, 1.45f));
}

bool UMonsterIdleBreathingMeshComponent::ApplyGunHitFeedback()
{
    const auto* Execution = Combat.Get();
    const auto* Mesh = GetSkeletalMeshAsset();
    if (!Execution || Execution->IsDead() || Execution->IsControlled() || Execution->IsKnockedDown()
        || bPauseAnims || IsSimulatingPhysics() || !Mesh || Mesh != GunHitMesh.Get())
    {
        GunHitPulses.Reset(); PreviousGunHitTracks.Reset();
        return false;
    }
    if (GunHitPulses.IsEmpty() && PreviousGunHitTracks.IsEmpty()) return false;
    const double Time = GetWorld()->GetTimeSeconds();
    GunHitPulses.RemoveAll([Time](const auto& Pulse) { return Time - Pulse.StartTime >= Pulse.Duration; });
    if (CVarMonsterGunHitFeedback.GetValueOnGameThread() == 0
        || CVarMonsterGunHitStrength.GetValueOnGameThread() <= 0.f) GunHitPulses.Reset();
    auto& Pose = GetEditableComponentSpaceTransforms();
    const auto Local = GetBoneSpaceTransforms();
    const auto& Skeleton = Mesh->GetRefSkeleton();
    if (Pose.Num() != Skeleton.GetNum() || Local.Num() != Skeleton.GetNum()) return false;

    TArray<int32, TInlineAllocator<8>> RestoreTracks;
    for (const int32 Track : PreviousGunHitTracks) RestoreTracks.AddUnique(Track);
    PreviousGunHitTracks.Reset();
    for (const auto& Pulse : GunHitPulses)
    {
        RestoreTracks.AddUnique(Pulse.Track);
        PreviousGunHitTracks.AddUnique(Pulse.Track);
    }
    // Restore each affected branch before composing this frame's offsets. This
    // also removes the last offset on the expiration frame, without pose drift.
    for (const int32 TrackIndex : RestoreTracks)
    {
        const auto& Track = GunHitBones[TrackIndex];
        Pose[Track.Index] = IncomingComponentPose(Local, Skeleton, Track.Index);
        for (const int32 Child : Track.Descendants)
            Pose[Child] = IncomingComponentPose(Local, Skeleton, Child);
    }
    TArray<FVector, TInlineAllocator<4>> Rotations;
    float TotalAngle = 0.f;
    for (const auto& Pulse : GunHitPulses)
    {
        const float Phase = FMath::Clamp(float(Time - Pulse.StartTime) / Pulse.Duration, 0.f, 1.f);
        // Fast flex, one smaller rebound, then zero. Animation keeps advancing.
        const float Weight = 2.f * FMath::Sin(2.f * PI * Phase) * FMath::Exp(-3.f * Phase);
        const float Angle = Pulse.Radians * Weight;
        Rotations.Add(GetComponentTransform().InverseTransformVectorNoScale(Pulse.AxisWorld).GetSafeNormal() * Angle);
        TotalAngle += FMath::Abs(Angle);
    }
    const float Limit = FMath::DegreesToRadians(7.f);
    const float Scale = TotalAngle > Limit ? Limit / TotalAngle : 1.f;
    for (int32 I = 0; I < GunHitPulses.Num(); ++I)
    {
        const auto& Track = GunHitBones[GunHitPulses[I].Track];
        const FVector Rotation = Rotations[I] * Scale;
        const float Angle = Rotation.Size();
        if (Angle <= SMALL_NUMBER) continue;
        const FTransform Before = Pose[Track.Index];
        FTransform After = Before;
        After.SetRotation((FQuat(Rotation / Angle, Angle) * Before.GetRotation()).GetNormalized());
        Pose[Track.Index] = After;
        for (const int32 Child : Track.Descendants)
            Pose[Child] = Pose[Child].GetRelativeTransform(Before) * After;
    }
    return !GunHitPulses.IsEmpty();
}
