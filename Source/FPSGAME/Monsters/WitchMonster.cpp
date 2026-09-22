#include "WitchMonster.h"
#include "WitchSpellAnimInstance.h"
#include "WitchProjectile.h"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "AIController.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "UObject/ConstructorHelpers.h"
#include "TimerManager.h"
AWitchMonster::AWitchMonster(const FObjectInitializer& Initializer) : Super(Initializer)
{
    Tags.Remove(TEXT("NurseZombie")); Tags.Add(TEXT("Witch"));
    GetCapsuleComponent()->InitCapsuleSize(34.f, 94.f);
    // Health/magic/cooldowns come from the original witch config. World units
    // are authored centimetres, not an automatic conversion of source pixels.
    MaxHealth = 1300.f; Health = MaxHealth; WalkSpeed = 82.5f; AggroRadius = 1600.f;
    AttackRange = SpellRange; AttackDamage = 0.f; RecoveryTime = 0.f;
    // The inherited attack clock drives our overridden presentation hook.
    // Its melee contact branch is disabled: only ReleaseSpell deals attacks.
    ContactTime = 0.f; ContactEnd = -1.f; CorpseSeconds = 15.f;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> StaffAsset(TEXT("/Game/Monsters/WitchMeshy/Props/SM_Witch_Staff.SM_Witch_Staff"));
    static ConstructorHelpers::FClassFinder<AAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    // Concrete presentation resolves its own assets; do not load retired Witch variants.
    VisualMesh = nullptr; IdleClip = nullptr; WalkClip = nullptr; AttackClip = nullptr;
    GetMesh()->SetSkeletalMeshAsset(nullptr);
    GetMesh()->bCollideWithEnvironment = true;
    if (AI.Succeeded()) AIControllerClass = AI.Class;
    Staff = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WitchStaff"));
    Staff->SetupAttachment(GetMesh(), TEXT("hand_l")); Staff->SetStaticMesh(StaffAsset.Object);
    Bottle = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WitchBottle"));
    Bottle->SetupAttachment(GetMesh(), TEXT("hand_r"));
    for (auto* Prop : {Staff.Get(), Bottle.Get()})
    {
        Prop->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Prop->SetGenerateOverlapEvents(false); Prop->SetCanEverAffectNavigation(false);
    }
    AlignVisual();
}

void AWitchMonster::AlignVisual()
{
    // Navigation profiles within 5 cm are equivalent in UE. Keep explicit
    // clearance distinct from Nurse (184 cm), while retaining our 188 cm body.
    auto* Movement = GetCharacterMovement();
    Movement->SetUpdateNavAgentWithOwnersCollisions(false);
    auto& Agent = Movement->GetNavAgentPropertiesRef();
    Agent.AgentRadius = GetCapsuleComponent()->GetScaledCapsuleRadius();
    Agent.AgentHeight = FMath::Max(192.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() * 2.f);
    Agent.AgentStepHeight = Movement->MaxStepHeight;
    if (!VisualMesh) return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    // The rebuilt authoring source places the soles at zero.
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()));
}

void AWitchMonster::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform); AlignVisual();
}

void AWitchMonster::BeginPlay()
{
    AttackClip = CastClip; AlignVisual();
    Super::BeginPlay();
    // The initial idle pose provides the attachment frame. Preserve that offset
    // while the same hand bones subsequently raise the staff and throw.
    GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    AttachProps();
}

bool AWitchMonster::CanCast(APawn* Candidate) const
{
    if (!IsValid(Candidate) || !CastClip || !ThrowClip || State == ENurseState::Dead
        || State == ENurseState::Stagger || State == ENurseState::Attack) return false;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < NextMagicAt && Now < NextBottleAt) return false;
    if (FVector::Dist2D(GetActorLocation(), Candidate->GetActorLocation()) > SpellRange) return false;
    // Finish facing during approach/idle, before planting for the spell.
    const FVector Aim = (Candidate->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
    if (FVector::DotProduct(GetActorForwardVector(), Aim) < .98f) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchSight), false, this);
    Query.AddIgnoredActor(Candidate);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation() + FVector(0,0,35),
        Candidate->GetActorLocation(), ECC_Visibility, Query);
}

void AWitchMonster::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!HasAuthority() || (State != ENurseState::Idle && State != ENurseState::Chase)) return;
    const auto* AI = Cast<AAIController>(GetController());
    const auto* Board = AI ? AI->GetBlackboardComponent() : nullptr;
    auto* AimTarget = Board ? Cast<APawn>(Board->GetValueAsObject(TEXT("Target"))) : nullptr;
    if (!AimTarget || Board->GetValueAsBool(TEXT("Returning"))
        || FVector::DistSquared2D(GetActorLocation(), AimTarget->GetActorLocation()) > FMath::Square(SpellRange)) return;
    const FRotator Facing(0, (AimTarget->GetActorLocation() - GetActorLocation()).Rotation().Yaw, 0);
    SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), Facing, DeltaSeconds, 110.f));
}

UWitchSpellAnimInstance* AWitchMonster::GetSpellAnimation()
{
    if (!Cast<UWitchSpellAnimInstance>(GetMesh()->GetAnimInstance()))
        GetMesh()->SetAnimInstanceClass(UWitchSpellAnimInstance::StaticClass());
    return Cast<UWitchSpellAnimInstance>(GetMesh()->GetAnimInstance());
}

void AWitchMonster::StartStateAnimation(UAnimSequence* Clip, bool bLoop)
{
    if (State == ENurseState::Attack)
    {
        const double Now = GetWorld()->GetTimeSeconds();
        bThrowing = Now < NextMagicAt && Now >= NextBottleAt;
        AttackClip = bThrowing ? ThrowClip : CastClip;
        Clip = AttackClip; bReleased = false;
        Bottle->SetVisibility(true);
        if (bThrowing) NextBottleAt = Now + BottleCooldown;
        else NextMagicAt = Now + MagicCooldown;
        if (const auto* AI = Cast<AAIController>(GetController()))
            if (const auto* Blackboard = AI->GetBlackboardComponent())
                SpellTarget = Cast<APawn>(Blackboard->GetValueAsObject(TEXT("Target")));
    }
    else if (Bottle) Bottle->SetVisibility(true);
    if (auto* Animation = GetSpellAnimation()) Animation->PlayState(Clip, bLoop);
}

void AWitchMonster::SetAttackAnimationTime(float Seconds)
{
    if (auto* Animation = GetSpellAnimation()) Animation->SetCombatTime(Seconds);
    const float Release = bThrowing ? .75f : 1.5f * 5.f / 14.f;
    if (!bReleased && State == ENurseState::Attack && Seconds >= Release)
    {
        bReleased = true; ReleaseSpell();
    }
}

void AWitchMonster::ReleaseSpell()
{
    if (!HasAuthority() || State != ENurseState::Attack || !SpellTarget.IsValid()) return;
    GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    const FVector Start = bThrowing ? Bottle->GetComponentLocation()
        : Staff->GetComponentLocation() + Staff->GetUpVector() * 150.f;
    const FVector AimLocation = SpellTarget->GetActorLocation();
    Spells.RemoveAll([](const auto& Spell) { return !Spell.IsValid(); });
    for (int32 Index = 0; Index < (bThrowing ? 1 : 3); ++Index)
    {
        FActorSpawnParameters Params; Params.Owner = this; Params.Instigator = this;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Spell = GetWorld()->SpawnActor<AWitchProjectile>(Start, FRotator::ZeroRotator, Params);
        if (!Spell) continue;
        const FVector Prediction = AimLocation + SpellTarget->GetVelocity() * FMath::Min(.5f,
            FVector::Dist(Start, AimLocation) / FMath::Max(1.f, ProjectileSpeed));
        const FVector Aim = (Prediction - Start).GetSafeNormal().RotateAngleAxis((Index - 1) * 15.f, FVector::UpVector);
        Spell->Launch(this, bThrowing, bThrowing ? AimLocation : Start + Aim * 1000.f,
            ProjectileSpeed, MagicAttack * .75f, PoisonRadius);
        Spells.Add(Spell);
    }
    if (bThrowing) Bottle->SetVisibility(false);
}

void AWitchMonster::SetWalkAnimationRate(float)
{
    if (auto* Animation = GetSpellAnimation())
        Animation->SetLocomotionRate(FMath::Clamp(GetVelocity().Size2D() / FMath::Max(1.f, WalkSpeed), 0.f, 2.f));
}

void AWitchMonster::StartHitPresentation(UAnimSequence* Clip, float Duration)
{
    bReleased = true; SpellTarget.Reset(); Bottle->SetVisibility(true);
    // The native player freezes its current pose while the shared state is Stagger.
    if (Clip) if (auto* Animation = GetSpellAnimation()) Animation->PlayState(Clip, false);
}

void AWitchMonster::SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining)
{
    if (!Clip) return;
    const float Time = Elapsed < .15f ? Elapsed : Remaining > .4f ? .15f : Clip->GetPlayLength() - FMath::Max(0.f, Remaining);
    if (auto* Animation = GetSpellAnimation()) Animation->SetCombatTime(FMath::Clamp(Time, 0.f, Clip->GetPlayLength()));
}

void AWitchMonster::StartDeathPresentation()
{
    bReleased = true; SpellTarget.Reset();
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (DeathClip) { GetMesh()->PlayAnimation(DeathClip, false); GetMesh()->SetPlayRate(1.f); }
    const float Delay = DeathClip ? DeathClip->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction : 0.f;
    if (Delay > 0) GetWorldTimerManager().SetTimer(RagdollTimer, this, &ThisClass::StartRagdoll, Delay, false);
    else StartRagdoll();
}

void AWitchMonster::StartRagdoll()
{
    if (State != ENurseState::Dead || !GetMesh()->GetPhysicsAsset()) return;
    if (DeathClip)
    {
        GetMesh()->SetPosition(DeathClip->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction, false);
        GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    }
    GetMesh()->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
    GetMesh()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    GetMesh()->bPauseAnims = true;
    GetMesh()->SetAllBodiesSimulatePhysics(true); GetMesh()->SetSimulatePhysics(true);
    GetMesh()->WakeAllRigidBodies();
}

void AWitchMonster::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(RagdollTimer);
    for (const auto& Spell : Spells) if (Spell.IsValid()) Spell->Destroy();
    Spells.Reset(); Super::EndPlay(Reason);
}
