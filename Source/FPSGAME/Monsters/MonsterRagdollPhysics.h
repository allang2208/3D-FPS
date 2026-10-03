#pragma once

#include "CoreMinimal.h"

class USkeletalMeshComponent;
struct FPoseSnapshot;
struct FHitResult;

/** Short handoff window; owned by the existing monster control component/actor. */
struct FMonsterRagdollHandoff
{
    int32 FramesRemaining = 0;
    float SpeedLimit = 200.f;
    float ElapsedSeconds = 0.f;
};

struct FMonsterRagdollBodyState
{
    FTransform WorldTransform = FTransform::Identity;
    FVector LinearVelocity = FVector::ZeroVector;
    FVector AngularVelocity = FVector::ZeroVector;
};

/** Shared physical handoff for humanoids and custom rigs; gameplay owns all phases. */
namespace MonsterRagdollPhysics
{
    // ALS-Refactored-inspired body reads and initial speed limiting. MIT notice:
    // Docs/ThirdParty/ALS-Refactored-LICENSE.md. No ALS character/animation dependency.
    bool ReadBody(const USkeletalMeshComponent* Mesh, FName Bone, FMonsterRagdollBodyState& Out);
    FTransform BoneWorldTransform(const USkeletalMeshComponent* Mesh, FName Bone);
    FName ContainerRoot(const USkeletalMeshComponent* Mesh, FName AnchorBone);
    void AlignContainerRoot(USkeletalMeshComponent* Mesh, FName AnchorBone);
    void BeginHandoff(USkeletalMeshComponent* Mesh, FName AnchorBone, const FVector& LinearVelocity,
        const FVector& AngularVelocity, FMonsterRagdollHandoff& Handoff);
    void LimitHandoffSpeed(USkeletalMeshComponent* Mesh, FMonsterRagdollHandoff& Handoff, float DeltaSeconds);
    bool IsSettled(const USkeletalMeshComponent* Mesh, float LinearSpeed, float AngularSpeed);
    bool FindGround(const USkeletalMeshComponent* Mesh, FName AnchorBone, FHitResult& Out);
    // Physical support requires contact at an anatomical collision volume,
    // rather than merely finding a floor below a bone pivot.
    bool FindSupport(const USkeletalMeshComponent* Mesh, FHitResult& Out);
    void RelaxJointDrives(USkeletalMeshComponent* Mesh);
    // Whole-body height adjustment only for the non-physical animation fallback.
    void GroundAnimatedPose(USkeletalMeshComponent* Mesh);
    // Death-only retirement; status/FX timers and corpse lifespan stay owned
    // by their original systems. Living knockdown never calls this.
    void RetireCorpseTicks(USkeletalMeshComponent* Mesh);
    void CapturePose(USkeletalMeshComponent* Mesh, FPoseSnapshot& Out);
    void RebasePose(FPoseSnapshot& Pose, const FTransform& OldMeshWorld, const FTransform& NewMeshWorld);
}
