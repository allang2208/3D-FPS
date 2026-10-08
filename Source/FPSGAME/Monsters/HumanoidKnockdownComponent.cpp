#include "HumanoidKnockdownComponent.h"
#include "HumanoidRagdollBudget.h"
#include "NurseZombie.h"
#include "WitchRebuiltMonster.h"
#include "FatZombieAnimInstance.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/ConstraintInstance.h"

UHumanoidKnockdownComponent::UHumanoidKnockdownComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
}
ANurseZombie* UHumanoidKnockdownComponent::Humanoid() const { return Cast<ANurseZombie>(GetOwner()); }
USkeletalMeshComponent* UHumanoidKnockdownComponent::BodyMesh() const { return Humanoid()?Humanoid()->GetMesh():nullptr; }
bool UHumanoidKnockdownComponent::IsControlling() const { return !bCorpse && Phase!=EHumanoidKnockdownPhase::None; }
bool UHumanoidKnockdownComponent::GetRecoverySupport(FVector& Point,FVector& Normal) const
{
    if (bCorpse || Phase!=EHumanoidKnockdownPhase::GettingUp) return false;
    Point=RecoveryFloorPoint; Normal=RecoveryFloorNormal;
    return true;
}

void UHumanoidKnockdownComponent::OffsetRecoverySupport(const FVector& Delta)
{
    if(!bCorpse&&Phase==EHumanoidKnockdownPhase::GettingUp)RecoveryFloorPoint+=Delta;
}

void UHumanoidKnockdownComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* N=Humanoid(); auto* Mesh=BodyMesh();
    if (!N || !Mesh || !Mesh->GetSkeletalMeshAsset()) return;
    const FString Role=N->ActorHasTag(TEXT("WitchRebuilt"))?TEXT("Witch"):
        N->ActorHasTag(TEXT("Mutant3"))?TEXT("Mutant3"):
        N->ActorHasTag(TEXT("FatZombie"))?TEXT("FatZombie"):TEXT("Nurse");
    auto Load=[&](const TCHAR* Suffix)
    {
        const FString Name=TEXT("A_")+Role+TEXT("_")+Suffix;
        return LoadObject<UAnimSequence>(nullptr,*(TEXT("/Game/Monsters/HumanoidKnockdown/")+Role+TEXT("/")+Name+TEXT(".")+Name));
    };
    if (!FallClip) FallClip=Load(TEXT("Hit_Knockback"));
    if (!GetUpClip) GetUpClip=Load(TEXT("LayToIdle"));
    if (!ProneGetUpClip) ProneGetUpClip=Load(TEXT("ProneToIdle"));
    // The legacy Witch uses a different skeleton. Never apply the rebuilt rig to it.
    if (GetUpClip && GetUpClip->GetSkeleton()!=Mesh->GetSkeletalMeshAsset()->GetSkeleton())
    { FallClip=nullptr; GetUpClip=nullptr; ProneGetUpClip=nullptr; }
    PelvisBone=Mesh->GetBoneIndex(TEXT("Hips"))!=INDEX_NONE?TEXT("Hips"):TEXT("pelvis");
    HeadBone=Mesh->GetBoneIndex(TEXT("Head"))!=INDEX_NONE?TEXT("Head"):TEXT("head");
    if (Role==TEXT("FatZombie")) { LaunchScale=.68f; GetUpRate=.65f; }
    else if (Role==TEXT("Mutant3")) { LaunchScale=.85f; GetUpRate=1.1f; }
    else if (Role==TEXT("Witch")) { GetUpRate=.8f; bGroundCorpseFeet=true; }
    const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    const int32 Index=Ref.FindBoneIndex(PelvisBone);
    if (Index!=INDEX_NONE)
    {
        FTransform Rest=Ref.GetRefBonePose()[Index];
        for (int32 P=Ref.GetParentIndex(Index);P!=INDEX_NONE;P=Ref.GetParentIndex(P)) Rest*=Ref.GetRefBonePose()[P];
        const FVector Front=Mesh->GetComponentTransform().InverseTransformVectorNoScale(N->GetActorForwardVector());
        PelvisLocalFront=Rest.InverseTransformVectorNoScale(Front).GetSafeNormal();
    }
}

void UHumanoidKnockdownComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (auto* Budget=GetWorld()->GetSubsystem<UHumanoidRagdollBudget>()) Budget->Release(this);
    Super::EndPlay(Reason);
}

void UHumanoidKnockdownComponent::RememberStandingState()
{
    if (bSavedStanding) return;
    auto* N=Humanoid(); auto* Mesh=BodyMesh();
    StandingMeshRelative=Mesh->GetRelativeTransform();
    StandingAnimClass=Mesh->GetAnimClass();
    StandingResponses=Mesh->GetCollisionResponseToChannels();
    StandingMeshCollision=Mesh->GetCollisionEnabled();
    StandingObjectType=Mesh->GetCollisionObjectType();
    StandingCapsuleCollision=N->GetCapsuleComponent()->GetCollisionEnabled();
    StandingLOD=Mesh->GetForcedLOD();
    bStandingUpdateJointsFromAnimation=Mesh->bUpdateJointsFromAnimation;
    StandingRadius=N->GetCapsuleComponent()->GetUnscaledCapsuleRadius();
    StandingHalfHeight=N->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight();
    StandingPawnResponse=N->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Pawn);
    StandingAirControl=N->GetCharacterMovement()->AirControl;
    bStandingOrientToMovement=N->GetCharacterMovement()->bOrientRotationToMovement;
    bStandingNavUpdate=N->GetCharacterMovement()->ShouldUpdateNavAgentWithOwnersCollision();
    MonsterObstacleCollision::BuildProbes(Mesh,ObstacleProbes);
    ClipObstacleCache.Reset();
    RecoveryFacingIndex=0; NextRecoveryProbe=0;
    bSavedStanding=true;
}

UFatZombieAnimInstance* UHumanoidKnockdownComponent::PosePlayer()
{
    auto* Mesh=BodyMesh();
    if (!Cast<UFatZombieAnimInstance>(Mesh->GetAnimInstance())) Mesh->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
    return Cast<UFatZombieAnimInstance>(Mesh->GetAnimInstance());
}

bool UHumanoidKnockdownComponent::Launch(APawn* InstigatorPawn, FVector Velocity, float DownSeconds, bool bForced)
{
    auto* N=Humanoid(); auto* Mesh=BodyMesh();
    if (!N || !N->HasAuthority() || !bEnabled || N->State==ENurseState::Dead || !FallClip || !GetUpClip ||
        (!bForced&&(N->ActorHasTag(TEXT("KnockdownImmune")) || N->ActorHasTag(TEXT("KnockbackImmune"))))) return false;
    if(N->Combat&&!N->Combat->CanReceiveLaunchOrKnockdown())return false;
    const bool bAlreadyDown=Phase==EHumanoidKnockdownPhase::Downed;
    const bool bHadStandingState=bSavedStanding;
    RememberStandingState();
    // Reserve physics or safe animation space before interrupting gameplay. In a
    // tight corner, keep the caller's ordinary swept knockback instead of forcing
    // a horizontal body through a wall when the ragdoll budget is full.
    if (!AcquirePhysicsBudget() && (!bAlreadyDown||bForced) && !PrepareAnimatedCapsule())
    { if (!bHadStandingState) bSavedStanding=false; return false; }
    // Let the existing interruption hook cancel special attacks before physics takes ownership.
    if (!IsControlling()) N->InterruptAttack(.1f);
    N->State=ENurseState::KnockedDown; N->bAttackConsumed=true; N->StateTime=0;
    N->Cooldown=FMath::Max(N->Cooldown,.6f);
    if (auto* AI=Cast<AMonsterAIController>(N->GetController()))
    { AI->StopMovement(); AI->RememberDamage(InstigatorPawn); AI->UpdateKnowledge(); }
    auto* Move=N->GetCharacterMovement();
    Move->StopMovementImmediately(); Move->ClearAccumulatedForces(); Move->DisableMovement();
    bCorpse=false;
    ControlUntil=FMath::Max(ControlUntil,GetWorld()->GetTimeSeconds()+FMath::Max(GroundHoldSeconds,DownSeconds));
    FVector Horizontal(Velocity.X,Velocity.Y,0);
    Horizontal=Horizontal.GetClampedToMaxSize(700.f)*LaunchScale;
    Velocity=Horizontal+FVector(0,0,FMath::Clamp(Velocity.Z,0.f,500.f)*FMath::Sqrt(LaunchScale));
    if (auto* Witch=Cast<AWitchRebuiltMonster>(N)) Witch->UseKnockdownPresentation();
    Mesh->SetComponentTickEnabled(true); Mesh->SetForcedLOD(1);
    if (!StartPhysics(Velocity))
    {
        if (bAlreadyDown&&!bForced) { Phase=EHumanoidKnockdownPhase::Downed;return true; }
        // Same control and recovery contract when the solver budget is exhausted.
        RestoreCollision(); ApplyAnimatedCapsule();
        Move->SetMovementMode(MOVE_Falling); N->LaunchCharacter(Velocity,true,true);
        StartAnimatedFall(FallClip,0.f);
    }
    SetComponentTickEnabled(true); SetComponentTickInterval(0.f);
    return true;
}

void UHumanoidKnockdownComponent::ExtendControl(float Seconds)
{
    if (!IsControlling()) return;
    ControlUntil=FMath::Max(ControlUntil,GetWorld()->GetTimeSeconds()+FMath::Max(0.f,Seconds));
}

bool UHumanoidKnockdownComponent::OnDeath()
{
    const bool bWasControlled=IsControlling();
    bCorpse=true;
    FMonsterRagdollBodyState PreviousBody;
    const bool bHadPhysicalPose=MonsterRagdollPhysics::ReadBody(BodyMesh(),PelvisBone,PreviousBody);
    auto* Witch=Cast<AWitchRebuiltMonster>(GetOwner());
    if (bWasControlled && Witch) Witch->ReleaseStaffOnDeath();
    const bool bChangedCorpseMesh=Witch && Witch->UseCorpsePresentation();
    if (!bWasControlled) return false;
    if (Phase==EHumanoidKnockdownPhase::Physics)
    {
        // The physical body continues from its exact state; do not replay a standing death.
        if (bChangedCorpseMesh)
        {
            StartPhysics(bHadPhysicalPose?PreviousBody.LinearVelocity:FVector::ZeroVector);
            if (bHadPhysicalPose) MonsterRagdollPhysics::BeginHandoff(BodyMesh(),PelvisBone,
                PreviousBody.LinearVelocity,PreviousBody.AngularVelocity,PhysicsHandoff);
        }
        // Reuse the current velocity/pose while removing the live joint motors.
        // Death during a knockdown must receive the same passive tuning as a
        // standing death, without starting the handoff again.
        TunePhysics();
        PhaseAge=0; StableAge=0; return true;
    }
    if (Phase==EHumanoidKnockdownPhase::Downed)
    {
        if (StartPhysics(FVector::ZeroVector))
        { SetComponentTickEnabled(true); SetComponentTickInterval(0.f); return true; }
        FreezeCorpse(); return true;
    }
    if (!StartPhysics(FVector::ZeroVector))
    {
        // The capsule still falls under gravity for an airborne animation fallback.
        Humanoid()->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Humanoid()->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
        if (Phase==EHumanoidKnockdownPhase::GettingUp) StartAnimatedFall(FallClip,0.f);
    }
    return true;
}

FTransform UHumanoidKnockdownComponent::ClipBone(UAnimSequence* Clip, FName Bone, float Time) const
{
    FTransform Out=FTransform::Identity;
    if (!Clip || !Clip->GetSkeleton()) return Out;
    const auto& Ref=Clip->GetSkeleton()->GetReferenceSkeleton();
    for (int32 I=Ref.FindBoneIndex(Bone);I!=INDEX_NONE;I=Ref.GetParentIndex(I))
    {
        FTransform Local;
        Clip->GetBoneTransform(Local,FSkeletonPoseBoneIndex(I),FAnimExtractContext(double(Time),false),false);
        Out*=Local;
    }
    return Out;
}

void UHumanoidKnockdownComponent::StartDeath(UAnimSequence* DeathClip, float ClipTime)
{
    if (!Humanoid() || !Humanoid()->HasAuthority()) return;
    RememberStandingState(); bCorpse=true;
    auto* Mesh=BodyMesh();
    Mesh->SetComponentTickEnabled(true); Mesh->SetForcedLOD(1);
    Mesh->TickAnimation(0.f,false); Mesh->RefreshBoneTransforms();
    FVector FallVelocity=FVector::ZeroVector;
    if (DeathClip && ClipTime>.001f)
    {
        // Start the connected body with one fall velocity. Independent sampled
        // bone velocities fight the locked joints, especially the container root.
        const float Before=FMath::Max(0.f,ClipTime-1.f/30.f);
        const FVector Local=(ClipBone(DeathClip,PelvisBone,ClipTime).GetLocation()-
            ClipBone(DeathClip,PelvisBone,Before).GetLocation())/FMath::Max(.001f,ClipTime-Before);
        FallVelocity=Mesh->GetComponentTransform().TransformVector(Local).GetClampedToMaxSize(350.f);
        // A standing death must not inherit an upward animation correction.
        // Death during an existing physical launch is handled unchanged by OnDeath.
        FallVelocity.Z=FMath::Min(0.,FallVelocity.Z);
    }
    if (!StartPhysics(FallVelocity))
    {
        StartAnimatedFall(DeathClip?DeathClip:FallClip.Get(),DeathClip?ClipTime:0.f);
        if (!DeathClip && FallClip) FallStopTime=FallClip->GetPlayLength()*.5f;
        Humanoid()->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Humanoid()->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    }
    SetComponentTickEnabled(true); SetComponentTickInterval(0.f);
}

bool UHumanoidKnockdownComponent::AcquirePhysicsBudget()
{
    auto* Mesh=BodyMesh();
    const auto* Asset=Mesh->GetPhysicsAsset();
    const auto* Anchor=Mesh->GetBodyInstance(PelvisBone);
    if (!Asset || Asset->SkeletalBodySetups.IsEmpty() || !Anchor || !Anchor->IsValidBodyInstance()) return false;
    PhysicsBodyCount=Asset->SkeletalBodySetups.Num();
    if (!bBudgetOwned)
    {
        auto* Budget=GetWorld()->GetSubsystem<UHumanoidRagdollBudget>();
        if (!Budget || !Budget->Acquire(this,PhysicsBodyCount,bCorpse)) return false;
        bBudgetOwned=true;
    }
    return true;
}

bool UHumanoidKnockdownComponent::StartPhysics(const FVector& Velocity)
{
    auto* N=Humanoid(); auto* Mesh=BodyMesh();
    // Witch's death animation disables collision, which destroys articulated
    // bodies. Recreate them before checking the physical pelvis for admission.
    const ECollisionEnabled::Type PreviousCollision=Mesh->GetCollisionEnabled();
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    if (!AcquirePhysicsBudget())
    {
        Mesh->SetCollisionEnabled(PreviousCollision);
        UE_LOG(LogTemp,Display,TEXT("MONSTER_RAGDOLL_FALLBACK %s corpse=%d asset=%s pelvis_body=%d"),
            *N->GetName(),bCorpse,*GetNameSafe(Mesh->GetPhysicsAsset()),Mesh->GetBodyInstance(PelvisBone)!=nullptr);
        return false;
    }
    const bool bStartingSimulation=!Mesh->IsSimulatingPhysics();
    Mesh->SetComponentTickEnabled(true); Mesh->SetForcedLOD(1);
    if (bStartingSimulation)
    {
        Mesh->KinematicBonesUpdateType=EKinematicBonesUpdateToPhysics::SkipSimulatingBones;
        Mesh->TickAnimation(0.f,false); Mesh->RefreshBoneTransforms();
    }
    Mesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    RestoreAnimatedCapsule();
    N->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetCollisionProfileName(TEXT("Ragdoll"));
    // Keep Pawn object queries (spells) and Visibility traces (weapons) working while down.
    Mesh->SetCollisionObjectType(ECC_Pawn);
    Mesh->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
    Mesh->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);
    Mesh->SetCollisionResponseToChannel(ECC_WorldDynamic,ECR_Block);
    Mesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    if (bStartingSimulation)
    {
        // Flush the actual handoff pose before making the bodies dynamic. A
        // deferred kinematic target can otherwise leave physics on an older pose.
        Mesh->UpdateKinematicBonesToAnim(Mesh->GetComponentSpaceTransforms(),
            ETeleportType::TeleportPhysics,false,EAllowKinematicDeferral::DisallowDeferral);
        MonsterRagdollPhysics::AlignContainerRoot(Mesh,PelvisBone);
    }
    // Configure filters and constraints before their first simulation step.
    TunePhysics();
    Mesh->SetEnableGravity(true);
    Mesh->bPauseAnims=true;
    Mesh->bUpdateJointsFromAnimation=false;
    Mesh->KinematicBonesUpdateType=EKinematicBonesUpdateToPhysics::SkipAllBones;
    Mesh->SetAllBodiesSimulatePhysics(true); Mesh->SetSimulatePhysics(true);
    Mesh->SetAllBodiesPhysicsBlendWeight(1.f);
    const FVector AngularVelocity=bCorpse?FVector::ZeroVector:
        FVector::CrossProduct(FVector::UpVector,Velocity.GetSafeNormal2D())*1.5f;
    MonsterRagdollPhysics::BeginHandoff(Mesh,PelvisBone,Velocity,AngularVelocity,PhysicsHandoff);
    if (bCorpse && bGroundCorpseFeet)
        UE_LOG(LogTemp,Display,TEXT("WITCH_CORPSE_PHYSICS %s sim=%d bodies=%d"),
            *N->GetName(),Mesh->IsSimulatingPhysics(PelvisBone),Mesh->Bodies.Num());
    Phase=EHumanoidKnockdownPhase::Physics; PhaseAge=ProbeAge=StableAge=0; bGrounded=false;
    return true;
}

void UHumanoidKnockdownComponent::TunePhysics()
{
    auto* Mesh=BodyMesh();
    const FName Container=MonsterRagdollPhysics::ContainerRoot(Mesh,PelvisBone);
    auto Weight=[](FName Bone)
    {
        const FString S=Bone.ToString().ToLower();
        if (S.Contains(TEXT("root"))) return 2.f;
        if (S==TEXT("pelvis") || S==TEXT("hips")) return 16.f;
        if (S.Contains(TEXT("spine"))) return 10.f;
        if (S.Contains(TEXT("head"))) return 6.f;
        if (S.Contains(TEXT("neck"))) return 1.5f;
        if (S.Contains(TEXT("thigh")) || S.Contains(TEXT("upleg"))) return 9.f;
        if (S.Contains(TEXT("calf")) || S.EndsWith(TEXT("leg"))) return 4.f;
        if (S.Contains(TEXT("hand"))) return 1.f;
        if (S.Contains(TEXT("foot"))) return 2.f;
        if (S.Contains(TEXT("lowerarm")) || S.Contains(TEXT("forearm"))) return 2.f;
        return 3.5f;
    };
    float Sum=0.f;
    for (auto* Body:Mesh->Bodies) if (Body && Body->BodySetup.IsValid()) Sum+=Weight(Body->BodySetup->BoneName);
    const float Mass=Humanoid()->ActorHasTag(TEXT("FatZombie"))?200.f:Humanoid()->ActorHasTag(TEXT("Mutant3"))?100.f:65.f;
    for (auto* Body:Mesh->Bodies)
    {
        if (!Body || !Body->BodySetup.IsValid()) continue;
        const FName Bone=Body->BodySetup->BoneName;
        if (Bone==Container)
            Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        const FString Name=Bone.ToString().ToLower();
        const bool bTorso=Bone==PelvisBone || Name.Contains(TEXT("spine"));
        Body->SetMassOverride(Mass*Weight(Bone)/FMath::Max(1.f,Sum),true);
        const bool bRelaxWitchCorpse=bCorpse && bGroundCorpseFeet;
        Body->LinearDamping=.25f;
        Body->AngularDamping=bGroundCorpseFeet?
            (bRelaxWitchCorpse?(bTorso?1.f:.8f):(bTorso?4.f:2.6f)):(bTorso?1.2f:1.f);
        Body->UpdateDampingProperties();
        Body->SetMaxAngularVelocityInRadians(10.f,false);
        Body->SetMaxDepenetrationVelocity(80.f);
        const bool bConnectedWitchCorpse=bCorpse && bGroundCorpseFeet;
        Body->SetPositionSolverIterationCount(bCorpse?16:8);
        Body->SetVelocitySolverIterationCount(bConnectedWitchCorpse?8:bCorpse?4:2);
        // Fast hands/feet can cross a thin wall or a column edge even when the
        // pelvis remains outside. Include every simulated anatomical body.
        Body->SetUseCCD(Bone!=Container);
    }
    for (FConstraintInstance* Joint:Mesh->Constraints)
    {
        if (!Joint) continue;
        // Keep the anatomical frames and limits authored in the Physics Asset.
        // UE scales their anchor positions during instantiation; rewriting live
        // frames from the imported ref pose discards that scale and pulls limbs in.
        // Dissipate joint rotation without pulling a corpse toward a T pose.
        Joint->SetAngularDriveMode(EAngularDriveMode::TwistAndSwing);
        Joint->SetOrientationDriveTwistAndSwing(false,false);
        const FString ChildName=Joint->ConstraintBone1.ToString().ToLower();
        // A robe is not a reason to retain an upright torso: let gravity settle
        // the entire dead body, instead of damping only its legs less strongly.
        const bool bRelaxWitchCorpse=bCorpse && bGroundCorpseFeet;
        Joint->SetAngularVelocityDriveTwistAndSwing(bGroundCorpseFeet && !bCorpse,bGroundCorpseFeet && !bCorpse);
        Joint->SetAngularVelocityDriveSLERP(false);
        Joint->SetOrientationDriveSLERP(false);
        if (bRelaxWitchCorpse && ChildName.StartsWith(TEXT("spine")))
        {
            Joint->SetAngularSwing1Limit(ACM_Limited,40.f);
            Joint->SetAngularSwing2Limit(ACM_Limited,35.f);
            Joint->SetAngularTwistLimit(ACM_Limited,25.f);
        }
        else if (bRelaxWitchCorpse && ChildName.StartsWith(TEXT("upperarm")))
        {
            // The live casting envelope is too narrow for a relaxed dead arm.
            // Retain joint anchors and let gravity choose the rest orientation.
            Joint->SetAngularSwing1Limit(ACM_Limited,95.f);
            Joint->SetAngularSwing2Limit(ACM_Limited,75.f);
            Joint->SetAngularTwistLimit(ACM_Limited,60.f);
        }
        else if (bRelaxWitchCorpse && ChildName.StartsWith(TEXT("lowerarm")))
        {
            Joint->SetAngularSwing1Limit(ACM_Limited,105.f);
            Joint->SetAngularSwing2Limit(ACM_Limited,12.f);
            Joint->SetAngularTwistLimit(ACM_Limited,20.f);
        }
        else if (bRelaxWitchCorpse && ChildName.StartsWith(TEXT("hand")))
        {
            Joint->SetAngularSwing1Limit(ACM_Limited,35.f);
            Joint->SetAngularSwing2Limit(ACM_Limited,30.f);
            Joint->SetAngularTwistLimit(ACM_Limited,25.f);
        }
        Joint->SetAngularVelocityTarget(FVector::ZeroVector);
        Joint->SetAngularDriveParams(0.f,12.f,500.f);
        // The Witch's corpse asset has anatomical leg hinge frames. A bounded
        // linear correction retains sewn-body connections without projecting
        // limb rotations or forcing an upright reference pose.
        const bool bConnectedWitchCorpse=bCorpse && bGroundCorpseFeet;
        Joint->SetProjectionParams(bConnectedWitchCorpse,bConnectedWitchCorpse?.35f:0.f,0.f,
            bConnectedWitchCorpse?2.f:8.f,bConnectedWitchCorpse?180.f:30.f);
        Joint->SetShockPropagationParams(false,0.f);
    }
}

void UHumanoidKnockdownComponent::StartAnimatedFall(UAnimSequence* Clip, float StartTime)
{
    auto* Mesh=BodyMesh();
    FPoseSnapshot Pose; Mesh->SnapshotPose(Pose);
    Mesh->bPauseAnims=false; Mesh->KinematicBonesUpdateType=EKinematicBonesUpdateToPhysics::SkipSimulatingBones;
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Mesh->SetCollisionObjectType(ECC_Pawn); Mesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    PlayingClip=Clip; ClipStartTime=StartTime;
    FallStopTime=Clip?(bCorpse?Clip->GetPlayLength():Clip->GetPlayLength()*.5f):0.f;
    if (Clip) { PosePlayer()->RecoverFromSnapshot(Clip,Pose,.12f); PosePlayer()->SetCombatTime(StartTime); }
    else PosePlayer()->HoldSnapshot(Pose);
    Phase=EHumanoidKnockdownPhase::AnimatedFall; PhaseAge=ProbeAge=StableAge=0;
}

bool UHumanoidKnockdownComponent::FindGround(FHitResult& Ground) const
{
    if (Phase==EHumanoidKnockdownPhase::Physics)
        return MonsterRagdollPhysics::FindSupport(BodyMesh(),Ground);
    return MonsterRagdollPhysics::FindGround(BodyMesh(),PelvisBone,Ground);
}

void UHumanoidKnockdownComponent::StopPhysicsWithPose()
{
    auto* Mesh=BodyMesh();
    const bool bPhysicalPose=Mesh->IsSimulatingPhysics();
    // The post-physics skeleton may still be a frame behind the solver. Capture
    // simulated bones directly before giving the snapshot player sole ownership.
    MonsterRagdollPhysics::CapturePose(Mesh,FrozenPose);
    Mesh->PutAllRigidBodiesToSleep(); Mesh->SetSimulatePhysics(false); Mesh->SetAllBodiesSimulatePhysics(false);
    Mesh->SetAllBodiesPhysicsBlendWeight(0.f);
    PhysicsHandoff.FramesRemaining=0;
    if (bBudgetOwned) { GetWorld()->GetSubsystem<UHumanoidRagdollBudget>()->Release(this); bBudgetOwned=false; }
    Mesh->KinematicBonesUpdateType=EKinematicBonesUpdateToPhysics::SkipSimulatingBones;
    Mesh->bPauseAnims=false;
    PosePlayer()->HoldSnapshot(FrozenPose);
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Mesh->SetCollisionObjectType(ECC_Pawn);
    Mesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    Mesh->TickAnimation(0.f,false); Mesh->RefreshBoneTransforms();
    if (!bPhysicalPose && !Cast<AWitchRebuiltMonster>(GetOwner()))
    {
        MonsterRagdollPhysics::GroundAnimatedPose(Mesh);
        Mesh->SnapshotPose(FrozenPose);
        PosePlayer()->HoldSnapshot(FrozenPose);
        Mesh->TickAnimation(0.f,false); Mesh->RefreshBoneTransforms();
    }
    if (bCorpse && !bPhysicalPose) if (const auto* Witch=Cast<AWitchRebuiltMonster>(GetOwner()))
    {
        // Only the animation fallback needs procedural grounding. A real
        // physical corpse keeps the solver's contact pose, without a second
        // spine/foot/neck solver rotating it after its rigid bodies stop.
        Witch->GroundCorpsePose(FrozenPose);
        PosePlayer()->HoldSnapshot(FrozenPose);
        Mesh->TickAnimation(0.f,false); Mesh->RefreshBoneTransforms();
    }
}

void UHumanoidKnockdownComponent::FreezeCorpse()
{
    auto* N=Humanoid(); auto* Mesh=BodyMesh();
    StopPhysicsWithPose();
    N->GetCharacterMovement()->DisableMovement();
    N->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    RestoreAnimatedCapsule();
    Phase=EHumanoidKnockdownPhase::FrozenCorpse;
    SetComponentTickEnabled(false);
    MonsterRagdollPhysics::RetireCorpseTicks(Mesh);
}
bool UHumanoidKnockdownComponent::CanReleaseCorpseBudget() const
{ return bCorpse && bGrounded && StableAge>.65f &&
    Phase==EHumanoidKnockdownPhase::Physics && PhaseAge>2.f; }
void UHumanoidKnockdownComponent::FreezeForBudget() { if (CanReleaseCorpseBudget()) FreezeCorpse(); }

bool UHumanoidKnockdownComponent::TryGetUp()
{
    if (GetWorld()->GetTimeSeconds()<NextRecoveryProbe) return false;
    auto* N=Humanoid(); auto* Mesh=BodyMesh();
    FHitResult Floor;
    if (!GetUpClip || !FindGround(Floor) || Floor.ImpactNormal.Z<N->GetCharacterMovement()->GetWalkableFloorZ()) return false;
    const bool bFaceDown=MonsterRagdollPhysics::BoneWorldTransform(Mesh,PelvisBone).TransformVectorNoScale(PelvisLocalFront).Z<0;
    UAnimSequence* RecoveryClip=bFaceDown && ProneGetUpClip?ProneGetUpClip.Get():GetUpClip.Get();
    FRotator Facing; FVector Candidate;
    if (!FindRecoverySpace(RecoveryClip,Floor,Facing,Candidate)) return false;
    auto* Capsule=N->GetCapsuleComponent();
    GetUpBlend=bFaceDown && !ProneGetUpClip?FMath::Max(.65f,RecoveryBlendSeconds):RecoveryBlendSeconds;
    const FTransform OldWorld=Mesh->GetComponentTransform();
    Mesh->SnapshotPose(FrozenPose);
    N->SetActorLocationAndRotation(Candidate,Facing,false,nullptr,ETeleportType::TeleportPhysics);
    Mesh->AttachToComponent(Capsule,FAttachmentTransformRules::KeepWorldTransform);
    Mesh->SetRelativeTransform(StandingMeshRelative);
    // Express the captured physical root in the new capsule/mesh frame before blending.
    MonsterRagdollPhysics::RebasePose(FrozenPose,OldWorld,Mesh->GetComponentTransform());
    Mesh->SetComponentTickEnabled(true); Mesh->bPauseAnims=false;
    PlayingClip=RecoveryClip;
    RecoveryFloorPoint=Floor.ImpactPoint; RecoveryFloorNormal=Floor.ImpactNormal;
    N->State=ENurseState::GettingUp;
    Phase=EHumanoidKnockdownPhase::GettingUp; PhaseAge=0; FinishBlendAge=-1.f;
    PosePlayer()->RecoverFromSnapshot(PlayingClip,FrozenPose,GetUpBlend);
    Mesh->TickAnimation(0.f,false); Mesh->RefreshBoneTransforms();
    Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    SetComponentTickInterval(0.f);
    return true;
}

void UHumanoidKnockdownComponent::RestoreCollision()
{
    RestoreAnimatedCapsule();
    auto* Mesh=BodyMesh();
    Mesh->SetCollisionEnabled(StandingMeshCollision);
    Mesh->bUpdateJointsFromAnimation=bStandingUpdateJointsFromAnimation;
    Mesh->SetCollisionObjectType(StandingObjectType); Mesh->SetCollisionResponseToChannels(StandingResponses);
    Humanoid()->GetCapsuleComponent()->SetCollisionEnabled(StandingCapsuleCollision);
}

void UHumanoidKnockdownComponent::FinishGetUp()
{
    auto* N=Humanoid(); auto* Mesh=BodyMesh();
    if (auto* Witch=Cast<AWitchRebuiltMonster>(N)) Witch->RestoreStandingPresentation();
    RestoreCollision();
    Mesh->SetForcedLOD(StandingLOD);
    Mesh->bPauseAnims=false;
    if (StandingAnimClass && StandingAnimClass!=Mesh->GetAnimClass()) Mesh->SetAnimInstanceClass(StandingAnimClass);
    N->GetCharacterMovement()->ClearAccumulatedForces(); N->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    N->GetCharacterMovement()->bForceNextFloorCheck=true;
    Phase=EHumanoidKnockdownPhase::None;
    N->SetState(ENurseState::Recovery);
    N->Combat->FinishReaction();
    FrozenPose.Reset(); PlayingClip=nullptr; bSavedStanding=false;
    SetComponentTickEnabled(false);
}

void UHumanoidKnockdownComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Dt,Type,Tick);
    auto* N=Humanoid(); auto* Mesh=BodyMesh();
    if (!N || !Mesh || !N->HasAuthority()) return;
    PhaseAge+=Dt; ProbeAge+=Dt;
    if (Phase==EHumanoidKnockdownPhase::Physics)
    {
        MonsterRagdollPhysics::LimitHandoffSpeed(Mesh,PhysicsHandoff,Dt);
        // The detached physical mesh stays in place while targeting follows the
        // actual pelvis every frame, even when its animation pose is not refreshed.
        N->SetActorLocation(MonsterRagdollPhysics::BoneWorldTransform(Mesh,PelvisBone).GetLocation(),
            false,nullptr,ETeleportType::TeleportPhysics);
    }
    if (Phase==EHumanoidKnockdownPhase::GettingUp)
    {
        if (FinishBlendAge>=0.f)
        {
            FinishBlendAge+=Dt;
            PosePlayer()->SetCombatTime(0.f);
            if (FinishBlendAge>=.2f && GetWorld()->GetTimeSeconds()>=ControlUntil) FinishGetUp();
            return;
        }
        // Join the matching prone/supine start, then play its grounded roll/rise.
        const float Time=FMath::Max(0.f,PhaseAge-GetUpBlend)*GetUpRate;
        PosePlayer()->SetCombatTime(Time);
        if (PlayingClip && Time>=PlayingClip->GetPlayLength() && GetWorld()->GetTimeSeconds()>=ControlUntil)
        {
            if (N->IdleClip)
            {
                FPoseSnapshot Pose; Mesh->SnapshotPose(Pose);
                PlayingClip=N->IdleClip;
                PosePlayer()->RecoverFromSnapshot(PlayingClip,Pose,.2f);
                FinishBlendAge=0.f;
            }
            else FinishGetUp();
        }
        return;
    }
    if (Phase==EHumanoidKnockdownPhase::AnimatedFall)
    {
        if (PlayingClip) PosePlayer()->SetCombatTime(FMath::Min(FallStopTime,ClipStartTime+PhaseAge));
        if (ClipStartTime+PhaseAge<FallStopTime || N->GetCharacterMovement()->IsFalling()) return;
        if (bCorpse) { FreezeCorpse(); return; }
        N->GetCharacterMovement()->DisableMovement();
        StopPhysicsWithPose();
        Mesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
        RestoreAnimatedCapsule();
        N->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Phase=EHumanoidKnockdownPhase::Downed; PhaseAge=0;
        ControlUntil=FMath::Max(ControlUntil,GetWorld()->GetTimeSeconds()+GroundHoldSeconds);
        SetComponentTickInterval(.1f); return;
    }
    if (ProbeAge<.1f) return;
    const float ProbeDt=ProbeAge; ProbeAge=0;
    if (Phase==EHumanoidKnockdownPhase::Physics)
    {
        FHitResult Ground; bGrounded=FindGround(Ground);
        const bool bPassiveCorpse=bCorpse && !bGroundCorpseFeet;
        const bool bSlow=MonsterRagdollPhysics::IsSettled(Mesh,bPassiveCorpse?10.f:20.f,bPassiveCorpse?.3f:.5f);
        StableAge=bGrounded && bSlow?StableAge+ProbeDt:0.f;
        // Never freeze an airborne corpse solely because its wall-clock budget expired.
        if ((StableAge>(bCorpse?.65f:.35f) && PhaseAge>(bCorpse?2.f:.55f)) ||
            (!bCorpse && bGrounded && PhaseAge>CorpseSettleDeadline))
        {
            if (bCorpse) { FreezeCorpse(); return; }
            StopPhysicsWithPose(); Phase=EHumanoidKnockdownPhase::Downed; PhaseAge=0;
            ControlUntil=FMath::Max(ControlUntil,GetWorld()->GetTimeSeconds()+GroundHoldSeconds);
            SetComponentTickInterval(.1f);
        }
    }
    if (Phase==EHumanoidKnockdownPhase::Downed && GetWorld()->GetTimeSeconds()>=ControlUntil) TryGetUp();
}
