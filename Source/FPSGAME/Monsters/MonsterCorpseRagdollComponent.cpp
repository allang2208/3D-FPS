#include "MonsterCorpseRagdollComponent.h"
#include "MonsterCorpsePoseAnimInstance.h"
#include "HumanoidRagdollBudget.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/ConstraintInstance.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

UMonsterCorpseRagdollComponent::UMonsterCorpseRagdollComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

FName UMonsterCorpseRagdollComponent::SelectAnchor(USkeletalMeshComponent* Mesh) const
{
    if (!Mesh || !Mesh->GetSkeletalMeshAsset() || !Mesh->GetPhysicsAsset()) return NAME_None;
    if (Rig == EMonsterCorpseRig::HangingBell && Mesh->GetBodyInstance(TEXT("spine_01"))) return TEXT("spine_01");
    if (Rig == EMonsterCorpseRig::Maggot && Mesh->GetBodyInstance(TEXT("body_04"))) return TEXT("body_04");
    if (Rig == EMonsterCorpseRig::HandBrain && Mesh->GetBodyInstance(TEXT("base"))) return TEXT("base");
    if (Rig == EMonsterCorpseRig::FleshHand && Mesh->GetBodyInstance(TEXT("palm"))) return TEXT("palm");
    if (Rig == EMonsterCorpseRig::Mawcrawler && Mesh->GetBodyInstance(TEXT("body_center"))) return TEXT("body_center");
    // The Wolf and Meshy canine families have different bone names and bind poses.
    for (const auto& Setup : Mesh->GetPhysicsAsset()->SkeletalBodySetups)
        if (Setup && Mesh->GetBodyInstance(Setup->BoneName))
        {
            const FString Name = Setup->BoneName.ToString().ToLower();
            if (Name.Contains(TEXT("pelvis")) || Name == TEXT("hips") || Name == TEXT("hip")) return Setup->BoneName;
        }
    const FName Root = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton().GetBoneName(0);
    FName Largest;
    float LargestMass = -1.f;
    for (const auto& Setup : Mesh->GetPhysicsAsset()->SkeletalBodySetups)
        if (Setup && Setup->BoneName != Root)
            if (const auto* Body = Mesh->GetBodyInstance(Setup->BoneName); Body && Body->IsValidBodyInstance())
                if (Body->GetBodyMass() > LargestMass) { LargestMass = Body->GetBodyMass(); Largest = Setup->BoneName; }
    return Largest.IsNone() && Mesh->GetBodyInstance(Root) ? Root : Largest;
}

void UMonsterCorpseRagdollComponent::PrepareDeath(USkeletalMeshComponent* Mesh)
{
    BodyMesh = Mesh;
    if (Mesh && Rig == EMonsterCorpseRig::FleshHand)
        if (auto* Asset = LoadObject<UPhysicsAsset>(nullptr,
            TEXT("/Game/Monsters/FleshHand/PA_FleshHand_Corpse.PA_FleshHand_Corpse")))
            Mesh->SetPhysicsAsset(Asset);
    AnchorBone = SelectAnchor(Mesh);
    InheritedVelocity = GetOwner()->GetVelocity().GetClampedToMaxSize(600.f);
    if (Mesh && !AnchorBone.IsNone())
    {
        PreviousAnchor = Mesh->GetSocketTransform(AnchorBone);
        bHavePreviousPose = true;
    }
}

void UMonsterCorpseRagdollComponent::RecordDeathPose(USkeletalMeshComponent* Mesh, float DeltaSeconds, bool bPoseAlreadyEvaluated)
{
    if (!Mesh || bAttempted) return;
    if (AnchorBone.IsNone()) PrepareDeath(Mesh);
    // The actor's external death clock has just sampled its current source pose.
    if (!bPoseAlreadyEvaluated)
    {
        Mesh->TickAnimation(0.f, false);
        Mesh->RefreshBoneTransforms();
    }
    const FTransform Current = Mesh->GetSocketTransform(AnchorBone);
    if (bHavePreviousPose && DeltaSeconds > UE_SMALL_NUMBER)
    {
        PoseVelocity = (Current.GetLocation() - PreviousAnchor.GetLocation()) / DeltaSeconds;
        FQuat Delta = Current.GetRotation() * PreviousAnchor.GetRotation().Inverse();
        Delta.Normalize();
        if (Delta.W < 0.f) Delta = FQuat(-Delta.X, -Delta.Y, -Delta.Z, -Delta.W);
        FVector Axis; float Angle;
        Delta.ToAxisAndAngle(Axis, Angle);
        PoseAngularVelocity = Axis * (Angle / DeltaSeconds);
    }
    PreviousAnchor = Current;
    bHavePreviousPose = true;
}

bool UMonsterCorpseRagdollComponent::Start(USkeletalMeshComponent* Mesh, const FVector& ImpactVelocity)
{
    if (bAttempted || !GetOwner()->HasAuthority()) return false;
    bAttempted = true;
    BodyMesh = Mesh;
    if (!Mesh || !Mesh->GetPhysicsAsset()) return false;
    const auto PreviousCollision = Mesh->GetCollisionEnabled();
    // The death lead can remove the query bodies. Create them before choosing
    // an anchor or reserving a budget, as in the accepted Witch handoff.
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    AnchorBone = SelectAnchor(Mesh);
    const auto* Anchor = AnchorBone.IsNone() ? nullptr : Mesh->GetBodyInstance(AnchorBone);
    if (!Anchor || !Anchor->IsValidBodyInstance())
    { Mesh->SetCollisionEnabled(PreviousCollision); return false; }
    if (Rig == EMonsterCorpseRig::FleshHand && Mesh->GetPhysicsAsset()->ConstraintSetup.IsEmpty())
    { Mesh->SetCollisionEnabled(PreviousCollision); return false; }
    PhysicsBodyCount = Mesh->GetPhysicsAsset()->SkeletalBodySetups.Num();
    auto* Budget = GetWorld()->GetSubsystem<UHumanoidRagdollBudget>();
    if (!Budget || !Budget->Acquire(this, PhysicsBodyCount, true))
    { Mesh->SetCollisionEnabled(PreviousCollision); return false; }
    bBudgetOwned = true;

    Mesh->SetComponentTickEnabled(true);
    Mesh->SetForcedLOD(1);
    Mesh->KinematicBonesUpdateType = EKinematicBonesUpdateToPhysics::SkipSimulatingBones;
    Mesh->TickAnimation(0.f, false);
    Mesh->RefreshBoneTransforms();
    Mesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Mesh->SetCollisionProfileName(TEXT("Ragdoll"));
    Mesh->SetCollisionObjectType(ECC_Pawn);
    Mesh->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    Mesh->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Mesh->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);
    Mesh->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Block);
    Mesh->UpdateKinematicBonesToAnim(Mesh->GetComponentSpaceTransforms(), ETeleportType::TeleportPhysics,
        false, EAllowKinematicDeferral::DisallowDeferral);
    AlignRootAndTune();
    Mesh->SetEnableGravity(true);
    Mesh->bPauseAnims = true;
    Mesh->bUpdateJointsFromAnimation = false;
    Mesh->KinematicBonesUpdateType = EKinematicBonesUpdateToPhysics::SkipAllBones;
    Mesh->SetAllBodiesSimulatePhysics(true);
    Mesh->SetSimulatePhysics(true);
    Mesh->SetAllBodiesPhysicsBlendWeight(1.f);

    FVector Velocity = (PoseVelocity + InheritedVelocity * .4f + ImpactVelocity).GetClampedToMaxSize(450.f);
    Velocity.Z = FMath::Clamp(Velocity.Z, -350., 0.);
    MonsterRagdollPhysics::BeginHandoff(Mesh, AnchorBone, Velocity,
        PoseAngularVelocity.GetClampedToMaxSize(3.f), Handoff);
    bSimulating = true;
    PhysicsAge = ProbeAge = StableAge = 0.f;
    AddTickPrerequisiteComponent(Mesh);
    SetComponentTickEnabled(true);
    // The active component owns corpse updates; the actor's attack clock is finished.
    GetOwner()->SetActorTickEnabled(false);
    return true;
}

void UMonsterCorpseRagdollComponent::AlignRootAndTune()
{
    const auto& Ref = BodyMesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    const FName Root = Ref.GetBoneName(0);
    FName RootAnchor = AnchorBone;
    if (Rig == EMonsterCorpseRig::Maggot) RootAnchor = TEXT("body_00");
    else if (Root != AnchorBone)
        for (const FConstraintInstance* Joint : BodyMesh->Constraints)
        {
            if (!Joint) continue;
            if (Joint->ConstraintBone2 == Root) { RootAnchor = Joint->ConstraintBone1; break; }
            if (Joint->ConstraintBone1 == Root) { RootAnchor = Joint->ConstraintBone2; break; }
        }
    FName Helper = MonsterRagdollPhysics::ContainerRoot(BodyMesh, RootAnchor);
    // The custom rigs already use a non-contact "root" body, even when the FBX
    // adds another container above it. Retain that existing collision contract.
    if (Helper.IsNone() && (Rig == EMonsterCorpseRig::Maggot || Rig == EMonsterCorpseRig::HandBrain || Rig == EMonsterCorpseRig::Mawcrawler || Rig == EMonsterCorpseRig::HangingBell) &&
        BodyMesh->GetBodyInstance(TEXT("root"))) Helper = TEXT("root");
    MonsterRagdollPhysics::AlignContainerRoot(BodyMesh, RootAnchor);
    const float LinearDamping = Rig == EMonsterCorpseRig::HangingBell ? 1.2f : Rig == EMonsterCorpseRig::Maggot ? .6f : .25f;
    const float AngularDamping = Rig == EMonsterCorpseRig::HangingBell ? 2.5f : Rig == EMonsterCorpseRig::Maggot ? 1.8f : Rig == EMonsterCorpseRig::HandBrain ? 1.2f : .9f;
    float OriginalMass = 0.f;
    if (Rig == EMonsterCorpseRig::FleshHand)
        for (const auto* Body : BodyMesh->Bodies)
            if (Body && Body->IsValidBodyInstance()) OriginalMass += Body->GetBodyMass();
    for (const auto& Setup : BodyMesh->GetPhysicsAsset()->SkeletalBodySetups)
    {
        if (!Setup) continue;
        auto* Body = BodyMesh->GetBodyInstance(Setup->BoneName);
        if (!Body || !Body->IsValidBodyInstance()) continue;
        if (Setup->BoneName == Helper) { Body->SetCollisionEnabled(ECollisionEnabled::NoCollision); continue; }
        if (Rig == EMonsterCorpseRig::FleshHand && OriginalMass > UE_SMALL_NUMBER)
            Body->SetMassOverride(25.f * FMath::Pow(float(BodyMesh->GetComponentScale().GetAbsMax()), 3.f) *
                Body->GetBodyMass() / OriginalMass, true);
        Body->SetUseCCD(true);
        Body->LinearDamping = LinearDamping;
        Body->AngularDamping = AngularDamping;
        Body->UpdateDampingProperties();
        Body->SetMaxAngularVelocityInRadians(10.f, false);
        Body->SetMaxDepenetrationVelocity(80.f);
        Body->SetPositionSolverIterationCount(FMath::Max<uint8>(8, Body->PositionSolverIterationCount));
        Body->SetVelocitySolverIterationCount(FMath::Max<uint8>(2, Body->VelocitySolverIterationCount));
    }
    // Keep each species' anatomical frames and angular limits. Only the helper root
    // is reconnected; projection must not teleport a heavy/wide corpse through terrain.
    for (FConstraintInstance* Joint : BodyMesh->Constraints)
        if (Joint) { Joint->DisableProjection(); Joint->SetShockPropagationParams(false, Joint->GetShockPropagationAlpha()); }
    MonsterRagdollPhysics::RelaxJointDrives(BodyMesh);
}

void UMonsterCorpseRagdollComponent::TickComponent(float DeltaSeconds, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaSeconds, TickType, TickFunction);
    if (!bSimulating || !BodyMesh) return;
    PhysicsAge += DeltaSeconds;
    MonsterRagdollPhysics::LimitHandoffSpeed(BodyMesh, Handoff, DeltaSeconds);
    ProbeAge += DeltaSeconds;
    if (ProbeAge < .1f) return;
    const float ProbeDelta = ProbeAge;
    ProbeAge = 0.f;
    bGrounded = false;
    FHitResult Ground;
    bGrounded = MonsterRagdollPhysics::FindSupport(BodyMesh, Ground);
    const bool bStable = bGrounded && MonsterRagdollPhysics::IsSettled(BodyMesh, 10.f, .3f);
    StableAge = bStable ? StableAge + ProbeDelta : 0.f;
    if (PhysicsAge >= FMath::Max(1.2f, MinimumPhysicsSeconds) && StableAge >= FMath::Max(.5f, StableSeconds)) FreezePose(true);
}

bool UMonsterCorpseRagdollComponent::CanReleaseCorpseBudget() const
{
    return bSimulating && bGrounded && PhysicsAge >= FMath::Max(1.2f, MinimumPhysicsSeconds) && StableAge >= FMath::Max(.5f, StableSeconds);
}
void UMonsterCorpseRagdollComponent::FreezeForBudget()
{
    if (CanReleaseCorpseBudget()) FreezePose(true);
}
void UMonsterCorpseRagdollComponent::FreezeAnimatedPose(USkeletalMeshComponent* Mesh)
{
    if (bSimulating || bFrozen || !GetOwner()->HasAuthority()) return;
    BodyMesh = Mesh;
    if (!Mesh) return;
    Mesh->SetForcedLOD(1);
    Mesh->TickAnimation(0.f, false);
    Mesh->RefreshBoneTransforms();
    MonsterRagdollPhysics::GroundAnimatedPose(Mesh);
    FreezePose(false);
}

void UMonsterCorpseRagdollComponent::FreezePose(bool bFromPhysics)
{
    if (!BodyMesh || bFrozen) return;
    if (bFromPhysics) MonsterRagdollPhysics::CapturePose(BodyMesh, FrozenPose);
    else BodyMesh->SnapshotPose(FrozenPose);
    if (!FrozenPose.bIsValid) return;
    if (bFromPhysics)
    {
        BodyMesh->PutAllRigidBodiesToSleep();
        BodyMesh->SetSimulatePhysics(false);
        BodyMesh->SetAllBodiesSimulatePhysics(false);
        BodyMesh->SetAllBodiesPhysicsBlendWeight(0.f);
    }
    BodyMesh->KinematicBonesUpdateType = EKinematicBonesUpdateToPhysics::SkipSimulatingBones;
    BodyMesh->bPauseAnims = false;
    BodyMesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    BodyMesh->SetAnimInstanceClass(UMonsterCorpsePoseAnimInstance::StaticClass());
    CastChecked<UMonsterCorpsePoseAnimInstance>(BodyMesh->GetAnimInstance())->HoldPose(FrozenPose);
    BodyMesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    BodyMesh->SetCollisionObjectType(ECC_Pawn);
    BodyMesh->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    BodyMesh->TickAnimation(0.f, false);
    BodyMesh->RefreshBoneTransforms();
    Handoff.FramesRemaining = 0;
    bSimulating = false;
    bFrozen = true;
    ReleaseBudget();
    SetComponentTickEnabled(false);
    MonsterRagdollPhysics::RetireCorpseTicks(BodyMesh);
}

void UMonsterCorpseRagdollComponent::ReleaseBudget()
{
    if (!bBudgetOwned) return;
    if (auto* World = GetWorld())
        if (auto* Budget = World->GetSubsystem<UHumanoidRagdollBudget>()) Budget->Release(this);
    bBudgetOwned = false;
}
void UMonsterCorpseRagdollComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    ReleaseBudget();
    Super::EndPlay(Reason);
}
