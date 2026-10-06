#include "M25MagicComponent.h"
#include "VortexCofferM25.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/FPSLightningArc.h"
#include "../Skills/LightningDamage.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Net/UnrealNetwork.h"

UM25MagicComponent::UM25MagicComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
    SetIsReplicatedByDefault(true);
    ChargeAsset = TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/ElectricMagic/NS_ThunderCharge.NS_ThunderCharge")));
    ArcAsset = TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain")));
    ImpactAsset = TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/ElectricMagic/NS_ElectricImpact.NS_ElectricImpact")));
    LanceTube = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceRibbon.SM_ThunderLanceRibbon")));
    LanceIrisMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceIris.SM_ThunderLanceIris")));
    LanceBody = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceBeam.M_ThunderLanceBeam")));

    LanceIrisMat = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris.M_ThunderLanceIris")));
    ReleaseSound = TSoftObjectPtr<USoundBase>(FSoftObjectPath(TEXT("/Game/Skills/Lightning/S_LightningCast1.S_LightningCast1")));
}

void UM25MagicComponent::BeginPlay()
{
    Super::BeginPlay();
    Monster = Cast<AVortexCofferM25>(GetOwner());
    if (!Monster.IsValid()) return;
    AddTickPrerequisiteComponent(Monster->GetMesh());
    if (GetNetMode() != NM_DedicatedServer)
    {
        TArray<FSoftObjectPath> Paths = {ChargeAsset.ToSoftObjectPath(), ArcAsset.ToSoftObjectPath(),
            ImpactAsset.ToSoftObjectPath(), LanceTube.ToSoftObjectPath(), LanceIrisMesh.ToSoftObjectPath(),
            LanceBody.ToSoftObjectPath(), LanceIrisMat.ToSoftObjectPath(),
            ReleaseSound.ToSoftObjectPath()};
        AssetLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
            FStreamableDelegate::CreateWeakLambda(this, [this]() { UpdatePresentation(); }));
    }
    OnRep_CastState();
}

void UM25MagicComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UM25MagicComponent, CastState);
}

float UM25MagicComponent::Clock() const
{
    const auto* GS = GetWorld() ? GetWorld()->GetGameState() : nullptr;
    return GS ? GS->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
}

bool UM25MagicComponent::CanExecute() const
{
    const auto* M = Monster.Get();
    if (!M || !bAttacksEnabled || M->IsActorBeingDestroyed() || !M->IsActorTickEnabled()
        || M->ActorHasTag(TEXT("Friendly")) || M->ActorHasTag(TEXT("Summoned"))) return false;
    const auto* AI = Cast<AMonsterAIController>(M->GetController());
    if (!AI || !AI->bDecisionEnabled) return false;
    if (M->Combat && (M->Combat->IsDead() || M->Combat->IsControlled()
        || M->Combat->StunSecondsRemaining() > 0.f || M->Combat->IsImmobileReaction())) return false;
    const auto* Status = M->FindComponentByClass<UCombatStatusFormula>();
    return !Status || (!Status->IsStunned() && !Status->IsFrozen() && !Status->IsPetrified());
}

bool UM25MagicComponent::LivingEnemyPlayer(const APawn* Target) const
{
    if (!IsValid(Target) || !Target->IsPlayerControlled() || Target->IsActorBeingDestroyed()) return false;
    const auto* Health = Target->FindComponentByClass<UFPSCombatHealthComponent>();
    return Health && !Health->IsDead();
}

FVector UM25MagicComponent::ElectrodeLocation() const
{
    const auto* M = Monster.IsValid() ? Monster.Get() : Cast<AVortexCofferM25>(GetOwner());
    if (!M) return FVector::ZeroVector;
    const FName Socket(TEXT("socket_electric_00"));
    if (M->GetMesh()->DoesSocketExist(Socket)) return M->GetMesh()->GetSocketLocation(Socket);
    return M->GetActorLocation() - FVector(0, 0, M->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - 129.f);
}

FVector UM25MagicComponent::Origin(EM25Spell Spell) const
{
    return ElectrodeLocation() + FVector::UpVector * (Spell == EM25Spell::ThunderLance ? LanceChargeHeight : 16.f);
}

bool UM25MagicComponent::ClearChargeOrigin(EM25Spell Spell) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M25ChargeClearance), false, GetOwner());
    FHitResult Hit;
    return !GetWorld()->SweepSingleByChannel(Hit, ElectrodeLocation() + FVector(0, 0, 2),
        Origin(Spell), FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(8.f), Query);
}

FVector UM25MagicComponent::TargetPoint(const APawn* Target) const
{
    FVector Point = Target->GetActorLocation();
    if (const auto* Capsule = Target->FindComponentByClass<UCapsuleComponent>())
        Point = Capsule->GetComponentLocation() + FVector::UpVector * Capsule->GetScaledCapsuleHalfHeight() * .25f;
    return Point;
}

bool UM25MagicComponent::HasSight(const APawn* Target, EM25Spell Spell) const
{
    if (!LivingEnemyPlayer(Target) || !ClearChargeOrigin(Spell)) return false;
    const float Range = Spell == EM25Spell::ThunderLance ? LanceRange : LightningRange;
    if (FVector::DistSquared(Origin(Spell), TargetPoint(Target)) > FMath::Square(Range)) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M25MagicSight), false, GetOwner());
    Query.AddIgnoredActor(Target);
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit, Origin(Spell), TargetPoint(Target), ECC_Visibility, Query);
}

EM25Spell UM25MagicComponent::SelectSpell(APawn* Target) const
{
    const double Now = Clock();
    if (Now < RetryReadyAt) return EM25Spell::None;
    if (bOpenedWithLightning && Now >= LanceReadyAt && HasSight(Target, EM25Spell::ThunderLance))
        return EM25Spell::ThunderLance;
    if (Now >= LightningReadyAt && HasSight(Target, EM25Spell::Lightning))
        return EM25Spell::Lightning;
    return EM25Spell::None;
}

bool UM25MagicComponent::CanAttack(APawn* Target) const
{
    // Keep a local attack from starting before its telegraph can be presented.
    if (GetNetMode() != NM_DedicatedServer && (!ChargeAsset.Get() || !ArcAsset.Get()
        || !LanceTube.Get() || !LanceIrisMesh.Get() || !LanceBody.Get() || !LanceIrisMat.Get())) return false;
    return !IsBusy() && CanExecute() && SelectSpell(Target) != EM25Spell::None;
}

void UM25MagicComponent::SetTarget(APawn* Target)
{
    if (AttackTarget.Get() == Target) return;
    if (GetOwner()->HasAuthority())
    {
        if (IsBusy()) Cancel();
        // New engagements always open with the ordinary spell; cooldowns survive retargeting.
        bOpenedWithLightning = false;
    }
    AttackTarget = Target;
}

bool UM25MagicComponent::StartAttack(APawn* Target)
{
    if (!GetOwner()->HasAuthority() || !CanAttack(Target)) return false;
    const EM25Spell Spell = SelectSpell(Target);
    AttackTarget = Target;
    DamageSnapshot = FMath::Max(0.f, MagicAttack) * FMath::Max(0.f,
        Spell == EM25Spell::ThunderLance ? LanceMultiplier : LightningMultiplier);
    Monster->GetCharacterMovement()->StopMovementImmediately();
    if (auto* AI = Cast<AMonsterAIController>(Monster->GetController())) AI->StopMovement();
    CastState.Aim = TargetPoint(Target);
    CastState.bAimLocked = false;
    SetPhase(Spell, Spell == EM25Spell::ThunderLance ? FMath::Max(.3f, LanceWindup) : FMath::Max(.1f, LightningWindup));
    if (auto* AI = Cast<AMonsterAIController>(Monster->GetController())) AI->UpdateKnowledge();
    return true;
}

FVector UM25MagicComponent::PredictAim(const APawn* Target, float Seconds) const
{
    const FVector Point = TargetPoint(Target);
    // This is an instantaneous ray, so lead covers the remaining locked windup, not a fictitious flight time.
    const FVector Offset = (Target->GetVelocity() * Seconds).GetClampedToMaxSize(FMath::Max(0.f, MaxLeadDistance));
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M25LeadObstruction), false, GetOwner());
    Query.AddIgnoredActor(Target);
    FHitResult Hit;
    return GetWorld()->LineTraceSingleByChannel(Hit, Point, Point + Offset, ECC_Visibility, Query)
        ? Hit.ImpactPoint - Offset.GetSafeNormal() * 3.f : Point + Offset;
}

void UM25MagicComponent::SetPhase(EM25Spell Spell, float Duration)
{
    CastState.Spell = Spell;
    CastState.StartedAt = Clock();
    CastState.Duration = Duration;
    OnRep_CastState();
    GetOwner()->ForceNetUpdate();
}

void UM25MagicComponent::OnRep_CastState()
{
    if (Monster.IsValid()) Monster->RefreshCombatPoseTick();
    SetComponentTickEnabled(IsBusy());
    UpdatePresentation();
}

void UM25MagicComponent::UpdatePresentation()
{
    if (!Monster.IsValid() || GetNetMode() == NM_DedicatedServer) return;
    const bool Charging = !Monster->Dead() && !Monster->Controlled() &&
        (CastState.Spell == EM25Spell::Lightning || CastState.Spell == EM25Spell::ThunderLance);
    if (!Charging)
    {
        if (Charge) Charge->DeactivateImmediate();
        return;
    }
    if (!Charge && ChargeAsset.Get())
    {
        Charge = NewObject<UNiagaraComponent>(GetOwner(), TEXT("M25MagicCharge"));
        GetOwner()->AddInstanceComponent(Charge);
        Charge->SetAutoActivate(false);
        Charge->SetAsset(ChargeAsset.Get());
        Charge->SetCastShadow(false);
        Charge->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
        Charge->AddTickPrerequisiteComponent(this);
        Charge->RegisterComponent();
    }
    if (!Charge) return;
    const float Fraction = FMath::Clamp((Clock() - CastState.StartedAt) / FMath::Max(.01f, CastState.Duration), 0.f, 1.f);
    const bool Lance = CastState.Spell == EM25Spell::ThunderLance;
    const FVector Position = Origin(CastState.Spell);
    Charge->SetWorldLocationAndRotation(Position, (FVector(CastState.Aim) - Position).Rotation());
    const float Scale = (Lance ? .85f : .32f) * (.22f + .62f * FMath::SmoothStep(0.f, 1.f, Fraction));
    Charge->SetWorldScale3D(FVector(Scale));
    Charge->SetVariableFloat(TEXT("User.Charge"), Fraction);
    if (!Charge->IsActive()) Charge->Activate(true);
}

void UM25MagicComponent::TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta, Type, Tick);
    if (GetOwner()->HasAuthority())
    {
        const float Elapsed = Clock() - CastState.StartedAt;
        if (CastState.Spell == EM25Spell::Recovery)
        {
            if (Elapsed >= CastState.Duration) SetPhase(EM25Spell::None, 0.f);
        }
        else if (CastState.Spell != EM25Spell::None)
        {
            APawn* Target = AttackTarget.Get();
            if (!CanExecute() || !LivingEnemyPlayer(Target) || !ClearChargeOrigin(CastState.Spell)
                || (!CastState.bAimLocked && !HasSight(Target, CastState.Spell)))
            {
                Cancel();
                return;
            }
            const float Remaining = FMath::Max(0.f, CastState.Duration - Elapsed);
            if (!CastState.bAimLocked)
            {
                CastState.Aim = TargetPoint(Target);
                if (CastState.Spell == EM25Spell::ThunderLance && Remaining <= FMath::Max(0.f, LanceAimLockSeconds))
                {
                    CastState.Aim = PredictAim(Target, Remaining);
                    CastState.bAimLocked = true;
                    GetOwner()->ForceNetUpdate();
                }
            }
            if (Elapsed >= CastState.Duration) Release();
        }
    }
    UpdatePresentation();
}

bool UM25MagicComponent::FirstContact(FVector Start, FVector End, float Radius, FHitResult& Hit) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M25ElectricContact), false, GetOwner());
    FCollisionObjectQueryParams Objects;
    for (ECollisionChannel Channel : {ECC_WorldStatic, ECC_WorldDynamic, ECC_Pawn, ECC_PhysicsBody})
        Objects.AddObjectTypesToQuery(Channel);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByObjectType(Hits, Start, End, FQuat::Identity, Objects,
        FCollisionShape::MakeSphere(FMath::Max(.1f, Radius)), Query);
    bool Found = false;
    for (const FHitResult& Contact : Hits)
    {
        const auto* Component = Contact.GetComponent();
        const auto* Pawn = Cast<APawn>(Contact.GetActor());
        // Player capsules intentionally ignore Visibility; overlap-only volumes never block spells.
        const bool PlayerCapsule = Pawn && Pawn->IsPlayerControlled() && Component == Pawn->GetRootComponent();
        if (!Component || (!PlayerCapsule && Component->GetCollisionResponseToChannel(ECC_Visibility) != ECR_Block)) continue;
        if (!Found || Contact.Time < Hit.Time) { Hit = Contact; Found = true; }
    }
    return Found;
}

void UM25MagicComponent::Release()
{
    if (!GetOwner()->HasAuthority() || !CanExecute()) { Cancel(); return; }
    const bool Lance = CastState.Spell == EM25Spell::ThunderLance;
    const FVector Start = Origin(CastState.Spell);
    const FVector Direction = (FVector(CastState.Aim) - Start).GetSafeNormal();
    if (Direction.IsNearlyZero()) { Cancel(); return; }
    FHitResult Hit;
    const bool Blocked = FirstContact(Start, Start + Direction * (Lance ? LanceRange : LightningRange),
        Lance ? LanceHitRadius : .35f, Hit);
    // A swept sphere's center stays on the beam axis; the impact spark belongs on the surface point.
    const FVector End = Blocked ? Hit.Location : Start + Direction * (Lance ? LanceRange : LightningRange);
    const FVector Impact = Blocked ? Hit.ImpactPoint : End;
    const FVector Normal = Blocked ? Hit.ImpactNormal : -Direction;
    // Spend only the released spell's cooldown. Interrupted windups never consume a full cooldown.
    if (Lance) LanceReadyAt = Clock() + FMath::Max(0.f, LanceCooldown);
    else { LightningReadyAt = Clock() + FMath::Max(0.f, LightningCooldown); bOpenedWithLightning = true; }
    SetPhase(EM25Spell::Recovery, Lance ? .7f : .4f);
    if (Blocked && LivingEnemyPlayer(Cast<APawn>(Hit.GetActor())))
        UGameplayStatics::ApplyPointDamage(Hit.GetActor(), DamageSnapshot, Direction, Hit,
            Monster->GetController(), Monster.Get(), ULightningDamage::StaticClass());

    // The existing replicated spell VFX actor carries only presentation; damage is resolved above once.
    FLightningCast Visual;
    Visual.Duration = Lance ? .22f : .16f; Visual.Fade = Lance ? .42f : .22f;
    Visual.Segments = 10; Visual.Jitter = .065f;
    FActorSpawnParameters Spawn; Spawn.Owner = Monster.Get();
    if (auto* FX = GetWorld()->SpawnActor<AFPSLightningArc>(Start, FRotator::ZeroRotator, Spawn))
    {
        if (Lance && (GetNetMode() == NM_DedicatedServer || (LanceTube.Get() && LanceIrisMesh.Get() && LanceBody.Get() && LanceIrisMat.Get())))
            FX->InitializeColumn(LanceTube.Get(), LanceIrisMesh.Get(), LanceBody.Get(), LanceIrisMat.Get(), Start, End, Visual, 1.f, .32f);
        else FX->InitializeArc(ArcAsset.Get(), Start, End, Visual, Lance ? 1.1f : .5f, true, Lance ? 55.f : 44.f);
    }
    MulticastImpact(Start, Impact, Normal, Blocked, Lance);
}

void UM25MagicComponent::MulticastImpact_Implementation(FVector_NetQuantize Start,
    FVector_NetQuantize Point, FVector_NetQuantizeNormal Normal, bool bSurfaceHit, bool bLance)
{
    if (GetNetMode() == NM_DedicatedServer) return;
    if (bSurfaceHit && ImpactAsset.Get())
        UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, ImpactAsset.Get(), Point,
            FRotationMatrix::MakeFromZ(Normal).Rotator(), FVector(bLance ? .85f : .45f),
            true, true, ENCPoolMethod::AutoRelease);
    if (ReleaseSound.Get()) UGameplayStatics::PlaySoundAtLocation(this, ReleaseSound.Get(), Start, bLance ? .75f : .55f);
}

void UM25MagicComponent::Cancel()
{
    if (!GetOwner()->HasAuthority()) return;
    RetryReadyAt = Clock() + .75f;
    CastState.bAimLocked = false;
    SetPhase(EM25Spell::None, 0.f);
}

void UM25MagicComponent::EndPlay(EEndPlayReason::Type Reason)
{
    if (AssetLoad.IsValid()) AssetLoad->CancelHandle();
    AssetLoad.Reset();
    CastState.Spell = EM25Spell::None;
    if (Monster.IsValid()) Monster->RefreshCombatPoseTick();
    if (Charge) { Charge->DestroyComponent(); Charge = nullptr; }
    Super::EndPlay(Reason);
}

void UM25MagicComponent::Interrupt()
{
    if (GetOwner()->HasAuthority()) Cancel();
    else { CastState.Spell = EM25Spell::None; OnRep_CastState(); }
}
