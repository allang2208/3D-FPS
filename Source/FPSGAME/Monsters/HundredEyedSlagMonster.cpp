#include "HundredEyedSlagMonster.h"
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
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/OverlapResult.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

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
    Movement->RotationRate = FRotator(0, 180, 0);
    Movement->MaxWalkSpeed = ChaseSpeed;
    Movement->MaxAcceleration = 1400.f;
    Movement->BrakingDecelerationWalking = 1800.f;
    Movement->MaxStepHeight = 40.f;
    Movement->bCanWalkOffLedges = false;
    Movement->bRunPhysicsWithNoController = true;
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    static ConstructorHelpers::FClassFinder<AMonsterAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    AIControllerClass = AI.Succeeded() ? AI.Class.Get() : AMonsterAIController::StaticClass();
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> SlagMeshAsset(TEXT("/Game/Monsters/HundredEyedSlag/V1/SK_HundredEyedSlag_V1.SK_HundredEyedSlag_V1"));
    VisualMesh = SlagMeshAsset.Object;
    const TCHAR* Names[] = {TEXT("Idle"), TEXT("Move"), TEXT("Run"), TEXT("AttackSweep_R"),
        TEXT("AttackSlam_R"), TEXT("SpecialAshBurst"), TEXT("SpecialCharge"), TEXT("HitFront"),
        TEXT("HitLeft"), TEXT("HitRight"), TEXT("Stagger"), TEXT("StunEnter"), TEXT("StunLoop"),
        TEXT("StunExit"), TEXT("Death")};
    for (const TCHAR* Name : Names)
    {
        const FString AssetName = FString(TEXT("A_HundredEyedSlag_")) + Name;
        const FString Path = FString(TEXT("/Game/Monsters/HundredEyedSlag/V1/Animations/")) + AssetName + TEXT(".") + AssetName;
        ConstructorHelpers::FObjectFinder<UAnimSequence> Found(*Path);
        Clips.Add(FName(Name), Found.Object);
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
    EnterState(ESlagState::Idle);
}
bool AHundredEyedSlagMonster::Busy() const
{
    return Dead() || Controlled() || State == ESlagState::Recovery || State == ESlagState::Sweep
        || State == ESlagState::Slam || State == ESlagState::AshBurst || State == ESlagState::Charge;
}
void AHundredEyedSlagMonster::PlayClip(FName Name, bool Loop)
{
    if (CurrentClip == Name) return;
    CurrentClip = Name;
    if (auto* Player = Animation()) Player->TransitionTo(Clip(Name), Loop, !Loop, .08f);
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
    State = Next; StateSeconds = 0.f; CurrentClip = NAME_None;
    const bool Moving = Next == ESlagState::Chase || Next == ESlagState::Returning;
    GetCharacterMovement()->bOrientRotationToMovement = Moving;
    GetCharacterMovement()->MaxWalkSpeed = Next == ESlagState::Returning ? 39.f : ChaseSpeed;
    if (!Moving)
    {
        GetCharacterMovement()->StopMovementImmediately();
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->StopMovement();
    }
    switch (Next)
    {
    case ESlagState::Chase: PlayClip(TEXT("Run"), true); break;
    case ESlagState::Returning: PlayClip(TEXT("Move"), true); break;
    case ESlagState::Sweep: PlayClip(TEXT("AttackSweep_R")); break;
    case ESlagState::Slam: PlayClip(TEXT("AttackSlam_R")); break;
    case ESlagState::AshBurst: PlayClip(TEXT("SpecialAshBurst")); break;
    case ESlagState::Charge: PlayClip(TEXT("SpecialCharge")); GetCharacterMovement()->MaxWalkSpeed = ChargeSpeed; break;
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
    if (FMath::Abs(Victim->GetActorLocation().Z - GetActorLocation().Z) > 130.f) return false;
    const float Distance = FVector::Dist2D(Victim->GetActorLocation(), GetActorLocation());
    return Distance <= MeleeRange || (AshCooldown <= 0.f && Distance <= AshRadius)
        || (ChargeCooldown <= 0.f && Distance <= ChargeRange && Distance > MeleeRange);
}
bool AHundredEyedSlagMonster::StartAttack(APawn* Victim)
{
    if (!HasAuthority() || !CanAttack(Victim)) return false;
    Target = Victim;
    LockedDirection = (Victim->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
    SetActorRotation(LockedDirection.Rotation());
    HitVictims.Reset(); bAshReleased = false; bChargeBlocked = false;
    const float Distance = FVector::Dist2D(Victim->GetActorLocation(), GetActorLocation());
    if (Distance > MeleeRange && ChargeCooldown <= 0.f)
    {
        ChargeCooldown = 10.f; EnterState(ESlagState::Charge);
    }
    else if (AshCooldown <= 0.f && MeleeCounter >= 2)
    {
        AshCooldown = 8.f; MeleeCounter = 0; EnterState(ESlagState::AshBurst);
    }
    else if (Distance > MeleeRange)
    {
        AshCooldown = 8.f; EnterState(ESlagState::AshBurst);
    }
    else EnterState((++MeleeCounter % 2) ? ESlagState::Sweep : ESlagState::Slam);
    AttackCooldown = 2.5f;
    GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    PreviousPalm = GetMesh()->GetSocketLocation(TEXT("front_palm.R"));
    if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
    return true;
}
void AHundredEyedSlagMonster::DamageVictim(APawn* Victim, bool Magic)
{
    if (!IsValid(Victim) || !Victim->IsPlayerControlled() || HitVictims.Contains(Victim) || !CanSee(Victim)) return;
    const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Vitals && Vitals->IsDead()) return;
    HitVictims.Add(Victim);
    const ESlagState Before = State;
    const float Multiplier = State == ESlagState::Slam ? 1.4f : State == ESlagState::Charge ? 1.2f : 1.f;
    UGameplayStatics::ApplyDamage(Victim, (Magic ? MagicAttack : PhysicalAttack) * Multiplier,
        GetController(), this, Magic ? UHandBrainMagicDamage::StaticClass() : UEnemyMeleeDamage::StaticClass());
    // Damage can synchronously parry, stun or kill this attacker.
    if (State != Before || Dead()) return;
}
void AHundredEyedSlagMonster::SweepVictims(FVector From, FVector To, float Radius, bool Magic)
{
    const ESlagState Before = State;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SlagAttack), false, this);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByChannel(Hits, From, To, FQuat::Identity, ECC_Pawn, FCollisionShape::MakeSphere(Radius), Query);
    for (const FHitResult& Hit : Hits)
    {
        DamageVictim(Cast<APawn>(Hit.GetActor()), Magic);
        if (State != Before || Dead()) return;
    }
}
void AHundredEyedSlagMonster::Strike(float PreviousTime, float CurrentTime)
{
    if (State == ESlagState::AshBurst && !bAshReleased && PreviousTime < 1.f && CurrentTime >= 1.f)
    {
        bAshReleased = true;
        // Overlap gathers all victims; a blocking sweep would stop at the first body.
        TArray<FOverlapResult> Overlaps;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SlagAshBurst), false, this);
        GetWorld()->OverlapMultiByObjectType(Overlaps, GetActorLocation(), FQuat::Identity,
            FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeSphere(AshRadius), Query);
        for (const FOverlapResult& Overlap : Overlaps)
        {
            DamageVictim(Cast<APawn>(Overlap.GetActor()), true);
            if (State != ESlagState::AshBurst) return;
        }
        return;
    }
    const FVector Palm = GetMesh()->GetSocketLocation(TEXT("front_palm.R"));
    const float Start = State == ESlagState::Sweep ? .54f : .84f;
    const float End = State == ESlagState::Sweep ? .73f : 1.f;
    if ((State == ESlagState::Sweep || State == ESlagState::Slam) && CurrentTime >= Start && PreviousTime <= End)
    {
        SweepVictims(PreviousPalm, Palm, State == ESlagState::Slam ? 60.f : 48.f, false);
    }
    else if (State == ESlagState::Charge && !bChargeBlocked && CurrentTime >= .56f && PreviousTime <= 1.24f)
    {
        const FVector Center = GetActorLocation() + GetActorForwardVector() * 65.f;
        SweepVictims(Center, Center + GetActorForwardVector() * 10.f, 65.f, false);
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
    if (State == ESlagState::Dying)
    {
        const float Handoff = Clip(TEXT("Death")) ? Clip(TEXT("Death"))->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction : 1.68f;
        SampleClip(TEXT("Death"), FMath::Min(StateSeconds, Handoff));
        if (StateSeconds >= Handoff) EnterCorpse();
        return;
    }
    if (State == ESlagState::Corpse)
    {
        if (!bCorpseSleeping && StateSeconds >= 7.f) { GetMesh()->PutAllRigidBodiesToSleep(); bCorpseSleeping = true; }
        return;
    }
    if (Controlled())
    {
        if (StateSeconds >= ReactionSeconds) Combat->FinishReaction();
        return;
    }
    if (State == ESlagState::Recovery)
    {
        if (StateSeconds >= .16f) EnterState(ESlagState::Idle);
        return;
    }
    if (State == ESlagState::Chase || State == ESlagState::Returning)
    {
        if (auto* Player = Animation()) Player->SetLocomotionRate(FMath::Clamp(GetVelocity().Size2D() / (State == ESlagState::Returning ? 39.f : 91.f), 0.f, 1.6f));
        return;
    }
    if (State == ESlagState::Sweep || State == ESlagState::Slam || State == ESlagState::AshBurst || State == ESlagState::Charge)
    {
        if (!Target.IsValid()) { EnterState(ESlagState::Recovery); return; }
        if (State == ESlagState::Charge && !bChargeBlocked && StateSeconds >= .55f && StateSeconds < 1.25f)
            AddMovementInput(LockedDirection, 1.f, true);
        else GetCharacterMovement()->StopMovementImmediately();
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
    if (State == ESlagState::Charge && Impact.bBlockingHit && !Cast<APawn>(Impact.GetActor()))
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
    GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    GetMesh()->bPauseAnims = true;
    GetMesh()->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
    GetMesh()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    GetMesh()->SetAllBodiesSimulatePhysics(true); GetMesh()->SetSimulatePhysics(true);
    GetMesh()->SetAllPhysicsLinearVelocity(FVector::ZeroVector); GetMesh()->WakeAllRigidBodies();
    State = ESlagState::Corpse; StateSeconds = 0.f;
}
