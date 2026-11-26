#include "WildlifeAnimal.h"
#include "HillsWildlifeAudio.h"
#include "WildlifeDistanceActivity.h"
#include "WildlifeSubsystem.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "TimerManager.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Hearing.h"
#include "QuadrupedAnimationTemplate.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterCoreStats.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/EnemyAttackDamage.h"
#include "FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    bool WildlifeMeleeClear(const ACharacter& Animal,const APawn& Victim,float Reach)
    {
        const FVector Offset=Victim.GetActorLocation()-Animal.GetActorLocation();
        const float VerticalGap=FMath::Max(0.f,FMath::Abs(float(Offset.Z))
            -Animal.GetSimpleCollisionHalfHeight()-Victim.GetSimpleCollisionHalfHeight());
        // Same horizontal reach on level ground; separated capsules on ledges
        // must also fit inside that reach, rather than ignoring height entirely.
        if(Offset.SizeSquared2D()+FMath::Square(VerticalGap)>FMath::Square(Reach))return false;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(WildlifeMeleeSight),false,&Animal);
        Query.AddIgnoredActor(&Victim);
        return !Animal.GetWorld()->LineTraceTestByChannel(Animal.GetActorLocation(),Victim.GetActorLocation(),ECC_Visibility,Query);
    }
}

AColdSteelAnimal::AColdSteelAnimal(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UMonsterIdleBreathingMeshComponent>(MeshComponentName))
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    SetReplicateMovement(true);
    Random.GenerateNewSeed();
    WildlifeAudio = CreateDefaultSubobject<UHillsWildlifeAudio>(TEXT("HillsWildlifeAudio"));
    DistanceActivity = CreateDefaultSubobject<UWildlifeDistanceActivity>(TEXT("WildlifeDistanceActivity"));
    CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    CorpseRagdoll = CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    CorpseRagdoll->bAllowClientPresentation = true;
    CorpseRagdoll->Rig = EMonsterCorpseRig::Canine;
    GetCapsuleComponent()->InitCapsuleSize(34.f, 60.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetMesh()->SetAnimInstanceClass(UQuadrupedTemplateAnimInstance::StaticClass());
    bUseControllerRotationYaw = false;
    AutoPossessAI = EAutoPossessAI::Disabled;
    BaseEyeHeight = 20.f;
    auto* Move = GetCharacterMovement();
    Move->bOrientRotationToMovement = true;
    Move->RotationRate = FRotator(0, 540, 0);
    Move->MaxWalkSpeed = 450.f;
    Move->MaxAcceleration = 1200.f;
    Move->BrakingDecelerationWalking = 1400.f;
    Move->bRunPhysicsWithNoController = true;
    Move->MaxStepHeight = 45.f;
    Move->bCanWalkOffLedges = false;
    // Ambient wildlife is not an enemy: monsters and the kill tracker must not treat it as one.
    Tags.Add(TEXT("Wildlife"));
    Tags.Add(TEXT("NoSkillTraining"));
}

void AColdSteelAnimal::LoadSpecies()
{
    const FString Wanted = SpeciesId.IsEmpty() ? ReplicatedSpeciesId : SpeciesId;
    Row = WildlifeCatalog::Get().Find(Wanted);
    if (!Row)
    {
        UE_LOG(LogTemp, Error, TEXT("WILDLIFE_SPECIES_MISSING id=%s actor=%s"), *Wanted, *GetName());
        bSpeciesReady = false;
        return;
    }
    bSpeciesReady = true;
}

FText AColdSteelAnimal::GetDisplayName() const
{
    return FText::FromString(Row ? Row->DisplayName : SpeciesId);
}

void AColdSteelAnimal::ApplySpecies(const FString& InSpeciesId)
{
    SpeciesId = InSpeciesId;
    LoadSpecies();
    if (!Row) return;
    if (HasAuthority()) ReplicatedSpeciesId = Row->Id;
    if (HasActorBegunPlay()) WildlifeAudio->SetSpecies(Row->Id);
    GetCapsuleComponent()->SetCapsuleSize(Row->CapsuleRadius, Row->CapsuleHalfHeight);
    auto* Move = GetCharacterMovement();
    Move->MaxWalkSpeed = Row->RunSpeed;
    Move->MaxAcceleration = FMath::Max(800.f, Row->RunSpeed * 3.f);
    Move->BrakingDecelerationWalking = FMath::Max(900.f, Row->RunSpeed * 3.5f);
    CorpseRagdoll->Rig = EMonsterCorpseRig::Canine;
    AlignVisual();
}

void AColdSteelAnimal::AlignVisual()
{
    if (!AnimationSet || !AnimationSet->ReferenceMesh) return;
    USkeletalMesh* Visual = AnimationSet->ReferenceMesh;
    GetMesh()->SetSkeletalMeshAsset(Visual);
    GetMesh()->SetRelativeRotation(FRotator(0, Row ? Row->MeshYaw : -90.f, 0));
    const FBoxSphereBounds Bounds = Visual->GetBounds();
    const float HalfHeight = GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight();
    GetMesh()->SetRelativeLocation(FVector(0, 0, -HalfHeight - (Bounds.Origin.Z - Bounds.BoxExtent.Z)));
}

void AColdSteelAnimal::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    LoadSpecies();
    if (!Row) return;
    GetCapsuleComponent()->SetCapsuleSize(Row->CapsuleRadius, Row->CapsuleHalfHeight);
    AlignVisual();
}

UQuadrupedTemplateAnimInstance* AColdSteelAnimal::Animation() const
{
    return Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance());
}

float AColdSteelAnimal::ClipLength(FName Action) const
{
    UAnimSequence* Clip = AnimationSet ? AnimationSet->FindSequence(Action) : nullptr;
    return Clip ? Clip->GetPlayLength() : 0.f;
}

void AColdSteelAnimal::SampleAction(FName Action, float SourceSeconds)
{
    if (auto* Anim = Animation())
    {
        if (Anim->ActiveAction != Action) Anim->PlayTemplateAction(Action, true);
        Anim->SetActionTime(SourceSeconds);
        if (SourceSeconds >= Anim->ActiveDefinition.BlendSeconds) Anim->FinishPoseTransition();
        GetMesh()->TickAnimation(0.f, false);
        GetMesh()->RefreshBoneTransforms();
    }
}

void AColdSteelAnimal::PostInitializeComponents()
{
    Super::PostInitializeComponents();
    if (GetWorld()->IsGameWorld() && HasAuthority() && !UWildlifeSubsystem::IsWildlifeMap(GetWorld())) Destroy();
}

void AColdSteelAnimal::BeginPlay()
{
    Super::BeginPlay();
    Home = GetActorLocation();
    LoadSpecies();
    if (!bSpeciesReady)
    {
        SetActorTickEnabled(false);
        return;
    }
    WildlifeAudio->SetSpecies(Row->Id);
    if (HasAuthority())
    {
        ReplicatedSpeciesId = Row->Id;
        MaxHealth = FMath::Max(1.f, Row->Health * static_cast<float>(MonsterCoreStats::HealthMultiplier()));
        Health = MaxHealth;
        ListenForHillsNoise();
        if (Row->Id == TEXT("crow"))
        {
            // Natural and F6 spawners finish assigning flocks after BeginPlay.
            GetWorldTimerManager().SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(this, [this]()
            {
                if (!bHillsGroup && !IsDead())
                    if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>()) Wildlife->RegisterHillsGroup({this});
            }));
        }
    }
    AlignVisual();
    if (!Animation() || !Animation()->SetAnimationSet(AnimationSet))
    {
        UE_LOG(LogTemp, Error, TEXT("WILDLIFE_ANIMATION_SET_MISSING species=%s actor=%s"), *Row->Id, *GetName());
        SetActorTickEnabled(false);
        return;
    }
    Animation()->bUseOwnerVelocity = true;
    GetMesh()->AddTickPrerequisiteActor(this);
    if (HasAuthority()) EnterState(EWildlifeState::Idle);
    else OnRep_Presentation();
}

void AColdSteelAnimal::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AColdSteelAnimal, Health);
    DOREPLIFETIME(AColdSteelAnimal, MaxHealth);
    DOREPLIFETIME(AColdSteelAnimal, Presentation);
    DOREPLIFETIME(AColdSteelAnimal, ReplicatedSpeciesId);
}

double AColdSteelAnimal::PresentationClock() const
{
    const auto* GameState = GetWorld()->GetGameState();
    return GameState ? GameState->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
}

void AColdSteelAnimal::OnRep_Presentation()
{
    // Initial replication can arrive before BeginPlay has bound the animation set.
    if (HasAuthority() || !HasActorBegunPlay() || !Row || !Animation()) return;
    HitAction = Presentation.HitAction;
    EnterState(Presentation.State);
    StateSeconds = FMath::Max(0., PresentationClock() - Presentation.StartedAt);
    if (State == EWildlifeState::Hit)
        SampleAction(HitAction, FMath::Min(StateSeconds, ClipLength(HitAction)));
    else if (State == EWildlifeState::Attack || State == EWildlifeState::Dying)
        TickPresentation(0.f);
}

void AColdSteelAnimal::ApplyDeadCollision()
{
    DistanceActivity->LeaveForDeath();
    // Falling birds still need world collision to land, but never block a player.
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    if (State != EWildlifeState::AirFall)
    {
        GetCharacterMovement()->DisableMovement();
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
}

void AColdSteelAnimal::EnterState(EWildlifeState NewState)
{
    if (!Row) return;
    if (HasAuthority() && NewState == EWildlifeState::Flee && State != NewState)
        WildlifeAudio->Signal(EHillsAnimalSound::Alarm);
    State = NewState;
    StateSeconds = 0.f;
    if (HasAuthority())
    {
        Presentation.State = State;
        Presentation.HitAction = HitAction;
        Presentation.StartedAt = PresentationClock();
        ++Presentation.Revision;
        ForceNetUpdate();
    }
    if (IsDead()) ApplyDeadCollision();
    auto* Anim = Animation();
    auto* Move = GetCharacterMovement();
    const bool bLocomoting = InFlockFlight() || NewState == EWildlifeState::Wander || NewState == EWildlifeState::Flee || NewState == EWildlifeState::Chase;
    if (Move && HasAuthority())
    {
        if (!bLocomoting && NewState != EWildlifeState::AirFall) Move->StopMovementImmediately();
        Move->MaxWalkSpeed = (NewState == EWildlifeState::Flee || NewState == EWildlifeState::Chase) ? Row->RunSpeed : Row->WalkSpeed;
        Move->bOrientRotationToMovement = bLocomoting;
    }
    if (!Anim) return;
    switch (NewState)
    {
    case EWildlifeState::Idle:
        Anim->ResumeLocomotion(.2f);
        IdleSeconds = Random.FRandRange(IdleMinSeconds, FMath::Max(IdleMinSeconds, IdleMaxSeconds));
        break;
    case EWildlifeState::Graze:
        if (!Anim->PlayTemplateAction(TEXT("RestEnter"), false))
            if (!Anim->PlayTemplateAction(TEXT("RestLoop"), false)) Anim->ResumeLocomotion(.2f);
        IdleSeconds = Random.FRandRange(IdleMinSeconds, IdleMaxSeconds);
        break;
    case EWildlifeState::HerdForage:
        if (!Anim->PlayTemplateAction(TEXT("Forage"))) Anim->ResumeLocomotion(.2f);
        IdleSeconds = Random.FRandRange(IdleMinSeconds, FMath::Max(IdleMinSeconds, IdleMaxSeconds));
        break;
    case EWildlifeState::Alert:
        if (!Anim->PlayTemplateAction(TEXT("LookAround"), false)) Anim->ResumeLocomotion(.15f);
        break;
    case EWildlifeState::Wander:
        Anim->ResumeLocomotion(.2f);
        if (HasAuthority() && !bHillsGroup) PickWanderPoint();
        break;
    case EWildlifeState::Flee:
    case EWildlifeState::Chase:
        Anim->ResumeLocomotion(.12f);
        break;
    case EWildlifeState::Hit:
        if (!Anim->PlayTemplateAction(HitAction, !HasAuthority())) Anim->ResumeLocomotion(.1f);
        break;
    case EWildlifeState::Attack:
        bAttackConsumed = false;
        Anim->PlayTemplateAction(TEXT("AttackBite"), true);
        break;
    case EWildlifeState::Dying:
        Anim->PlayTemplateAction(TEXT("Death"), true);
        break;
    case EWildlifeState::TakeOff: Anim->PlayTemplateAction(TEXT("TakeOff")); break;
    case EWildlifeState::Fly: Anim->PlayTemplateAction(TEXT("Fly")); break;
    case EWildlifeState::Glide: Anim->PlayTemplateAction(TEXT("Glide")); break;
    case EWildlifeState::Land: Anim->PlayTemplateAction(TEXT("Land")); break;
    case EWildlifeState::AirFall: Anim->PlayTemplateAction(TEXT("AirFall")); break;
    case EWildlifeState::Corpse:
        if (!HasAuthority() && !CorpseRagdoll->WasAttempted() && !CorpseRagdoll->IsFrozen())
        {
            const float End = ClipLength(TEXT("Death"));
            SampleAction(TEXT("Death"), Row->bUseRagdoll ? End * DeathAnimationFraction : End);
            if (!Row->bUseRagdoll || !CorpseRagdoll->Start(GetMesh())) CorpseRagdoll->FreezeAnimatedPose(GetMesh());
        }
        break;
    default:
        break;
    }
}

void AColdSteelAnimal::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bSpeciesReady || !Row) return;
    if (GetNetMode() != NM_DedicatedServer && (Row->Id == TEXT("boar") || Row->Id.StartsWith(TEXT("deer_"))))
    {
        const auto* Anim = Animation();
        const bool bRunning = State == EWildlifeState::Flee && GetCharacterMovement()->IsMovingOnGround()
            && GetVelocity().SizeSquared2D() > FMath::Square(Row->WalkSpeed) && Anim && Anim->ActiveAction.IsNone();
        const float Phase = Anim && AnimationSet ? FMath::Frac(Anim->GaitPhase + AnimationSet->RunPhaseOffset) : 0.f;
        WildlifeAudio->UpdateHooves(bRunning, Phase, GetCharacterMovement()->GetActorFeetLocation());
    }
    if (!HasAuthority())
    {
        TickPresentation(DeltaSeconds);
        return;
    }
    TickAuthoritative(DeltaSeconds);
}

void AColdSteelAnimal::TickPresentation(float DeltaSeconds)
{
    StateSeconds = FMath::Max(0., PresentationClock() - Presentation.StartedAt);
    if (State == EWildlifeState::Dying)
    {
        const float End = ClipLength(TEXT("Death"));
        SampleAction(TEXT("Death"), FMath::Min(StateSeconds, End));
        // Only the replicated Corpse transition starts client physics. Do not
        // mutate the authoritative state locally while its packet is in flight.
        CorpseRagdoll->RecordDeathPose(GetMesh(), DeltaSeconds, true);
    }
    else if (State == EWildlifeState::Attack)
    {
        SampleAction(TEXT("AttackBite"), FMath::Min(StateSeconds, ClipLength(TEXT("AttackBite"))));
    }
    else if (State == EWildlifeState::Hit)
        SampleAction(HitAction, FMath::Min(StateSeconds, ClipLength(HitAction)));
}

bool AColdSteelAnimal::InFlockFlight() const
{
    return State == EWildlifeState::TakeOff || State == EWildlifeState::Fly ||
        State == EWildlifeState::Glide || State == EWildlifeState::Land;
}

void AColdSteelAnimal::SetHerdOrder(const FVector& Waypoint, bool bAtSlot, bool bRun, bool bPanic)
{
    if (!HasAuthority() || IsDead()) return;
    bHillsGroup = true;
    GroupWaypoint = Waypoint;
    bHerdAtSlot = bAtSlot;
    bHerdRun = bRun;
    bHerdPanic = bPanic;
    if (InFlockFlight())
    {
        GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        EnterState(EWildlifeState::Idle);
        ForceNetUpdate();
    }
}

void AColdSteelAnimal::ListenForHillsNoise()
{
    auto* Listener = NewObject<UAIPerceptionComponent>(this);
    auto* Hearing = NewObject<UAISenseConfig_Hearing>(Listener);
    Hearing->HearingRange = 3600.f;
    Hearing->SetMaxAge(2.f);
    Hearing->DetectionByAffiliation = FAISenseAffiliationFilter(true, true, true);
    Listener->ConfigureSense(*Hearing);
    Listener->OnTargetPerceptionUpdated.AddDynamic(this, &AColdSteelAnimal::OnHillsNoise);
    AddInstanceComponent(Listener);
    Listener->RegisterComponent();
}

void AColdSteelAnimal::OnHillsNoise(AActor* Source, FAIStimulus Stimulus)
{
    if (!HasAuthority() || IsDead() || IsDistancePaused() || !Source || !Stimulus.WasSuccessfullySensed()) return;
    if (Stimulus.Tag != TEXT("Gunshot") && Stimulus.Tag != TEXT("GunshotSuppressed")) return;
    if (GetWorld()->GetTimeSeconds() >= ThreatUntil) WildlifeAudio->Signal(EHillsAnimalSound::Alarm);
    RememberThreat(Stimulus.StimulusLocation);
}

void AColdSteelAnimal::RememberThreat(const FVector& Source)
{
    if (IsDistancePaused()) return;
    ThreatPosition = Source;
    ThreatUntil = GetWorld()->GetTimeSeconds() + 6.;
    if (bHillsGroup)
        if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>()) Wildlife->AlarmHillsGroup(this, Source);
}

void AColdSteelAnimal::SetFlightOrder(const FVector& Waypoint, EWildlifeState Phase, bool bAlarm)
{
    if (!HasAuthority() || IsDead() || !Row || State == EWildlifeState::Hit) return;
    bHillsGroup = true;
    GroupWaypoint = Waypoint;
    auto* Move = GetCharacterMovement();
    if (bAlarm && !bHerdPanic) WildlifeAudio->Signal(EHillsAnimalSound::Alarm);
    bHerdPanic = bAlarm;
    if (!Move->IsFlying())
    {
        WildlifeAudio->Signal(EHillsAnimalSound::TakeOff);
        Move->SetMovementMode(MOVE_Flying);
        Move->BrakingDecelerationFlying = 1650.f;
    }
    if (State != Phase)
    {
        EnterState(Phase);
        ForceNetUpdate();
    }
}

void AColdSteelAnimal::TickHillsOrder(float DeltaSeconds)
{
    if (InFlockFlight())
    {
        const FVector Delta = GroupWaypoint - GetActorLocation();
        const float Cruise = WildlifeCatalog::Get().HillsGroups.FlightSpeed;
        GetCharacterMovement()->MaxFlySpeed = FMath::Clamp(float(Delta.Size() * 2.4), 80.f, Cruise * 1.35f);
        if (Delta.SizeSquared() > 25.) AddMovementInput(Delta.GetSafeNormal(), 1.f, true);
        return;
    }
    if (bHerdAtSlot)
    {
        if (State != EWildlifeState::Idle && State != EWildlifeState::HerdForage)
            EnterState(EWildlifeState::Idle);
        else if (Row->Id != TEXT("crow") && StateSeconds >= IdleSeconds)
            EnterState(State == EWildlifeState::Idle ? EWildlifeState::HerdForage : EWildlifeState::Idle);
        StuckSeconds = 0.f;
        return;
    }
    const EWildlifeState Travel = bHerdPanic ? EWildlifeState::Flee : EWildlifeState::Wander;
    if (State != Travel) EnterState(Travel);
    const float Speed = bHerdPanic ? Row->RunSpeed : (bHerdRun ? Row->RunSpeed * .78f : Row->WalkSpeed);
    GetCharacterMovement()->MaxWalkSpeed = Speed;
    const FVector Delta = GroupWaypoint - GetActorLocation();
    if (Delta.SizeSquared2D() > FMath::Square(25.)) AddMovementInput(Delta.GetSafeNormal2D(), 1.f, true);
    if (bHerdPanic && Row->Attack.Damaging() && BlockedTooLong(DeltaSeconds) && AttackCooldownLeft <= 0.f)
    {
        // Preserve the cornered boar/stag reaction at contact distance.
        for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        {
            APlayerController* PC = It->Get();
            APawn* Pawn = PC ? PC->GetPawn() : nullptr;
            if (Pawn && FVector::Dist(Pawn->GetActorLocation(), GetActorLocation()) <= Row->Attack.Range)
            {
                const auto* Vitals = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
                if (!Vitals || !Vitals->IsDead()) { StartAttack(Pawn); break; }
            }
        }
    }
}

void AColdSteelAnimal::Landed(const FHitResult& Hit)
{
    Super::Landed(Hit);
    if (HasAuthority() && State == EWildlifeState::AirFall)
    {
        GetCharacterMovement()->DisableMovement();
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        EnterState(EWildlifeState::Dying);
        if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>()) Wildlife->DropLoot(*this, *Row, Hit.ImpactPoint);
        ForceNetUpdate();
    }
}

void AColdSteelAnimal::StartAttack(APawn* Victim)
{
    if (!Row->Attack.Damaging() || AttackCooldownLeft > 0.f || !IsValid(Victim)
        || !WildlifeMeleeClear(*this,*Victim,Row->Attack.Range * 1.2f)) return;
    Target = Victim;
    AttackCooldownLeft = Row->Attack.Cooldown;
    if (IsValid(Victim))
    {
        const FVector Dir = (Victim->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
        SetActorRotation(FRotator(0, Dir.Rotation().Yaw, 0));
    }
    EnterState(EWildlifeState::Attack);
}

void AColdSteelAnimal::TryContact()
{
    if (bAttackConsumed || !Target.IsValid()) return;
    APawn* Victim = Target.Get();
    const UFPSCombatHealthComponent* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Vitals && Vitals->IsDead()) return;
    const FVector Offset = Victim->GetActorLocation() - GetActorLocation();
    if (!WildlifeMeleeClear(*this,*Victim,Row->Attack.Range * 1.2f)) return;
    if (FVector::DotProduct(GetActorForwardVector(), Offset.GetSafeNormal2D()) < .2f) return;
    bAttackConsumed = true;
    UGameplayStatics::ApplyDamage(Victim, Row->Attack.Damage, nullptr, this, UEnemyMeleeDamage::StaticClass());
}

void AColdSteelAnimal::FinishAttack()
{
    AttackCooldownLeft = FMath::Max(AttackCooldownLeft, Row->Attack.Cooldown);
    Target.Reset();
    EnterState(EWildlifeState::Idle);
}

void AColdSteelAnimal::TickAuthoritative(float DeltaSeconds)
{
    StateSeconds += DeltaSeconds;
    AttackCooldownLeft = FMath::Max(0.f, AttackCooldownLeft - DeltaSeconds);

    if (State == EWildlifeState::Corpse || State == EWildlifeState::AirFall) return;
    if (State == EWildlifeState::Dying)
    {
        const float End = ClipLength(TEXT("Death"));
        const float Handoff = End * FMath::Clamp(DeathAnimationFraction, 0.f, 1.f);
        SampleAction(TEXT("Death"), FMath::Min(StateSeconds, End));
        CorpseRagdoll->RecordDeathPose(GetMesh(), DeltaSeconds, true);
        if (Row->bUseRagdoll && StateSeconds >= Handoff) EnterRagdoll();
        else if (!Row->bUseRagdoll && StateSeconds >= End)
        {
            SampleAction(TEXT("Death"), End);
            CorpseRagdoll->FreezeAnimatedPose(GetMesh());
            EnterState(EWildlifeState::Corpse);
        }
        return;
    }

    if (bHillsGroup && State != EWildlifeState::Hit && State != EWildlifeState::Attack)
    {
        TickHillsOrder(DeltaSeconds);
        return;
    }
    const double Now = GetWorld()->GetTimeSeconds();
    if (!bHillsGroup && Now < ThreatUntil && (State != EWildlifeState::Hit || StateSeconds >= HitSeconds))
    {
        if (State != EWildlifeState::Flee)
        {
            Target.Reset();
            EnterState(EWildlifeState::Flee);
            NextEscapeStep = 0.;
        }
        if (Now >= NextEscapeStep)
        {
            Goal = GetActorLocation();
            if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>())
                Wildlife->FindEscapeStep(*this, ThreatPosition, Goal);
            NextEscapeStep = Now + .45;
        }
        SteerTo(Goal, Row->RunSpeed, 45.f);
        return;
    }
    APawn* Threat = nullptr;
    float Distance = MAX_flt;
    const bool bPlayerNear = PlayerThreat(Threat, Distance);

    if (State == EWildlifeState::Hit)
    {
        if (StateSeconds >= HitSeconds)
        {
            if (bHillsGroup) { EnterState(EWildlifeState::Idle); return; }
            if (Threat && Row->Attack.Damaging() && (Row->Aggressive() || Health / MaxHealth < .5f))
            {
                Target = Threat;
                EnterState(EWildlifeState::Chase);
            }
            else
            {
                PickFleePoint(Threat);
                EnterState(EWildlifeState::Flee);
            }
        }
        return;
    }

    if (State == EWildlifeState::Attack)
    {
        if (!Target.IsValid() || StateSeconds > ClipLength(TEXT("AttackBite")) + .05f)
        {
            FinishAttack();
            return;
        }
        SampleAction(TEXT("AttackBite"), FMath::Min(StateSeconds, ClipLength(TEXT("AttackBite"))));
        if (Row->Attack.Damaging() && StateSeconds >= Row->Attack.ContactStart && StateSeconds < Row->Attack.ContactEnd)
            TryContact();
        return;
    }

    if (State == EWildlifeState::Chase)
    {
        if (!bPlayerNear || Distance > FMath::Max(Row->LeashRadius, Row->AggroRadius * 1.6f))
        {
            Target.Reset();
            EnterState(EWildlifeState::Idle);
            return;
        }
        if (Distance <= Row->Attack.Range && AttackCooldownLeft <= 0.f && Row->Attack.Damaging())
        {
            StartAttack(Threat);
            return;
        }
        SteerTo(Threat->GetActorLocation(), Row->RunSpeed, Row->Attack.Range * .8f);
        if (BlockedTooLong(DeltaSeconds)) EnterState(EWildlifeState::Idle);
        return;
    }

    if (State == EWildlifeState::Flee)
    {
        if (!Threat || Distance > Row->FleeRadius * 2.2f || StateSeconds > 8.f)
        {
            Home = GetActorLocation();
            EnterState(EWildlifeState::Idle);
            return;
        }
        SteerTo(Goal, Row->RunSpeed, 150.f);
        if (BlockedTooLong(DeltaSeconds))
        {
            // Cornered: retaliate when the species can, otherwise slide along the obstacle.
            if (Row->Attack.Damaging() && Distance < Row->Attack.Range * 1.2f && AttackCooldownLeft <= 0.f) StartAttack(Threat);
            else { PickFleePoint(Threat); StuckSeconds = 0.f; }
        }
        return;
    }

    if (State == EWildlifeState::Wander)
    {
        SteerTo(Goal, Row->WalkSpeed, 90.f);
        if (FVector::Dist2D(Goal, GetActorLocation()) <= 90.f || BlockedTooLong(DeltaSeconds))
            EnterState(EWildlifeState::Idle);
        return;
    }

    if (State == EWildlifeState::Alert)
    {
        if (!bPlayerNear || Distance > Row->AlertRadius * 1.15f) { EnterState(EWildlifeState::Idle); return; }
        if (Distance <= Row->FleeRadius) { PickFleePoint(Threat); EnterState(EWildlifeState::Flee); return; }
        if (StateSeconds >= FMath::Max(.8f, ClipLength(TEXT("LookAround")))) EnterState(EWildlifeState::Idle);
        return;
    }

    // Idle / Graze share the reaction window.
    if (bPlayerNear)
    {
        if (Row->Aggressive() && Distance <= Row->AggroRadius && Row->Attack.Damaging())
        {
            Target = Threat;
            EnterState(EWildlifeState::Chase);
            return;
        }
        if (Distance <= Row->FleeRadius)
        {
            PickFleePoint(Threat);
            EnterState(EWildlifeState::Flee);
            return;
        }
        if (Distance <= Row->AlertRadius && StateSeconds > .6f)
        {
            EnterState(EWildlifeState::Alert);
            return;
        }
    }
    if (StateSeconds >= IdleSeconds)
        EnterState(Random.FRand() < .4f ? EWildlifeState::Graze : EWildlifeState::Wander);
}

float AColdSteelAnimal::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    if (!HasAuthority() || IsDead() || Damage <= 0.f) return 0.f;
    IncomingHit = Causer ? GetActorLocation() - Causer->GetActorLocation() : -GetActorForwardVector();
    if (Event.IsOfType(FPointDamageEvent::ClassID))
        IncomingHit = static_cast<const FPointDamageEvent&>(Event).ShotDirection;
    const float Applied = FMath::Min(Health, FMath::Max(0.f,
        CombatFormulaRuntime::MitigateMonster(this, Damage,
            Event.DamageTypeClass ? Event.DamageTypeClass->GetDefaultObject<UDamageType>() : nullptr, Causer)));
    if (Applied <= 0.f) return 0.f;
    Health -= Applied;
    Super::TakeDamage(Applied, Event, EventInstigator, Causer);
    const AActor* Source = EventInstigator && EventInstigator->GetPawn() ? static_cast<AActor*>(EventInstigator->GetPawn().Get()) : Causer;
    if (Source && Source != this) RememberThreat(Source->GetActorLocation());
    if (Health <= 0.f)
    {
        Die(EventInstigator);
        return Applied;
    }
    WildlifeAudio->Signal(EHillsAnimalSound::Hurt);
    if (Event.IsOfType(FPointDamageEvent::ClassID))
    {
        const auto& Hit = static_cast<const FPointDamageEvent&>(Event).HitInfo;
        MulticastModelHit(Hit.BoneName, Hit.ImpactPoint, IncomingHit.GetSafeNormal(), Applied);
    }
    if (InFlockFlight() || Event.DamageTypeClass == UWildlifeGunDamage::StaticClass()) return Applied;
    // Directional flinch, then retaliate or run.
    const float Side = FVector::DotProduct(-IncomingHit.GetSafeNormal2D(), GetActorRightVector());
    HitAction = Side > .4f ? TEXT("HitRight") : Side < -.4f ? TEXT("HitLeft") : TEXT("HitFront");
    HitSeconds = FMath::Max(.25f, ClipLength(HitAction) * .8f);
    if (APawn* Attacker = EventInstigator ? EventInstigator->GetPawn().Get() : Cast<APawn>(Causer)) Target = Attacker;
    EnterState(EWildlifeState::Hit);
    return Applied;
}

void AColdSteelAnimal::MulticastModelHit_Implementation(FName Bone, FVector_NetQuantize Point,
    FVector_NetQuantizeNormal Direction, float Applied)
{
    if (IsDead() || GetNetMode() == NM_DedicatedServer) return;
    FHitResult Hit;
    Hit.BoneName = Bone;
    Hit.ImpactPoint = Point;
    if (auto* Body = Cast<UMonsterIdleBreathingMeshComponent>(GetMesh())) Body->AddGunHitFeedback(Hit, Direction, Applied);
}

void AColdSteelAnimal::Die(AController* Killer)
{
    if (IsDead()) return;
    DistanceActivity->LeaveForDeath();
    WildlifeAudio->Signal(EHillsAnimalSound::Death);
    CorpseRagdoll->PrepareDeath(GetMesh());
    const bool bAirborne = InFlockFlight();
    if (bAirborne) GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    else
    {
        GetCharacterMovement()->DisableMovement();
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    EnterState(bAirborne ? EWildlifeState::AirFall : EWildlifeState::Dying);
    ForceNetUpdate();
    if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>())
    {
        Wildlife->BeginCorpse(*this, *Row);
        if (!bAirborne) Wildlife->DropLoot(*this, *Row, GetActorLocation());
    }
    ColdSteelSkills::NotifyKillByOwner(GetGameInstance(), Killer, this);
    ColdSteelSkills::AwardKillByOwner(GetGameInstance(), Killer, this, Row->Experience);
}

void AColdSteelAnimal::EnterRagdoll()
{
    if (!HasAuthority() || State != EWildlifeState::Dying) return;
    if (!CorpseRagdoll->Start(GetMesh()))
        CorpseRagdoll->FreezeAnimatedPose(GetMesh());
    EnterState(EWildlifeState::Corpse);
}

void AColdSteelAnimal::LifeSpanExpired()
{
    // Terrain collision can stream out while a dead bird is still falling.
    if (HasAuthority() && State == EWildlifeState::AirFall && Row)
        if (auto* Wildlife = GetWorld()->GetSubsystem<UWildlifeSubsystem>()) Wildlife->DropLoot(*this, *Row, GetActorLocation());
    Super::LifeSpanExpired();
}

bool AColdSteelAnimal::IsDistancePaused() const
{
    return DistanceActivity->IsDistancePaused();
}

void AColdSteelAnimal::ResumeWildlifeStateClock()
{
    if (!HasAuthority()) return;
    Presentation.StartedAt = PresentationClock() - StateSeconds;
    ++Presentation.Revision;
    ForceNetUpdate();
}

void AColdSteelAnimal::EndPlay(const EEndPlayReason::Type Reason)
{
    Target.Reset();
    Super::EndPlay(Reason);
}
