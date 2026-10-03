#include "MonsterRagdollPhysics.h"
#include "HumanoidRagdollBudget.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "Animation/PoseSnapshot.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/ConstraintInstance.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

namespace MonsterRagdollPhysics
{
void RetireCorpseTicks(USkeletalMeshComponent* Mesh)
{
    Mesh->SuspendClothingSimulation();
    Mesh->SetComponentTickEnabled(false);
    auto* Owner = Mesh->GetOwner();
    Owner->SetActorTickEnabled(false);
    if (auto* Combat = Owner->FindComponentByClass<UMonsterCombatComponent>())
        Combat->SetComponentTickEnabled(false);
    if (auto* Character = Cast<ACharacter>(Owner))
    {
        Character->GetCharacterMovement()->DisableMovement();
        Character->GetCharacterMovement()->SetComponentTickEnabled(false);
        if (auto* AI = Cast<AMonsterAIController>(Character->GetController())) AI->UpdateKnowledge();
    }
    if (auto* Budget = Mesh->GetWorld()->GetSubsystem<UHumanoidRagdollBudget>())
        Budget->RegisterFrozenMesh(Mesh);
}

bool ReadBody(const USkeletalMeshComponent* Mesh, FName Bone, FMonsterRagdollBodyState& Out)
{
    const FBodyInstance* Body = Mesh ? Mesh->GetBodyInstance(Bone) : nullptr;
    if (!Body || !Body->IsValidBodyInstance() || !Body->IsInstanceSimulatingPhysics()) return false;
    // Read one coherent physics state, independent of animation ticking and URO.
    return FPhysicsCommand::ExecuteRead(Body->GetPhysicsActorHandle(), [&Out](const FPhysicsActorHandle& Handle)
    {
        Out.WorldTransform = FPhysicsInterface::GetTransform_AssumesLocked(Handle, true);
        Out.LinearVelocity = FPhysicsInterface::GetLinearVelocity_AssumesLocked(Handle);
        Out.AngularVelocity = FPhysicsInterface::GetAngularVelocity_AssumesLocked(Handle);
    });
}

FTransform BoneWorldTransform(const USkeletalMeshComponent* Mesh, FName Bone)
{
    FMonsterRagdollBodyState Body;
    if (ReadBody(Mesh, Bone, Body)) return Body.WorldTransform;
    // Frozen snapshots and the budget's animated fallback have no dynamic body.
    return Mesh ? Mesh->GetSocketTransform(Bone) : FTransform::Identity;
}

FName ContainerRoot(const USkeletalMeshComponent* Mesh, FName AnchorBone)
{
    if (!Mesh || !Mesh->GetSkeletalMeshAsset()) return NAME_None;
    const auto& Ref = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    if (Ref.GetNum() == 0) return NAME_None;
    const FName Root = Ref.GetBoneName(0);
    if (Root == AnchorBone || !Mesh->GetBodyInstance(Root)) return NAME_None;
    // Only a top-level physical helper connected directly to the anchor qualifies.
    // A pelvis-first skeleton has no helper; anatomical joints keep their asset frames.
    for (const FConstraintInstance* Joint : Mesh->Constraints)
        if (Joint && ((Joint->ConstraintBone1 == AnchorBone && Joint->ConstraintBone2 == Root) ||
            (Joint->ConstraintBone2 == AnchorBone && Joint->ConstraintBone1 == Root))) return Root;
    return NAME_None;
}

void AlignContainerRoot(USkeletalMeshComponent* Mesh, FName AnchorBone)
{
    const FName Root = ContainerRoot(Mesh, AnchorBone);
    if (Root.IsNone()) return;
    for (FConstraintInstance* Joint : Mesh->Constraints)
    {
        if (!Joint || !((Joint->ConstraintBone1 == AnchorBone && Joint->ConstraintBone2 == Root) ||
            (Joint->ConstraintBone2 == AnchorBone && Joint->ConstraintBone1 == Root))) continue;
        const auto* Child = Mesh->GetBodyInstance(Joint->ConstraintBone1);
        const auto* Parent = Mesh->GetBodyInstance(Joint->ConstraintBone2);
        if (!Child || !Parent || !Child->IsValidBodyInstance() || !Parent->IsValidBodyInstance()) continue;
        FTransform ChildWorld = Child->GetUnrealWorldTransform(false, true);
        FTransform ParentWorld = Parent->GetUnrealWorldTransform(false, true);
        ChildWorld.RemoveScaling(); ParentWorld.RemoveScaling();
        // Live frames are rigid-body centimetres, including rigs with a scaled root.
        Joint->SetRefFrame(EConstraintFrame::Frame1, FTransform::Identity);
        Joint->SetRefFrame(EConstraintFrame::Frame2, ChildWorld.GetRelativeTransform(ParentWorld));
        Joint->SetLinearXLimit(LCM_Locked, 0.f); Joint->SetLinearYLimit(LCM_Locked, 0.f);
        Joint->SetLinearZLimit(LCM_Locked, 0.f);
        Joint->SetAngularSwing1Limit(ACM_Locked, 0.f); Joint->SetAngularSwing2Limit(ACM_Locked, 0.f);
        Joint->SetAngularTwistLimit(ACM_Locked, 0.f); Joint->SetDisableCollision(true);
    }
    if (auto* Body = Mesh->GetBodyInstance(Root)) Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void BeginHandoff(USkeletalMeshComponent* Mesh, FName AnchorBone, const FVector& LinearVelocity,
    const FVector& AngularVelocity, FMonsterRagdollHandoff& Handoff)
{
    Handoff = FMonsterRagdollHandoff{};
    if (!Mesh) return;
    const auto* Anchor = Mesh->GetBodyInstance(AnchorBone);
    const FVector Pivot = Anchor && Anchor->IsValidBodyInstance() ? Anchor->GetCOMPosition() :
        BoneWorldTransform(Mesh, AnchorBone).GetLocation();
    for (FBodyInstance* Body : Mesh->Bodies)
    {
        if (!Body || !Body->IsInstanceSimulatingPhysics()) continue;
        Body->ClearForces(); Body->ClearTorques();
        // One rigid motion at each COM avoids independent limb kicks fighting joints.
        const FVector Velocity = LinearVelocity + FVector::CrossProduct(AngularVelocity, Body->GetCOMPosition() - Pivot);
        Body->SetLinearVelocity(Velocity, false);
        Body->SetAngularVelocityInRadians(AngularVelocity, false);
        Handoff.SpeedLimit = FMath::Max(Handoff.SpeedLimit, static_cast<float>(Velocity.Size()));
    }
    Handoff.FramesRemaining = 8;
    Mesh->WakeAllRigidBodies();
}

void LimitHandoffSpeed(USkeletalMeshComponent* Mesh, FMonsterRagdollHandoff& Handoff, float DeltaSeconds)
{
    if (!Mesh || Handoff.FramesRemaining <= 0) return;
    Handoff.ElapsedSeconds += FMath::Max(0.f, DeltaSeconds);
    // Retain intended launch/rotation and gravity instead of capping a legitimate fall.
    const float Gravity = Mesh->GetWorld() ? FMath::Abs(Mesh->GetWorld()->GetGravityZ()) : 980.f;
    const float Limit = Handoff.SpeedLimit + Gravity * Handoff.ElapsedSeconds;
    for (FBodyInstance* Body : Mesh->Bodies)
    {
        if (!Body || !Body->IsInstanceSimulatingPhysics()) continue;
        FPhysicsCommand::ExecuteWrite(Body->GetPhysicsActorHandle(), [Limit](const FPhysicsActorHandle& Handle)
        {
            const FVector Velocity = FPhysicsInterface::GetLinearVelocity_AssumesLocked(Handle);
            if (Velocity.SizeSquared() > FMath::Square(Limit))
                FPhysicsInterface::SetLinearVelocity_AssumesLocked(Handle, Velocity.GetClampedToMaxSize(Limit));
        });
    }
    --Handoff.FramesRemaining;
}

bool IsSettled(const USkeletalMeshComponent* Mesh, float LinearSpeed, float AngularSpeed)
{
    if (!Mesh) return false;
    bool bHasSimulatingBody = false;
    for (const FBodyInstance* Body : Mesh->Bodies)
    {
        if (!Body || !Body->IsInstanceSimulatingPhysics()) continue;
        bHasSimulatingBody = true;
        bool bSlow = false;
        FPhysicsCommand::ExecuteRead(Body->GetPhysicsActorHandle(), [&](const FPhysicsActorHandle& Handle)
        {
            bSlow = FPhysicsInterface::GetLinearVelocity_AssumesLocked(Handle).SizeSquared() <= FMath::Square(LinearSpeed) &&
                FPhysicsInterface::GetAngularVelocity_AssumesLocked(Handle).SizeSquared() <= FMath::Square(AngularSpeed);
        });
        if (!bSlow) return false;
    }
    return bHasSimulatingBody;
}

bool FindGround(const USkeletalMeshComponent* Mesh, FName AnchorBone, FHitResult& Out)
{
    if (!Mesh || !Mesh->GetWorld()) return false;
    const FVector At = BoneWorldTransform(Mesh, AnchorBone).GetLocation();
    float Reach = 65.f;
    if (const auto* Body = Mesh->GetBodyInstance(AnchorBone); Body && Body->IsInstanceSimulatingPhysics())
    {
        const FBox Bounds = Body->GetBodyBounds();
        if (Bounds.IsValid) Reach = FMath::Max(Reach, static_cast<float>(At.Z - Bounds.Min.Z + 15.f));
    }
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    return Mesh->GetWorld()->LineTraceSingleByObjectType(Out, At + FVector(0, 0, 15),
        At - FVector(0, 0, Reach + 35.f), Objects,
        FCollisionQueryParams(SCENE_QUERY_STAT(MonsterRagdollGround), false, Mesh->GetOwner())) &&
        Out.ImpactNormal.Z > .35f && At.Z - Out.ImpactPoint.Z <= Reach;
}

bool FindSupport(const USkeletalMeshComponent* Mesh, FHitResult& Out)
{
    if (!Mesh || !Mesh->GetWorld()) return false;
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterRagdollSupport), false, Mesh->GetOwner());
    for (const FBodyInstance* Body : Mesh->Bodies)
    {
        if (!Body || !Body->IsInstanceSimulatingPhysics() || Body->GetCollisionEnabled() == ECollisionEnabled::NoCollision) continue;
        const FBox Bounds = Body->GetBodyBounds();
        if (!Bounds.IsValid) continue;
        const FVector Bottom(Bounds.GetCenter().X, Bounds.GetCenter().Y, Bounds.Min.Z);
        if (Mesh->GetWorld()->LineTraceSingleByObjectType(Out, Bottom + FVector(0, 0, 6),
            Bottom - FVector(0, 0, 6), Objects, Query) && Out.ImpactNormal.Z > .5f &&
            FMath::Abs(Bottom.Z - Out.ImpactPoint.Z) <= 2.f) return true;
    }
    return false;
}

void RelaxJointDrives(USkeletalMeshComponent* Mesh)
{
    if (!Mesh) return;
    for (FConstraintInstance* Joint : Mesh->Constraints)
    {
        if (!Joint) continue;
        // Preserve anatomical frames and limits. A dead body has no motor
        // trying to keep its cast/attack pose or stop its gravity-driven rotation.
        Joint->SetOrientationDriveTwistAndSwing(false, false);
        Joint->SetOrientationDriveSLERP(false);
        Joint->SetAngularVelocityDriveTwistAndSwing(false, false);
        Joint->SetAngularVelocityDriveSLERP(false);
        Joint->SetLinearPositionDrive(false, false, false);
        Joint->SetLinearVelocityDrive(false, false, false);
    }
}

void GroundAnimatedPose(USkeletalMeshComponent* Mesh)
{
    if (!Mesh || !Mesh->GetWorld() || Mesh->IsSimulatingPhysics()) return;
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Mesh->UpdateKinematicBonesToAnim(Mesh->GetComponentSpaceTransforms(), ETeleportType::TeleportPhysics,
        false, EAllowKinematicDeferral::DisallowDeferral);
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterAnimatedCorpseGround), false, Mesh->GetOwner());
    double Gap = TNumericLimits<double>::Max();
    for (const FBodyInstance* Body : Mesh->Bodies)
    {
        if (!Body || !Body->IsValidBodyInstance() || Body->GetCollisionEnabled() == ECollisionEnabled::NoCollision) continue;
        if (Body->BodySetup.IsValid())
        {
            const FString Name = Body->BodySetup->BoneName.ToString().ToLower();
            // The budget fallback has not run AlignContainerRoot/TunePhysics.
            // Its tiny unskinned helper must not hold the visible corpse up.
            if (Name.EndsWith(TEXT("root")) || Name == TEXT("armature")) continue;
        }
        const FBox Bounds = Body->GetBodyBounds();
        if (!Bounds.IsValid) continue;
        const FVector Bottom(Bounds.GetCenter().X, Bounds.GetCenter().Y, Bounds.Min.Z);
        FHitResult Floor;
        if (Mesh->GetWorld()->LineTraceSingleByObjectType(Floor, Bottom + FVector(0, 0, 25),
            Bottom - FVector(0, 0, 100), Objects, Query) && Floor.ImpactNormal.Z > .5f)
            Gap = FMath::Min(Gap, Bottom.Z - Floor.ImpactPoint.Z - .5);
    }
    if (Gap != TNumericLimits<double>::Max())
        Mesh->AddWorldOffset(FVector(0, 0, FMath::Clamp(-Gap, -80., 20.)), false, nullptr, ETeleportType::TeleportPhysics);
}

void CapturePose(USkeletalMeshComponent* Mesh, FPoseSnapshot& Out)
{
    if (!Mesh || !Mesh->GetSkeletalMeshAsset()) { Out.Reset(); return; }
    Mesh->SnapshotPose(Out);
    const auto& Ref = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    TArray<FTransform> WorldPose;
    WorldPose.SetNum(Out.LocalTransforms.Num());
    for (int32 Index = 0; Index < Out.LocalTransforms.Num(); ++Index)
    {
        const int32 Parent = Ref.GetParentIndex(Index);
        const FTransform ParentWorld = Parent == INDEX_NONE ? Mesh->GetComponentTransform() : WorldPose[Parent];
        WorldPose[Index] = Out.LocalTransforms[Index] * ParentWorld;
        FMonsterRagdollBodyState Physical;
        if (ReadBody(Mesh, Out.BoneNames[Index], Physical))
        {
            // Physics has rigid unit scale. Retain the skeletal scale chain (e.g. Slag's
            // root x100), while using current body translation/rotation in world space.
            WorldPose[Index].SetLocation(Physical.WorldTransform.GetLocation());
            WorldPose[Index].SetRotation(Physical.WorldTransform.GetRotation());
            Out.LocalTransforms[Index] = WorldPose[Index].GetRelativeTransform(ParentWorld);
        }
    }
}

void RebasePose(FPoseSnapshot& Pose, const FTransform& OldMeshWorld, const FTransform& NewMeshWorld)
{
    if (Pose.bIsValid && !Pose.LocalTransforms.IsEmpty())
        Pose.LocalTransforms[0] = Pose.LocalTransforms[0] * OldMeshWorld * NewMeshWorld.Inverse();
}
}
