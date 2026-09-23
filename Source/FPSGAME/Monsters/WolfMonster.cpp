#include "WolfMonster.h"
#include "ZombieDogAppearanceComponent.h"
#include "QuadrupedAnimationTemplate.h"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "MonsterAIController.h"
#include "MonsterCharacterMovementComponent.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "UObject/ConstructorHelpers.h"

AWolfMonster::AWolfMonster(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick = true;
    Combat = CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    WoundAppearance = CreateDefaultSubobject<UZombieDogAppearanceComponent>(TEXT("WoundAppearance"));
    Combat->PoiseThreshold = 40.f; Combat->StaggerDuration = .45f; Combat->StunDuration = 1.1f;
    DeathAnimationFraction = MonsterCombatTuning::DeathAnimationFraction;
    GetCapsuleComponent()->InitCapsuleSize(34.f, 60.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetMesh()->SetAnimInstanceClass(UQuadrupedTemplateAnimInstance::StaticClass());
    bUseControllerRotationYaw = false;
    BaseEyeHeight = 15.f;
    auto* Move = GetCharacterMovement();
    Move->bOrientRotationToMovement = true;
    Move->RotationRate = FRotator(0, 360, 0);
    Move->MaxWalkSpeed = ChaseSpeed;
    Move->MaxAcceleration = 1400.f;
    Move->BrakingDecelerationWalking = 1600.f;
    Move->bRunPhysicsWithNoController = true;
    Move->MaxStepHeight = 40.f;
    Move->bCanWalkOffLedges = false;
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    static ConstructorHelpers::FClassFinder<AMonsterAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    AIControllerClass = AI.Succeeded() ? AI.Class.Get() : AMonsterAIController::StaticClass();
    Tags.Add(TEXT("Enemy")); Tags.Add(TEXT("Wolf"));
}

void AWolfMonster::AlignVisual()
{
    if (!AnimationSet || !AnimationSet->ReferenceMesh) return;
    USkeletalMesh* Visual = AnimationSet->ReferenceMesh;
    GetMesh()->SetSkeletalMeshAsset(Visual);
    // The source wolf faces component +Y; UE Character movement faces +X.
    GetMesh()->SetRelativeRotation(FRotator(0, -90.f, 0));
    const auto Bounds = Visual->GetBounds();
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() - (Bounds.Origin.Z - Bounds.BoxExtent.Z)));
}
void AWolfMonster::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform); AlignVisual();
    WoundAppearance->ApplyAppearance(GetMesh());
}
UQuadrupedTemplateAnimInstance* AWolfMonster::Animation() const { return Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance()); }
float AWolfMonster::ClipLength(FName Action) const
{
    UAnimSequence* Clip = AnimationSet ? AnimationSet->FindSequence(Action) : nullptr;
    return Clip ? Clip->GetPlayLength() : 0.f;
}
void AWolfMonster::BeginPlay()
{
    Super::BeginPlay();
    Home = GetActorLocation(); MaxHealth*=static_cast<float>(MonsterCoreStats::HealthMultiplier()); Health = FMath::Max(1.f, MaxHealth); // 全局生命成长层；归巢回血读取的也是放大后的 MaxHealth
    AlignVisual();
    WoundAppearance->ApplyAppearance(GetMesh());
    if (!Animation() || !Animation()->SetAnimationSet(AnimationSet))
    {
        UE_LOG(LogTemp, Error, TEXT("WOLF_ANIMATION_SET_MISSING %s"), *GetName());
        SetActorTickEnabled(false); return;
    }
    Animation()->bUseOwnerVelocity = true;
    // Character state and contact sampling precede presentation's ordinary tick.
    GetMesh()->AddTickPrerequisiteActor(this);
    GetMesh()->AddTickPrerequisiteComponent(Combat);
    EnterState(EWolfState::Idle);
    if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
}
bool AWolfMonster::Busy() const
{
    return Dead() || State == EWolfState::Howl || State == EWolfState::Bite || State == EWolfState::Pounce || State == EWolfState::Stagger || State == EWolfState::Recovery;
}
FVector AWolfMonster::Mouth() const
{
    return GetMesh()->GetSocketLocation(TEXT("Wolf_-Head")) + GetActorForwardVector() * 18.f;
}
bool AWolfMonster::CanSee(const AActor* Actor) const
{
    if (!IsValid(Actor)) return false;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WolfSight), false, this);
    Query.AddIgnoredActor(Actor);
    return !GetWorld()->LineTraceSingleByChannel(Hit, Mouth(), Actor->GetActorLocation(), ECC_Visibility, Query);
}
bool AWolfMonster::CanAttack(APawn* Victim) const
{
    if (!IsValid(Victim) || Busy() || !GetCharacterMovement()->IsMovingOnGround()) return false;
    const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Vitals && Vitals->IsDead()) return false;
    const FVector Offset = Victim->GetActorLocation() - GetActorLocation();
    if (FMath::Abs(Offset.Z) > 120.f || !CanSee(Victim)) return false;
    const float Distance = Offset.Size2D();
    if (bHowlOnEncounter && !bHasAlerted && Distance > PounceMinRange && Distance <= AggroRadius && ClipLength(TEXT("Howl")) > 0.f) return true;
    const auto* Bite = AnimationSet ? AnimationSet->FindAction(TEXT("AttackBite")) : nullptr;
    const auto* Pounce = AnimationSet ? AnimationSet->FindAction(TEXT("AttackPounce")) : nullptr;
    return (Distance <= BiteTriggerRange && BiteCooldownLeft <= 0.f && Bite && Bite->ContactStartSeconds >= 0.f && Bite->ContactEndSeconds > Bite->ContactStartSeconds)
        || (Distance >= PounceMinRange && Distance <= PounceMaxRange && PounceCooldownLeft <= 0.f && Pounce && Pounce->ContactStartSeconds >= 0.f && Pounce->ContactEndSeconds > Pounce->ContactStartSeconds);
}
bool AWolfMonster::StartAttack(APawn* Victim)
{
    if (!HasAuthority() || !CanAttack(Victim)) return false;
    Target = Victim;
    AttackDirection = (Victim->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
    SetActorRotation(AttackDirection.Rotation());
    const float Distance = FVector::Dist2D(Victim->GetActorLocation(), GetActorLocation());
    if (bHowlOnEncounter && !bHasAlerted && Distance > PounceMinRange && ClipLength(TEXT("Howl")) > 0.f)
    {
        bHasAlerted = true; bPackAlertSent = false;
        EnterState(EWolfState::Howl);
    }
    else if (Distance <= BiteTriggerRange)
    {
        bHasAlerted = true; BiteCooldownLeft = BiteCooldown;
        EnterState(EWolfState::Bite);
    }
    else
    {
        bHasAlerted = true; PounceCooldownLeft = PounceCooldown;
        PounceOrigin = GetActorLocation();
        // Lock the landing direction/length now. A sidestep can evade the pounce.
        PounceDistance = FMath::Clamp(Distance - 110.f, 0.f, PounceMaxRange - 110.f);
        LastPounceSourceTime = 0.f; bPounceBlocked = false;
        EnterState(EWolfState::Pounce);
    }
    if (auto* AI = Cast<AMonsterAIController>(GetController())) { AI->StopMovement(); AI->UpdateKnowledge(); }
    return true;
}
void AWolfMonster::EnterState(EWolfState NewState)
{
    State = NewState; StateSeconds = 0.f;
    const bool Moving = State == EWolfState::Chase || State == EWolfState::Returning;
    GetCharacterMovement()->bOrientRotationToMovement = Moving;
    GetCharacterMovement()->MaxWalkSpeed = State == EWolfState::Returning ? WalkSpeed : ChaseSpeed;
    if (!Moving) GetCharacterMovement()->StopMovementImmediately();
    if (auto* Anim = Animation())
    {
        if (State == EWolfState::Bite || State == EWolfState::Pounce)
        {
            bAttackConsumed = false; bAttackAnimationStarted = false;
            Anim->PlayTemplateAction(TEXT("IdleAlert"), false);
        }
        else if (State == EWolfState::Howl) Anim->PlayTemplateAction(TEXT("Howl"), true);
        else if (State == EWolfState::Dying) Anim->PlayTemplateAction(TEXT("Death"), true);
        else if (State != EWolfState::Stagger && State != EWolfState::Ragdoll) Anim->ResumeLocomotion(.15f);
    }
}
void AWolfMonster::SetLocomotion(bool bMoving, bool bReturning)
{
    if (Busy()) return;
    const EWolfState Next = bMoving ? (bReturning ? EWolfState::Returning : EWolfState::Chase) : EWolfState::Idle;
    if (State != Next) EnterState(Next);
}
void AWolfMonster::ReachedHome()
{
    Health = MaxHealth; bHasAlerted = false; Target.Reset();
    SetLocomotion(false, false);
}
void AWolfMonster::SampleAction(FName Action, float SourceSeconds)
{
    if (auto* Anim = Animation())
    {
        if (Anim->ActiveAction != Action) Anim->PlayTemplateAction(Action, true);
        Anim->SetActionTime(SourceSeconds);
        if (SourceSeconds >= Anim->ActiveDefinition.BlendSeconds) Anim->FinishPoseTransition();
        // Evaluate the source contact pose before querying its mouth position.
        GetMesh()->TickAnimation(0.f, false);
        GetMesh()->RefreshBoneTransforms();
    }
}
void AWolfMonster::TryContact(float SourceSeconds)
{
    if (bAttackConsumed || !Target.IsValid() || !CanSee(Target.Get())) return;
    const auto* Vitals = Target->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Vitals && Vitals->IsDead()) return;
    const FVector Offset = Target->GetActorLocation() - GetActorLocation();
    if (Offset.Size2D() > BiteTriggerRange + 35.f || FVector::DotProduct(AttackDirection, Offset.GetSafeNormal2D()) < .35f) return;
    auto* TargetBody = Cast<UPrimitiveComponent>(Target->GetRootComponent());
    FVector Closest;
    if (!TargetBody || TargetBody->GetClosestPointOnCollision(Mouth(), Closest) < 0.f || FVector::DistSquared(Mouth(), Closest) > FMath::Square(ContactRadius)) return;
    // Consume before the callback: parry can synchronously cancel this attack.
    bAttackConsumed = true;
    const float Damage = State == EWolfState::Pounce ? PounceDamage : BiteDamage;
    const float Applied = UGameplayStatics::ApplyDamage(Target.Get(), Damage, GetController(), this, UEnemyMeleeDamage::StaticClass());
    if (Applied > 0.f) ++SuccessfulHits;
}
void AWolfMonster::AdvancePounce(float SourceSeconds)
{
    if (bPounceBlocked || LastPounceSourceTime >= PounceTravelEnd || SourceSeconds < PounceTravelStart || PounceTravelEnd <= PounceTravelStart) return;
    auto* Move = GetCharacterMovement();
    if (!bPounceMovement)
    {
        bPounceMovement = true;
        Move->SetMovementMode(MOVE_Flying);
        Move->StopMovementImmediately();
    }
    const float End = FMath::Min(SourceSeconds, PounceTravelEnd);
    float Time = FMath::Max(LastPounceSourceTime, PounceTravelStart);
    while (Time < End - SMALL_NUMBER)
    {
        Time = FMath::Min(End, Time + 1.f / 60.f);
        const float Alpha = (Time - PounceTravelStart) / (PounceTravelEnd - PounceTravelStart);
        const FVector Desired = PounceOrigin + AttackDirection * (PounceDistance * Alpha)
            + FVector(0, 0, FMath::Sin(Alpha * PI) * PounceArcHeight);
        FHitResult Hit;
        Move->SafeMoveUpdatedComponent(Desired - GetActorLocation(), GetActorQuat(), true, Hit);
        if (Hit.bBlockingHit)
        {
            bPounceBlocked = true;
            if (Hit.GetActor() != Target.Get()) bAttackConsumed = true;
            break;
        }
    }
    LastPounceSourceTime = End;
    if (bPounceBlocked || SourceSeconds >= PounceTravelEnd) FinishPounceMovement();
}
void AWolfMonster::FinishPounceMovement()
{
    if (!bPounceMovement) return;
    bPounceMovement = false;
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    GetCharacterMovement()->bForceNextFloorCheck = true;
}
void AWolfMonster::AdvanceAttack(float PreviousSeconds)
{
    const EWolfState AttackState = State;
    const FName Action = State == EWolfState::Pounce ? TEXT("AttackPounce") : TEXT("AttackBite");
    const float Windup = State == EWolfState::Pounce ? PounceWindup : BiteWindup;
    const float Now = FMath::Max(0.f, StateSeconds - Windup);
    const float Before = FMath::Max(0.f, PreviousSeconds - Windup);
    if (StateSeconds < Windup) return;
    if (!bAttackAnimationStarted)
    {
        bAttackAnimationStarted = true;
        if (auto* Anim = Animation()) Anim->PlayTemplateAction(Action, true);
    }
    SetActorRotation(AttackDirection.Rotation());
    const auto* Definition = AnimationSet->FindAction(Action);
    const bool InContact = Definition && Definition->ContactStartSeconds >= 0.f
        && Before < Definition->ContactEndSeconds && Now >= Definition->ContactStartSeconds;
    // If a long frame crosses the complete window, consume the contact pose before
    // advancing to the recovery pose. Both movement and animation use source time.
    if (InContact && !bAttackConsumed)
    {
        const float Contact = FMath::Clamp(Now, Definition->ContactStartSeconds, Definition->ContactEndSeconds - .0001f);
        if (State == EWolfState::Pounce) AdvancePounce(Contact);
        SampleAction(Action, Contact);
        TryContact(Contact);
        if (State != AttackState) return;
    }
    if (State == EWolfState::Pounce) AdvancePounce(Now);
    SampleAction(Action, FMath::Min(Now, ClipLength(Action)));
    if (Now >= ClipLength(Action))
    {
        FinishPounceMovement();
        RecoverySeconds = AttackState == EWolfState::Pounce ? PounceRecovery : BiteRecovery;
        EnterState(EWolfState::Recovery);
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
    }
}
void AWolfMonster::AlertPack()
{
    bPackAlertSent = true;
    if (!Target.IsValid()) return;
    for (TActorIterator<AWolfMonster> It(GetWorld()); It; ++It)
    {
        AWolfMonster* Other = *It;
        if (Other == this || Other->Dead() || Other->Target.IsValid() || FVector::DistSquared2D(GetActorLocation(), Other->GetActorLocation()) > FMath::Square(PackAlertRadius)) continue;
        // Share a last-known target; the existing perception/LOS rules still
        // determine whether it can attack. Receiving an alert never chains howls.
        Other->bHasAlerted = true;
        if (auto* AI = Cast<AMonsterAIController>(Other->GetController())) AI->RememberDamage(Target.Get());
    }
}
void AWolfMonster::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!HasAuthority()) return;
    const float Previous = StateSeconds;
    StateSeconds += FMath::Max(0.f, DeltaSeconds);
    BiteCooldownLeft = FMath::Max(0.f, BiteCooldownLeft - DeltaSeconds);
    PounceCooldownLeft = FMath::Max(0.f, PounceCooldownLeft - DeltaSeconds);
    if (State == EWolfState::Dying)
    {
        const float Handoff = ClipLength(TEXT("Death")) * FMath::Clamp(DeathAnimationFraction, 0.f, 1.f);
        SampleAction(TEXT("Death"), FMath::Min(StateSeconds, bUseRagdoll ? Handoff : ClipLength(TEXT("Death"))));
        if (bUseRagdoll && StateSeconds >= Handoff) EnterRagdoll();
        return;
    }
    if (State == EWolfState::Ragdoll)
    {
        if (!bCorpseSleeping && StateSeconds > 5.f) { GetMesh()->PutAllRigidBodiesToSleep(); bCorpseSleeping = true; }
        return;
    }
    if (State == EWolfState::Stagger) { if (StateSeconds >= ReactionSeconds) Combat->FinishReaction(); return; }
    if (State == EWolfState::Recovery)
    {
        if (StateSeconds >= RecoverySeconds) { EnterState(EWolfState::Idle); if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge(); }
        return;
    }
    if (State == EWolfState::Bite || State == EWolfState::Pounce || State == EWolfState::Howl)
    {
        const auto* Vitals = Target.IsValid() ? Target->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
        if (!Target.IsValid() || (Vitals && Vitals->IsDead()))
        {
            bAttackConsumed = true; FinishPounceMovement(); RecoverySeconds = .2f; EnterState(EWolfState::Recovery); return;
        }
    }
    if (State == EWolfState::Howl)
    {
        SampleAction(TEXT("Howl"), FMath::Min(StateSeconds, ClipLength(TEXT("Howl"))));
        if (!bPackAlertSent && StateSeconds >= PackAlertTime) AlertPack();
        if (StateSeconds >= ClipLength(TEXT("Howl"))) { RecoverySeconds = .2f; EnterState(EWolfState::Recovery); }
        return;
    }
    if (State == EWolfState::Bite || State == EWolfState::Pounce) AdvanceAttack(Previous);
}
void AWolfMonster::InterruptAttack(float Seconds)
{
    if (!HasAuthority() || Dead()) return;
    bAttackConsumed = true; FinishPounceMovement();
    BiteCooldownLeft = FMath::Max(BiteCooldownLeft, .6f);
    ReactionSeconds = FMath::Max(.1f, Seconds);
    EnterState(EWolfState::Stagger);
    Combat->BeginReaction(ReactionSeconds);
}
void AWolfMonster::StartHitPresentation()
{
    const FVector Incoming = Combat->IsParryReaction() ? Combat->GetParryDirection() : IncomingHitDirection;
    const float Side = FVector::DotProduct(-Incoming.GetSafeNormal2D(), GetActorRightVector());
    ReactionAction = Side > .4f ? TEXT("HitRight") : Side < -.4f ? TEXT("HitLeft") : TEXT("HitFront");
    if (auto* Anim = Animation())
    {
        Anim->PlayTemplateAction(ReactionAction, true);
        if (Combat->IsParryReaction()) Anim->FinishPoseTransition();
    }
}
void AWolfMonster::SetHitPresentationTime(float Elapsed, float Remaining)
{
    // The source frontal recoil is deepest near .3 s. Preserve its recovery,
    // extending the held recoil instead of stretching the entire short clip.
    constexpr float Peak = .3f;
    const float Tail = FMath::Max(.01f, ClipLength(ReactionAction) - Peak);
    const float Time = Elapsed < Peak ? Elapsed : Remaining > Tail ? Peak : ClipLength(ReactionAction) - FMath::Max(0.f, Remaining);
    if (auto* Anim = Animation()) Anim->SetActionTime(Time);
}
void AWolfMonster::FinishHitReaction() { if (State != EWolfState::Stagger) return; RecoverySeconds = .15f; EnterState(EWolfState::Recovery); }
float AWolfMonster::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    if (!HasAuthority() || Dead() || Damage <= 0.f) return 0.f;
    IncomingHitDirection = Causer ? GetActorLocation() - Causer->GetActorLocation() : -GetActorForwardVector();
    if (Event.IsOfType(FPointDamageEvent::ClassID)) IncomingHitDirection = static_cast<const FPointDamageEvent&>(Event).ShotDirection;
    const float Requested = Damage;
    Damage = UDevelopmentTuningSubsystem::ShouldOneHitKill(this, EventInstigator, Causer) ? Health
        : CombatFormulaRuntime::MitigateMonster(this, Damage, Event.DamageTypeClass ? Event.DamageTypeClass->GetDefaultObject<UDamageType>() : nullptr, Causer);
    const float Applied = FMath::Min(Health, FMath::Max(0.f, Damage));
    if (Applied <= 0.f) return 0.f;
    Health -= Applied;
    Super::TakeDamage(Applied, Event, EventInstigator, Causer);
    if (Health <= 0.f) Die(EventInstigator);
    else Combat->ReceiveHit(Applied, EventInstigator ? EventInstigator->GetPawn().Get() : Cast<APawn>(Causer));
    UE_LOG(LogTemp, Display, TEXT("WOLF_DAMAGE target=%s requested=%.2f applied=%.2f health=%.2f/%.2f"), *GetName(), Requested, Applied, Health, MaxHealth);
    return Applied;
}
void AWolfMonster::Die(AController* Killer)
{
    if (Dead()) return;
    bAttackConsumed = true; Target.Reset(); FinishPounceMovement();
    EnterState(EWolfState::Dying);
    GetCharacterMovement()->DisableMovement();
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
    SetLifeSpan(FMath::Max(CorpseSeconds, ClipLength(TEXT("Death")) + 3.f));
    if (auto* Player = Cast<APlayerController>(Killer))
        if (Player->IsLocalController() && GetGameInstance())
            GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this, ExperienceReward);
}
void AWolfMonster::EnterRagdoll()
{
    if (State != EWolfState::Dying) return;
    auto* Body = GetMesh();
    if (!Body->GetPhysicsAsset()) { bUseRagdoll = false; return; }
    SampleAction(TEXT("Death"), ClipLength(TEXT("Death")) * FMath::Clamp(DeathAnimationFraction, 0.f, 1.f));
    Body->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Body->SetCollisionProfileName(TEXT("Ragdoll"));
    Body->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    Body->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Body->bPauseAnims = true;
    Body->KinematicBonesUpdateType = EKinematicBonesUpdateToPhysics::SkipAllBones;
    Body->SetAllBodiesSimulatePhysics(true); Body->SetSimulatePhysics(true);
    Body->SetAllPhysicsLinearVelocity(FVector::ZeroVector);
    Body->SetAllPhysicsAngularVelocityInRadians(FVector::ZeroVector);
    Body->WakeAllRigidBodies();
    State = EWolfState::Ragdoll; StateSeconds = 0.f;
}
void AWolfMonster::EndPlay(const EEndPlayReason::Type Reason)
{
    if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->StopMovement();
    Target.Reset(); bAttackConsumed = true;
    Super::EndPlay(Reason);
}
bool AWolfMonster::PrepareCombatPhysics(USkeletalMesh* InMesh)
{
#if WITH_EDITOR
    if (!InMesh || !InMesh->GetPathName().StartsWith(TEXT("/Game/Monsters/Wolf/"))) return false;
    auto* Physics = InMesh->GetPhysicsAsset();
    if (!Physics || !Physics->GetPathName().StartsWith(TEXT("/Game/Monsters/Wolf/"))) return false;
    InMesh->SetEnablePerPolyCollision(false);
    Physics->Modify();
    for (const auto& Body : Physics->SkeletalBodySetups)
    {
        if (!Body) continue;
        Body->Modify();
        Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        Body->PhysicsType = PhysType_Default;
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Body->DefaultInstance.LinearDamping = 1.f;
        Body->DefaultInstance.AngularDamping = 3.f;
        Body->DefaultInstance.bUseCCD = true;
        Body->InvalidatePhysicsData(); Body->CreatePhysicsMeshes();
    }
    Physics->UpdateBodySetupIndexMap(); Physics->UpdateBoundsBodiesArray();
    Physics->MarkPackageDirty(); InMesh->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
