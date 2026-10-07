#include "VortexCofferM25.h"
#include "MonsterCorpseRagdollComponent.h"
#include "M25AnimInstance.h"
#include "M25BackElectricComponent.h"
#include "M25MagicComponent.h"
#include "M25BiteComponent.h"
#include "MonsterAIController.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"

AVortexCofferM25::AVortexCofferM25(const FObjectInitializer& Initializer)
    : Super(Initializer.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(CharacterMovementComponentName)
        .SetDefaultSubobjectClass<UMonsterIdleBreathingMeshComponent>(MeshComponentName))
{
    // Shared BT pursuit also uses this as the actor's enabled/disabled gate.
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    Combat = CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    CorpseRagdoll = CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    CorpseRagdoll->Rig = EMonsterCorpseRig::Mawcrawler;
    BackElectric = CreateDefaultSubobject<UM25BackElectricComponent>(TEXT("BackElectric"));
    Magic = CreateDefaultSubobject<UM25MagicComponent>(TEXT("MagicExecution"));
    Bite = CreateDefaultSubobject<UM25BiteComponent>(TEXT("BiteExecution"));
    IdleVoice = CreateDefaultSubobject<UAudioComponent>(TEXT("IdleVoice"));
    CrawlVoice = CreateDefaultSubobject<UAudioComponent>(TEXT("CrawlVoice"));
    for (TObjectPtr<UAudioComponent> Voice : {IdleVoice, CrawlVoice})
    {
        Voice->SetupAttachment(GetMesh(), TEXT("body_05"));
        Voice->bAutoActivate = false;
        Voice->bAutoDestroy = false;
        Voice->bAllowAnyoneToDestroyMe = false;
        Voice->bOverrideAttenuation = true;
        Voice->AttenuationOverrides.bAttenuate = true;
        Voice->AttenuationOverrides.bSpatialize = true;
    }
    IdleVoice->AttenuationOverrides.FalloffDistance = 1400.f;
    CrawlVoice->AttenuationOverrides.FalloffDistance = 1500.f;
    GetCapsuleComponent()->InitCapsuleSize(225.f, 225.f);
    GetMesh()->SetRelativeLocation(FVector(0, 0, -225.f));
    ApplyHitCollision();
    GetMesh()->SetGenerateOverlapEvents(false);
    GetMesh()->SetCanEverAffectNavigation(false);
    GetMesh()->SetAnimInstanceClass(UM25AnimInstance::StaticClass());
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetMesh()->bEnableUpdateRateOptimizations = true;

    auto* Movement = GetCharacterMovement();
    Movement->MaxWalkSpeed = WalkSpeed;
    Movement->MaxAcceleration = 480.f;
    Movement->BrakingDecelerationWalking = 720.f;
    Movement->RotationRate = FRotator(0, 150.f, 0);
    Movement->bOrientRotationToMovement = true;
    Movement->bCanWalkOffLedges = false;
    Movement->bRunPhysicsWithNoController = true;
    // Share M10's large-body clearance and the HandBrain 40 cm stair limit.
    CastChecked<UMonsterCharacterMovementComponent>(Movement)->ConfigureWideBodyStairs(225.f, 450.f);
    bUseControllerRotationYaw = false;
    BaseEyeHeight = -180.f;
    AIControllerClass = AMonsterAIController::StaticClass();
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    SetCanBeDamaged(true);
    Tags.Add(TEXT("Enemy"));
    Tags.Add(TEXT("VortexCofferM25"));
}

void AVortexCofferM25::GetActorEyesViewPoint(FVector& Location, FRotator& Rotation) const
{
    // Sight originates near the exposed electrodes instead of the low capsule eye.
    Location = Magic ? Magic->ElectrodeLocation() + FVector(0, 0, 10.f) : GetActorLocation();
    Rotation = GetActorRotation();
}

void AVortexCofferM25::ApplyVisual()
{
    if (!VisualMesh) return;
    if (GetMesh()->GetSkeletalMeshAsset() != VisualMesh)
        GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    if (HitSurfacePhysics && GetMesh()->GetPhysicsAsset() != HitSurfacePhysics)
        GetMesh()->SetPhysicsAsset(HitSurfacePhysics);
    const FBoxSphereBounds Bounds = VisualMesh->GetBounds();
    const float Bottom = Bounds.Origin.Z - Bounds.BoxExtent.Z;
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() - Bottom));
    GetMesh()->SetRelativeRotation(FRotator(0, MeshYaw, 0));
}

void AVortexCofferM25::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225.f, 450.f);
    ApplyVisual();
    ApplyHitCollision();
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
}

void AVortexCofferM25::BeginPlay()
{
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225.f, 450.f);
    Super::BeginPlay();
    ApplyVisual();
    ApplyHitCollision();
    SetCanBeDamaged(true);
    if (HasAuthority())
    {
        MaxHealth = FMath::Max(1.f, MaxHealth * float(MonsterCoreStats::HealthMultiplier()));
        Health = MaxHealth;
    }
    Home = GetActorLocation();
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
    GetMesh()->AddTickPrerequisiteComponent(GetCharacterMovement());
    if (GetNetMode() != NM_DedicatedServer)
    {
        if (IdleVoice) IdleVoice->SetSound(IdleSound);
        if (CrawlVoice) CrawlVoice->SetSound(CrawlSound);
        UpdateLoopAudio();
    }
    if (auto* AI = Cast<AMonsterAIController>(GetController()))
        AI->UpdateKnowledge();
}

void AVortexCofferM25::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateLoopAudio();
}

USoundAttenuation* AVortexCofferM25::OneShotAttenuation(float Falloff) const
{
    auto* Attenuation = NewObject<USoundAttenuation>(const_cast<AVortexCofferM25*>(this));
    Attenuation->Attenuation.bAttenuate = true;
    Attenuation->Attenuation.bSpatialize = true;
    Attenuation->Attenuation.FalloffDistance = Falloff;
    return Attenuation;
}

void AVortexCofferM25::UpdateLoopAudio()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    const bool Alive = !Dead();
    if (IdleVoice)
    {
        if (Alive && IdleVoice->Sound) { if (!IdleVoice->IsPlaying()) IdleVoice->Play(); }
        else if (IdleVoice->IsPlaying()) IdleVoice->Stop();
    }
    if (CrawlVoice)
    {
        const bool Moving = Alive && !Controlled()
            && GetCharacterMovement()->IsMovingOnGround() && GetVelocity().Size2D() > 4.f;
        if (Moving && CrawlVoice->Sound) { if (!CrawlVoice->IsPlaying()) CrawlVoice->Play(); }
        else if (CrawlVoice->IsPlaying()) CrawlVoice->Stop();
    }
}

bool AVortexCofferM25::CanAttackTarget(APawn* Target) const
{
    return !Dead() && !Controlled() && ((Bite && Bite->CanAttack(Target)) || (Magic && Magic->CanAttack(Target)));
}

bool AVortexCofferM25::AttackBusy() const
{
    const bool Executing = (Bite && Bite->IsBusy()) || (Magic && Magic->IsBusy());
    // Hold movement only when no other channel can start. Selection still belongs to the shared BT.
    return Executing && !CanAttackTarget(CombatTarget.Get());
}

bool AVortexCofferM25::StartAttack(APawn* Target)
{
    if (Dead() || Controlled()) return false;
    if (Bite && Bite->CanAttack(Target)) return Bite->StartAttack(Target);
    return Magic && Magic->StartAttack(Target);
}

void AVortexCofferM25::SetCombatTarget(APawn* Target)
{
    if (Target) bHasSearchGoal = false;
    CombatTarget = Target;
    if (Bite) Bite->SetTarget(Target);
    if (Magic) Magic->SetTarget(Target);
}

void AVortexCofferM25::RefreshCombatPoseTick()
{
    const bool Executing = !Dead() && (Controlled() || (Bite && Bite->IsBusy()) || (Magic && Magic->IsBusy()));
    auto* Body = GetMesh();
    if (Executing && !bCombatPoseOverride)
    {
        bCombatPoseOverride = true;
        SavedPoseTick = uint8(Body->VisibilityBasedAnimTickOption);
        bSavedUpdateRateOptimization = Body->bEnableUpdateRateOptimizations;
        Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Body->bEnableUpdateRateOptimizations = false;
    }
    else if (!Executing && bCombatPoseOverride)
    {
        Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption(SavedPoseTick);
        Body->bEnableUpdateRateOptimizations = bSavedUpdateRateOptimization;
        bCombatPoseOverride = false;
    }
}
