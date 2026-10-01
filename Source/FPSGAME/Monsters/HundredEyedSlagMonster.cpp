#include "HundredEyedSlagMonster.h"
#include "SlagBlackMist.h"
#include "MonsterAIController.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "FatZombieAnimInstance.h"
#include "HandBrainMonster.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/OverlapResult.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/ConstraintInstance.h"

AHundredEyedSlagMonster::AHundredEyedSlagMonster(const FObjectInitializer& Initializer)
    : Super(Initializer.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick = true;
    Combat = CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    Status = CreateDefaultSubobject<UCombatStatusFormula>(TEXT("CombatStatus"));
    GetCapsuleComponent()->InitCapsuleSize(70.f, 70.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    GetMesh()->SetRelativeLocation(FVector(0, 0, -70));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetMesh()->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
    bUseControllerRotationYaw = false;
    BaseEyeHeight = 35.f;
    auto* Movement = GetCharacterMovement();
    Movement->bOrientRotationToMovement = true;
    Movement->RotationRate = FRotator(0, 270, 0);
    Movement->MaxWalkSpeed = ChaseSpeed;
    Movement->MaxAcceleration = 1400.f;
    Movement->BrakingDecelerationWalking = 1800.f;
    Movement->MaxStepHeight = 40.f;
    Movement->bCanWalkOffLedges = false;
    Movement->bRunPhysicsWithNoController = true;
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    static ConstructorHelpers::FClassFinder<AMonsterAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    AIControllerClass = AI.Succeeded() ? AI.Class.Get() : AMonsterAIController::StaticClass();
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> SlagMeshAsset(TEXT("/Game/Monsters/HundredEyedSlag/ArticulationV12/SK_HundredEyedSlag_V12.SK_HundredEyedSlag_V12"));
    VisualMesh = SlagMeshAsset.Object;
    const TCHAR* Names[] = {TEXT("Idle"), TEXT("Move"), TEXT("Run"), TEXT("AttackSweep_R"),
        TEXT("AttackSlam_R"), TEXT("HitFront"),
        TEXT("HitLeft"), TEXT("HitRight"), TEXT("Stagger"), TEXT("StunEnter"), TEXT("StunLoop"),
        TEXT("StunExit"), TEXT("Death"), TEXT("EyeLaserWindup"), TEXT("EyeLaserFire"),
        TEXT("EyeLaserRecover")};
    for (const TCHAR* Name : Names)
    {
        const bool Polished = FName(Name) == TEXT("Run") || FName(Name) == TEXT("Move") || FName(Name) == TEXT("Death");
        const FString AssetName = FString(TEXT("A_HundredEyedSlag_")) + Name + (Polished ? TEXT("_V2") : TEXT(""));
        const bool SpecialClip = FString(Name).StartsWith(TEXT("EyeLaser"));
        const FString Path = FString(SpecialClip ? TEXT("/Game/Monsters/HundredEyedSlag/ThreeAttacksV13/Animations/")
            : Polished ? TEXT("/Game/Monsters/HundredEyedSlag/PolishV2/Animations/")
            : TEXT("/Game/Monsters/HundredEyedSlag/V1/Animations/")) + AssetName + TEXT(".") + AssetName;
        ConstructorHelpers::FObjectFinder<UAnimSequence> Found(*Path);
        Clips.Add(FName(Name), Found.Object);
    }
    static ConstructorHelpers::FObjectFinder<UStaticMesh> LaserCylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> LaserSphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> ChargePlane(TEXT("/Engine/BasicShapes/Plane.Plane"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> LaserMaterial(TEXT("/Game/Monsters/HundredEyedSlag/EyeLaserJumpV11/Materials/M_EyeLaser.M_EyeLaser"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> ChargeMaterial(TEXT("/Game/Monsters/HundredEyedSlag/EyeChargeV14/M_EyeVortex.M_EyeVortex"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> EyeCore(TEXT("/Game/Monsters/HundredEyedSlag/EyeChargeV14/MI_EyeOrbRed.MI_EyeOrbRed"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> EyeConvergence(TEXT("/Game/Monsters/HundredEyedSlag/EyeChargeV14/NS_EyeConvergence.NS_EyeConvergence"));
    // Two eye glows, two soft eye halos, a focus orb and a core/halo pair.
    // All seven renderers are reused and have neither Tick nor collision.
    for (int32 I = 0; I < 7; ++I)
    {
        auto* Renderer = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("EyeLaser%d"), I));
        Renderer->SetupAttachment(GetMesh());
        Renderer->SetStaticMesh(I < 2 || I == 4 ? LaserSphere.Object : I < 4 ? ChargePlane.Object : LaserCylinder.Object);
        Renderer->SetMaterial(0, I < 2 ? EyeCore.Object : I < 4 ? ChargeMaterial.Object : LaserMaterial.Object);
        Renderer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Renderer->SetCastShadow(false);
        Renderer->bReceivesDecals = false;
        Renderer->SetVisibility(false);
        Renderer->SetComponentTickEnabled(false);
        EyeLaserRenderers.Add(Renderer);
    }
    for (int32 I = 0; I < 2; ++I)
    {
        auto* ChargeFX = CreateDefaultSubobject<UNiagaraComponent>(*FString::Printf(TEXT("EyeConvergence%d"),I));
        ChargeFX->SetupAttachment(GetMesh());
        ChargeFX->SetAsset(EyeConvergence.Object);
        ChargeFX->SetAutoActivate(false);
        ChargeFX->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        ChargeFX->SetCastShadow(false);
        ChargeFX->SetVisibility(false);
        EyeChargeSystems.Add(ChargeFX);
    }
    Combat->HitClip = Clip(TEXT("Stagger"));
    Tags.Add(TEXT("Enemy"));
    Tags.Add(TEXT("HundredEyedSlag"));
    AlignVisual();
}

UAnimSequence* AHundredEyedSlagMonster::Clip(FName Name) const
{
    const auto* Found = Clips.Find(Name);
    return Found ? Found->Get() : nullptr;
}
UFatZombieAnimInstance* AHundredEyedSlagMonster::Animation() const
{
    return Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance());
}
void AHundredEyedSlagMonster::AlignVisual()
{
    if (!VisualMesh) return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    // The imported top-level Armature has scale 100. Give it a physical body so
    // physics blending never inverse-scales positions through an unphysical parent.
    if (auto* Physics = LoadObject<UPhysicsAsset>(nullptr,
        TEXT("/Game/Monsters/HundredEyedSlag/RagdollGroundV16/PA_HundredEyedSlag_Ground_V16.PA_HundredEyedSlag_Ground_V16")))
        GetMesh()->SetPhysicsAsset(Physics);
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()));
    // Blender's FBX facing is converted at import; the authoring receipt supplies this yaw.
    GetMesh()->SetRelativeRotation(FRotator::ZeroRotator);
}
void AHundredEyedSlagMonster::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform); AlignVisual();
}
void AHundredEyedSlagMonster::BeginPlay()
{
    Super::BeginPlay();
    Home = GetActorLocation();
    MaxHealth *= static_cast<float>(MonsterCoreStats::HealthMultiplier());
    Health = FMath::Max(1.f, MaxHealth);
    AlignVisual();
    GetMesh()->AddTickPrerequisiteActor(this);
    GetMesh()->AddTickPrerequisiteComponent(Combat);
    for (const auto& ChargeFX : EyeChargeSystems)
        if (ChargeFX) { ChargeFX->AddTickPrerequisiteActor(this); ChargeFX->DeactivateImmediate(); }
    if (VisualMesh)
    {
        const auto& Skeleton = VisualMesh->GetRefSkeleton();
        int32 Index = Skeleton.FindBoneIndex(TEXT("front_plate"));
        FTransform Reference = FTransform::Identity;
        for (; Index != INDEX_NONE; Index = Skeleton.GetParentIndex(Index)) Reference = Reference*Skeleton.GetRefBonePose()[Index];
        EyeBindOffsets[0] = Reference.InverseTransformPosition(LaserPrimaryEyePosition);
        EyeBindOffsets[1] = Reference.InverseTransformPosition(LaserSecondaryEyePosition);
    }
    EnterState(ESlagState::Idle);
    if (HasAuthority() && bEnableBlackMist)
    {
        const FVector MistOffset = BlackMistOffset - FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        const FTransform SpawnTransform(GetActorRotation(), GetActorTransform().TransformPosition(MistOffset));
        BackMist = GetWorld()->SpawnActorDeferred<ASlagBlackMist>(ASlagBlackMist::StaticClass(),
            SpawnTransform, this, this, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if (BackMist)
        {
            BackMist->Radius = BlackMistRadius; BackMist->BlindSeconds = BlackMistBlindSeconds;
            BackMist->FinishSpawning(SpawnTransform);
            BackMist->AttachToActor(this, FAttachmentTransformRules::KeepWorldTransform);
            BackMist->SetActorRelativeRotation(FRotator::ZeroRotator);
            BackMist->SetActorRelativeLocation(MistOffset);
        }
    }
}
bool AHundredEyedSlagMonster::Busy() const
{
    return Dead() || Controlled() || State == ESlagState::Recovery || State == ESlagState::Sweep
        || State == ESlagState::Slam || SpecialAttacking();
}
void AHundredEyedSlagMonster::PlayClip(FName Name, bool Loop)
{
    if (CurrentClip == Name) return;
    CurrentClip = Name;
    if (auto* Player = Animation())
    {
        FMonsterClipTransition Settings;
        Settings.bContinueOutgoingLoop = Loop;
        Settings.InitialPlayRate = Loop ? FMath::Clamp(GetVelocity().Size2D() / (Name == TEXT("Move") ? 120.f : 280.f), .05f, 1.6f) : 1.f;
        if (Name == TEXT("Idle")) Settings.InitialPlayRate = 1.f;
        Player->TransitionTo(Clip(Name), Loop, !Loop, Name == TEXT("Death") ? .12f : Loop ? .16f : .10f, Settings);
    }
}
void AHundredEyedSlagMonster::SampleClip(FName Name, float Seconds, bool Loop)
{
    // Controlled loops wrap their sample explicitly; the player must not add a second clock.
    PlayClip(Name, false);
    if (auto* Player = Animation())
    {
        if (auto* Asset = Clip(Name); Asset && Asset->GetPlayLength() > SMALL_NUMBER)
            Player->SetCombatTime(Loop ? FMath::Fmod(FMath::Max(0.f, Seconds), Asset->GetPlayLength()) : Seconds);
        Player->SetControlledBlendTime(FMath::Max(0.f, Seconds));
    }
}
void AHundredEyedSlagMonster::EnterState(ESlagState Next)
{
    if (State != Next) ClearLaserFX();
    State = Next; StateSeconds = 0.f; CurrentClip = NAME_None;
    const bool Moving = Next == ESlagState::Chase || Next == ESlagState::Returning;
    // Begin the windup within the expanded claw corridor, without requiring
    // the monster to press its capsule against the player.
    const float ContactRange = FMath::Min(Next == ESlagState::Sweep ? 250.f : 215.f,MeleeRange*.8f);
    const bool MeleeApproach = (Next == ESlagState::Sweep || Next == ESlagState::Slam) && Target.IsValid()
        && FVector::Dist2D(Target->GetActorLocation(), GetActorLocation()) > ContactRange + 5.f;
    GetCharacterMovement()->bOrientRotationToMovement = Moving;
    GetCharacterMovement()->MaxWalkSpeed = Next == ESlagState::Returning ? ReturnSpeed : ChaseSpeed;
    GetCharacterMovement()->MaxAcceleration = 1400.f;
    if (!Moving)
    {
        GetCharacterMovement()->StopMovementImmediately();
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->StopMovement();
    }
    switch (Next)
    {
    case ESlagState::Chase: PlayClip(TEXT("Run"), true); break;
    case ESlagState::Returning: PlayClip(TEXT("Move"), true); break;
    case ESlagState::Sweep: PlayClip(MeleeApproach ? TEXT("Run") : TEXT("AttackSweep_R"), MeleeApproach); break;
    case ESlagState::Slam: PlayClip(MeleeApproach ? TEXT("Run") : TEXT("AttackSlam_R"), MeleeApproach); break;
    case ESlagState::EyeLaserWindup: PlayClip(TEXT("EyeLaserWindup")); break;
    case ESlagState::EyeLaserFire:
        LaserNextDamageSeconds = 0.f;
        PlayClip(TEXT("EyeLaserFire"));
        break;
    case ESlagState::EyeLaserRecover: PlayClip(TEXT("EyeLaserRecover")); break;
    case ESlagState::Dying: PlayClip(TEXT("Death")); break;
    case ESlagState::Recovery: PlayClip(TEXT("Idle"), true); break;
    case ESlagState::Idle: PlayClip(TEXT("Idle"), true); break;
    default: break;
    }
}
void AHundredEyedSlagMonster::SetLocomotion(bool Moving, bool Returning)
{
    if (Busy()) return;
    const ESlagState Next = Moving ? (Returning ? ESlagState::Returning : ESlagState::Chase) : ESlagState::Idle;
    if (State != Next) EnterState(Next);
}
bool AHundredEyedSlagMonster::CanSee(const APawn* Victim) const
{
    if (!IsValid(Victim)) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SlagVisibility), false, this);
    Query.AddIgnoredActor(Victim);
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation(), Victim->GetActorLocation(), ECC_Visibility, Query);
}
bool AHundredEyedSlagMonster::CanAttack(APawn* Victim) const
{
    if (!IsValid(Victim) || Busy() || AttackCooldown > 0.f || !CanSee(Victim)) return false;
    const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Vitals && Vitals->IsDead()) return false;
    const float Distance = FVector::Dist2D(Victim->GetActorLocation(), GetActorLocation());
    const bool Grounded = GetCharacterMovement()->IsMovingOnGround() && !Status->BlocksMovement();
    const bool PhysicalHeight = FMath::Abs(Victim->GetActorLocation().Z - GetActorLocation().Z) <= 130.f;
    return (Grounded && PhysicalHeight && Distance <= MeleeRange)
        || (Grounded && LaserCooldown <= 0.f && FVector::Dist(Victim->GetActorLocation(), LaserFocus()) <= LaserRange
            && Clip(TEXT("EyeLaserWindup")) && Clip(TEXT("EyeLaserFire")) && Clip(TEXT("EyeLaserRecover")));
}
bool AHundredEyedSlagMonster::StartAttack(APawn* Victim)
{
    if (!HasAuthority() || !CanAttack(Victim)) return false;
    Target = Victim;
    LockedDirection = (Victim->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
    SetActorRotation(LockedDirection.Rotation());
    HitVictims.Reset(); bAshReleased = false; bChargeBlocked = false;
    const float Distance = FVector::Dist2D(Victim->GetActorLocation(), GetActorLocation());
    const bool PhysicalHeight = FMath::Abs(Victim->GetActorLocation().Z - GetActorLocation().Z) <= 130.f;
    if (LaserCooldown <= 0.f && (Distance > MeleeRange || !PhysicalHeight)
        && FVector::Dist(Victim->GetActorLocation(), LaserFocus()) <= LaserRange
        && Clip(TEXT("EyeLaserWindup")) && Clip(TEXT("EyeLaserFire")) && Clip(TEXT("EyeLaserRecover")))
    {
        bLaserAimLocked = false; LaserCooldown = LaserCooldownSeconds; EnterState(ESlagState::EyeLaserWindup);
    }
    else EnterState((++MeleeCounter % 2) ? ESlagState::Sweep : ESlagState::Slam);
    // Busy owns the full action and recovery. Avoid an additional idle gap after it.
    AttackCooldown = 1.25f;
    GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    PreviousPalm = GetMesh()->GetSocketLocation(TEXT("front_palm_R"));
    if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
    return true;
}
void AHundredEyedSlagMonster::DamageVictim(APawn* Victim, bool Magic)
{
    if (!IsValid(Victim) || !Victim->IsPlayerControlled() || HitVictims.Contains(Victim) || !CanSee(Victim)) return;
    const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Vitals && Vitals->IsDead()) return;
    if (!Magic && (State == ESlagState::Sweep || State == ESlagState::Slam))
    {
        const FVector Delta = Victim->GetActorLocation()-GetActorLocation();
        const float Reach = State == ESlagState::Slam ? SlamReach : SweepReach;
        const float TargetRadius = Victim->GetSimpleCollisionRadius();
        const float Facing = FVector::DotProduct(Delta.GetSafeNormal2D(),LockedDirection.GetSafeNormal2D());
        if (Delta.Size2D() > Reach+TargetRadius || Facing < (State == ESlagState::Slam ? .70f : .30f)) return;
    }
    HitVictims.Add(Victim);
    const ESlagState Before = State;
    const float Multiplier = State == ESlagState::Slam ? 1.4f : SweepDamageMultiplier;
    const float Applied = UGameplayStatics::ApplyDamage(Victim, (Magic ? MagicAttack : PhysicalAttack) * Multiplier,
        GetController(), this, Magic ? UHandBrainMagicDamage::StaticClass() : UEnemyMeleeDamage::StaticClass());
    // Damage can synchronously parry, stun or kill this attacker.
    if (State != Before || Dead()) return;
    if (!Magic && Before == ESlagState::Slam && Applied > 0.f && (!Vitals || !Vitals->IsDead()))
        UCombatStatusFormula::GetOrAdd(Victim)->AddStun(SlamStunSeconds);
}
void AHundredEyedSlagMonster::SweepVictims(FVector From, FVector To, float Radius, bool Magic)
{
    const ESlagState Before = State;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SlagAttack), false, this);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByObjectType(Hits, From, To, FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeSphere(Radius), Query);
    for (const FHitResult& Hit : Hits)
    {
        DamageVictim(Cast<APawn>(Hit.GetActor()), Magic);
        if (State != Before || Dead()) return;
    }
}
void AHundredEyedSlagMonster::Strike(float PreviousTime, float CurrentTime)
{
    const FVector Palm = GetMesh()->GetSocketLocation(TEXT("front_palm_R"));
    const float Start = State == ESlagState::Sweep ? .54f : .84f;
    const float End = State == ESlagState::Sweep ? .73f : 1.f;
    if ((State == ESlagState::Sweep || State == ESlagState::Slam) && CurrentTime >= Start && PreviousTime <= End)
    {
        const ESlagState Before = State;
        const float Radius = State == ESlagState::Slam ? SlamHitRadius : SweepHitRadius;
        const float Reach = State == ESlagState::Slam ? SlamReach : SweepReach;
        SweepVictims(PreviousPalm,Palm,Radius,false);
        if (State != Before || Dead()) return;
        // Extrude the animated claw volume forward within its reach. This
        // changes actual contact coverage, not just AI engagement distance.
        const FVector Direction = LockedDirection.GetSafeNormal2D();
        const float Extension = FMath::Max(0.f,Reach-Radius-FVector::DotProduct(Palm-GetActorLocation(),Direction));
        SweepVictims(Palm,Palm+Direction*Extension,Radius,false);
    }
    PreviousPalm = Palm;
}
void AHundredEyedSlagMonster::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!HasAuthority()) return;
    const float PreviousTime = StateSeconds;
    StateSeconds += DeltaSeconds;
    AttackCooldown = FMath::Max(0.f, AttackCooldown - DeltaSeconds);
    AshCooldown = FMath::Max(0.f, AshCooldown - DeltaSeconds);
    ChargeCooldown = FMath::Max(0.f, ChargeCooldown - DeltaSeconds);
    LaserCooldown = FMath::Max(0.f, LaserCooldown - DeltaSeconds);
    if (State == ESlagState::Dying)
    {
        const float Handoff = Clip(TEXT("Death")) ? FMath::Min(RagdollHandoffSeconds, Clip(TEXT("Death"))->GetPlayLength()) : RagdollHandoffSeconds;
        TMap<FName, FTransform> PreviousBodies;
        if (auto* Physics = GetMesh()->GetPhysicsAsset())
            for (const USkeletalBodySetup* Body : Physics->SkeletalBodySetups)
                PreviousBodies.Add(Body->BoneName, GetMesh()->GetSocketTransform(Body->BoneName));
        const float SampleTime = FMath::Min(StateSeconds, Handoff);
        SampleClip(TEXT("Death"), SampleTime);
        GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
        const float Interval = FMath::Max(.001f, SampleTime - PreviousTime);
        for (const auto& Pair : PreviousBodies)
        {
            const FTransform Now = GetMesh()->GetSocketTransform(Pair.Key);
            DeathBoneVelocities.Add(Pair.Key, ((Now.GetLocation() - Pair.Value.GetLocation()) / Interval).GetClampedToMaxSize(400.f));
            FQuat Delta = Now.GetRotation() * Pair.Value.GetRotation().Inverse();
            if (Delta.W < 0.f) Delta = Delta * -1.f;
            FVector Axis; float Angle; Delta.ToAxisAndAngle(Axis, Angle);
            DeathBoneAngularVelocities.Add(Pair.Key, (Axis * (Angle / Interval)).GetClampedToMaxSize(10.f));
        }
        if (StateSeconds >= Handoff) EnterCorpse();
        return;
    }
    if (State == ESlagState::Corpse)
    {
        if (!bCorpseSleeping && StateSeconds >= 5.f)
        {
            bool Settled = true;
            for (const auto* Body : GetMesh()->Bodies) if (Body && Body->IsValidBodyInstance())
                Settled &= Body->GetUnrealWorldVelocity().SizeSquared() < 81.f
                    && Body->GetUnrealWorldAngularVelocityInRadians().SizeSquared() < .09f;
            if (Settled) { GetMesh()->PutAllRigidBodiesToSleep(); bCorpseSleeping = true; }
        }
        return;
    }
    if (Controlled())
    {
        if (StateSeconds >= ReactionSeconds) Combat->FinishReaction();
        return;
    }
    if (State == ESlagState::Recovery)
    {
        if (StateSeconds >= .12f)
        {
            EnterState(ESlagState::Idle);
            if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
        }
        return;
    }
    if (State == ESlagState::Chase || State == ESlagState::Returning)
    {
        if (auto* Player = Animation()) Player->SetLocomotionRate(FMath::Clamp(GetVelocity().Size2D() / (State == ESlagState::Returning ? 120.f : 280.f), 0.f, 1.6f));
        return;
    }
    if (SpecialAttacking()) { TickSpecialAttack(DeltaSeconds); return; }
    if (State == ESlagState::Sweep || State == ESlagState::Slam)
    {
        if (!Target.IsValid()) { EnterState(ESlagState::Recovery); return; }
        APawn* Victim = Target.Get();
        auto* Movement = GetCharacterMovement();
        const FVector ToVictim = Victim->GetActorLocation() - GetActorLocation();
        const bool Melee = State == ESlagState::Sweep || State == ESlagState::Slam;
        if (Melee && CurrentClip == TEXT("Run"))
        {
            const float ContactRange = FMath::Min(State == ESlagState::Sweep ? 250.f : 215.f,MeleeRange*.8f);
            const float Gap = ToVictim.Size2D() - ContactRange;
            if (bChargeBlocked || StateSeconds >= 1.1f || !Movement->IsMovingOnGround()
                || FMath::Abs(ToVictim.Z) > 130.f)
            {
                EnterState(ESlagState::Recovery); return;
            }
            if (Gap <= 5.f)
            {
                // Reset the action clock on planting; this remains one busy action.
                EnterState(State);
                GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
                PreviousPalm = GetMesh()->GetSocketLocation(TEXT("front_palm_R"));
                return;
            }
            SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), ToVictim.GetSafeNormal2D().Rotation(), DeltaSeconds, 270.f));
            Movement->MaxWalkSpeed = FMath::Min(ChaseSpeed, Gap / FMath::Max(DeltaSeconds, .001f));
            AddMovementInput(ToVictim.GetSafeNormal2D(), 1.f, true);
            if (auto* Player = Animation()) Player->SetLocomotionRate(FMath::Clamp(GetVelocity().Size2D() / 280.f, 0.f, 1.6f));
            return;
        }
        const float AimUntil = State == ESlagState::Sweep ? .48f : State == ESlagState::Slam ? .74f : .40f;
        // Track only the readable windup; the active strike/dash remains committed.
        if (Melee && StateSeconds < AimUntil && !ToVictim.IsNearlyZero())
        {
            SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), ToVictim.GetSafeNormal2D().Rotation(), DeltaSeconds, 180.f));
            LockedDirection = GetActorForwardVector();
        }
        Movement->StopMovementImmediately();
        const ESlagState Before = State;
        SampleClip(CurrentClip, StateSeconds);
        GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
        Strike(PreviousTime, StateSeconds);
        if (State != Before) return;
        const float Duration = Clip(CurrentClip) ? Clip(CurrentClip)->GetPlayLength() : 2.4f;
        if (StateSeconds >= Duration) EnterState(ESlagState::Recovery);
    }
}
void AHundredEyedSlagMonster::MoveBlockedBy(const FHitResult& Impact)
{
    Super::MoveBlockedBy(Impact);
    if ((State == ESlagState::Sweep || State == ESlagState::Slam)
        && Impact.bBlockingHit && !Cast<APawn>(Impact.GetActor()))
    {
        bChargeBlocked = true; GetCharacterMovement()->StopMovementImmediately();
    }
}
void AHundredEyedSlagMonster::InterruptAttack(float Seconds)
{
    if (!HasAuthority() || Dead()) return;
    ReactionSeconds = FMath::Max(.1f, Seconds);
    HitVictims.Reset(); bAshReleased = true; bChargeBlocked = true;
    EnterState(ESlagState::Stagger);
    Combat->BeginReaction(ReactionSeconds);
}
void AHundredEyedSlagMonster::StartHitPresentation()
{
    bStunPresentation = Combat->bStunned && !Combat->IsImmobileReaction();
    const FVector Local = GetActorTransform().InverseTransformVectorNoScale(DamageDirection);
    ReactionClip = Combat->IsParryReaction() || ReactionSeconds >= Combat->ToughnessBreakSeconds * .8f ? FName(TEXT("Stagger"))
        : FMath::Abs(Local.Y) > FMath::Abs(Local.X) ? (Local.Y > 0.f ? FName(TEXT("HitLeft")) : FName(TEXT("HitRight"))) : FName(TEXT("HitFront"));
    SampleClip(bStunPresentation ? FName(TEXT("StunEnter")) : ReactionClip, 0.f);
}
void AHundredEyedSlagMonster::SetHitPresentationTime(float Elapsed, float Remaining)
{
    const float StunLeft = Combat->StunSecondsRemaining();
    if (bStunPresentation && !Combat->IsImmobileReaction() && StunLeft > 0.f)
    {
        // All three phases fit inside the skill deadline, including short stuns.
        const float EntryWindow = FMath::Min(.6f, ReactionSeconds * .3f);
        const float ExitWindow = FMath::Min(.7f, ReactionSeconds * .3f);
        if (StunLeft <= ExitWindow)
            SampleClip(TEXT("StunExit"), .7f * (1.f - StunLeft / FMath::Max(.01f, ExitWindow)));
        else if (Elapsed < EntryWindow)
            SampleClip(TEXT("StunEnter"), .6f * Elapsed / FMath::Max(.01f, EntryWindow));
        else SampleClip(TEXT("StunLoop"), Elapsed - EntryWindow, true);
    }
    else
    {
        const float Length = Clip(ReactionClip) ? Clip(ReactionClip)->GetPlayLength() : 1.05f;
        const float Time = Combat->IsImmobileReaction() ? FMath::Min(.15f, Length) : FMath::Clamp(Elapsed / FMath::Max(.1f, ReactionSeconds) * Length, 0.f, Length);
        SampleClip(ReactionClip, Time);
    }
}
void AHundredEyedSlagMonster::FinishHitReaction()
{
    if (Controlled() && !Dead()) { bStunPresentation = false; EnterState(ESlagState::Idle); }
}
float AHundredEyedSlagMonster::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    if (!HasAuthority() || Dead() || Damage <= 0.f) return 0.f;
    const float Applied = UDevelopmentTuningSubsystem::ShouldOneHitKill(this, EventInstigator, Causer) ? Health
        : FMath::Min(Health, CombatFormulaRuntime::MitigateMonster(this, Damage,
            Event.DamageTypeClass ? Event.DamageTypeClass->GetDefaultObject<UDamageType>() : nullptr, Causer));
    if (Applied <= 0.f) return 0.f;
    DamageDirection = Causer ? Causer->GetActorLocation() - GetActorLocation() : -GetActorForwardVector();
    Health -= Applied; Super::TakeDamage(Applied, Event, EventInstigator, Causer);
    if (Health <= 0.f)
    {
        if (BackMist) { BackMist->StopEmission(); BackMist = nullptr; }
        DeathVelocity = GetVelocity().GetClampedToMaxSize(400.f);
        Target.Reset(); HitVictims.Reset(); EnterState(ESlagState::Dying);
        GetCharacterMovement()->DisableMovement();
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        SetLifeSpan(CorpseSeconds);
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
        if (!bRewarded)
        {
            bRewarded = true;
            if (auto* PC = Cast<APlayerController>(EventInstigator))
                if (PC->IsLocalController() && GetGameInstance()) GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this, ExperienceReward);
        }
    }
    else Combat->ReceiveHit(Applied, EventInstigator ? EventInstigator->GetPawn().Get() : Cast<APawn>(Causer), MonsterToughness::FormOf(Event.DamageTypeClass));
    return Applied;
}
void AHundredEyedSlagMonster::EnterCorpse()
{
    auto* CorpseMesh = GetMesh();
    CorpseMesh->KinematicBonesUpdateType = EKinematicBonesUpdateToPhysics::SkipSimulatingBones;
    CorpseMesh->TickAnimation(0.f, false); CorpseMesh->RefreshBoneTransforms();
    CorpseMesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    CorpseMesh->SetCollisionProfileName(TEXT("Ragdoll"));
    CorpseMesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    CorpseMesh->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    CorpseMesh->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);
    CorpseMesh->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Block);
    // A deferred target can still hold the previous animation frame. Flush the
    // sampled death pose while every body is kinematic, then freeze animation writes.
    CorpseMesh->UpdateKinematicBonesToAnim(CorpseMesh->GetComponentSpaceTransforms(),
        ETeleportType::TeleportPhysics, false, EAllowKinematicDeferral::DisallowDeferral);
    for (auto* Joint : CorpseMesh->Constraints)
    {
        if (!Joint || Joint->ConstraintBone1 != TEXT("pelvis") || Joint->ConstraintBone2 != TEXT("Armature")) continue;
        const auto* Child = CorpseMesh->GetBodyInstance(Joint->ConstraintBone1);
        const auto* Parent = CorpseMesh->GetBodyInstance(Joint->ConstraintBone2);
        if (!Child || !Parent) continue;
        FTransform ChildWorld = Child->GetUnrealWorldTransform(false, true);
        FTransform ParentWorld = Parent->GetUnrealWorldTransform(false, true);
        ChildWorld.RemoveScaling(); ParentWorld.RemoveScaling();
        // Live constraint frames use rigid-body centimetres, not inverse-scaled
        // skeleton units. Lock the helper to THIS pose, not the standing reference.
        Joint->SetRefFrame(EConstraintFrame::Frame1, FTransform::Identity);
        Joint->SetRefFrame(EConstraintFrame::Frame2, ChildWorld.GetRelativeTransform(ParentWorld));
        Joint->SetLinearXLimit(LCM_Locked, 0.f); Joint->SetLinearYLimit(LCM_Locked, 0.f); Joint->SetLinearZLimit(LCM_Locked, 0.f);
        Joint->SetAngularSwing1Limit(ACM_Locked, 0.f); Joint->SetAngularSwing2Limit(ACM_Locked, 0.f);
        Joint->SetAngularTwistLimit(ACM_Locked, 0.f); Joint->SetDisableCollision(true);
    }
    // The container root follows the pelvis; it must not collide at the model origin.
    if (auto* Root = CorpseMesh->GetBodyInstance(TEXT("Armature")))
        Root->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CorpseMesh->SetAllUseCCD(true);
    CorpseMesh->SetEnableGravity(true);
    CorpseMesh->bPauseAnims = true;
    CorpseMesh->bUpdateJointsFromAnimation = false;
    CorpseMesh->KinematicBonesUpdateType = EKinematicBonesUpdateToPhysics::SkipAllBones;
    CorpseMesh->SetAllBodiesSimulatePhysics(true); CorpseMesh->SetSimulatePhysics(true);
    CorpseMesh->SetAllBodiesPhysicsBlendWeight(1.f);
    const FVector ImpactVelocity = -DamageDirection.GetSafeNormal2D() * 45.f;
    FVector FallVelocity = (DeathBoneVelocities.FindRef(TEXT("pelvis")) + DeathVelocity * .4f + ImpactVelocity).GetClampedToMaxSize(400.f);
    FallVelocity.Z = FMath::Clamp(FallVelocity.Z, -180., 0.);
    const FVector AngularVelocity = DeathBoneAngularVelocities.FindRef(TEXT("pelvis")).GetClampedToMaxSize(3.f);
    const auto* Pelvis = CorpseMesh->GetBodyInstance(TEXT("pelvis"));
    const FVector Pivot = Pelvis ? Pelvis->GetCOMPosition() : CorpseMesh->GetSocketLocation(TEXT("pelvis"));
    for (auto* Body : CorpseMesh->Bodies) if (Body && Body->IsValidBodyInstance())
    {
        Body->ClearForces(); Body->ClearTorques();
        // Independent sampled limb velocities fight the locked joints, including
        // the new container. Transfer one coherent rigid motion at each body COM.
        Body->SetLinearVelocity(FallVelocity + FVector::CrossProduct(AngularVelocity, Body->GetCOMPosition() - Pivot), false);
        Body->SetAngularVelocityInRadians(AngularVelocity, false);
    }
    CorpseMesh->WakeAllRigidBodies();
    State = ESlagState::Corpse; StateSeconds = 0.f;
}
