#include "MantisM27Monster.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

void AMantisM27Monster::NotifyCloakEncounter(APawn* Victim)
{
    if (!HasAuthority() || !HasActorBegunPlay() || bEncounterCloakUsed || !IsValid(Victim) || Health <= 0.f) return;
    bEncounterCloakUsed = true;
    SetCloaked(true);
}

float AMantisM27Monster::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    const float Before = Health;
    const float Applied = Super::TakeDamage(Damage, Event, EventInstigator, Causer);
    if (!HasAuthority()) return Applied;
    if (Applied > 0.f && Health > 0.f && GetWorld()->GetTimeSeconds()-LastMantisHurtAudioAt >= .22)
    {
        LastMantisHurtAudioAt = GetWorld()->GetTimeSeconds();
        MulticastMantisAccent(TEXT("Hurt"), ServerClock());
    }
    if (Health <= 0.f)
    {
        SetCloaked(false);
        RestoreCloakVisuals();
    }
    else if (Applied > 0.f && !bInjuryCloakUsed && Before > MaxHealth * CloakInjuryThreshold && Health <= MaxHealth * CloakInjuryThreshold)
    {
        bInjuryCloakUsed = true;
        // A half-health hit during the opening cloak spends the second charge
        // and refreshes its retreat, without an opaque flash between charges.
        SetCloaked(true);
    }
    return Applied;
}

void AMantisM27Monster::SetCloaked(bool Enabled)
{
    if (!HasAuthority()) return;
    if (Enabled)
    {
        CancelPounce();
        ActiveAttackDamageScale = 1.f;
        if (!bCloaked) UncloakedMoveSpeed = GetCharacterMovement()->MaxWalkSpeed;
        CloakStartedAt = GetWorld()->GetTimeSeconds();
        bCloakAttackCommitted = false;
        NextCloakGoalAt = 0.;
        CloakOrbitDirection = (GetUniqueID() & 1) ? 1.f : -1.f;
        bContactConsumed = true;
        CancelAttackForLocomotion(); // Keep existing stuns and knockdowns intact.
        GetCharacterMovement()->MaxWalkSpeed = CloakMoveSpeed;
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->StopMovement();
    }
    else if (bCloaked)
    {
        GetCharacterMovement()->MaxWalkSpeed = UncloakedMoveSpeed;
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->StopMovement();
    }
    const bool Changed = bCloaked != Enabled;
    bCloaked = Enabled;
    if (Changed)
    {
        OnRep_Cloaked(); ForceNetUpdate();
        if (Health > 0.f && State != ENurseState::Dead)
            MulticastMantisAccent(Enabled ? TEXT("CloakEnter") :
                ActiveAttackDamageScale > 1.f ? TEXT("ShadowBreak") : TEXT("CloakExit"), ServerClock());
    }
}

void AMantisM27Monster::OnRep_Cloaked()
{
    if (bCloaked) PrepareCloakVisuals();
    else RestoreCloakVisuals(); // Attack starts fully visible on every peer.
}

bool AMantisM27Monster::IsCloakRecoveryReady() const
{
    return !bCloaked || bCloakAttackCommitted;
}

void AMantisM27Monster::BeginShadowStrike()
{
    ActiveAttackDamageScale = bCloaked ? ShadowStrikeMultiplier : 1.f;
    SetCloaked(false);
    RestoreCloakVisuals();
}

void AMantisM27Monster::PrepareCloakVisuals()
{
    if (bCloakVisualsApplied || GetNetMode() == NM_DedicatedServer || !CloakMaterial) return;
    auto* BodyMesh = GetMesh();
    if (!CloakInstance) CloakInstance = UMaterialInstanceDynamic::Create(CloakMaterial, this);
    if (!CloakInstance) return;
    UncloakedMaterials.Reset();
    for (int32 Slot = 0; Slot < BodyMesh->GetNumMaterials(); ++Slot) UncloakedMaterials.Add(BodyMesh->GetMaterial(Slot));
    bUncloakedCastsShadow = BodyMesh->CastShadow;
    if (!CloakShadow)
    {
        CloakShadow = NewObject<USkeletalMeshComponent>(this, TEXT("M27CloakShadow"));
        CloakShadow->SetupAttachment(BodyMesh);
        CloakShadow->SetSkeletalMeshAsset(BodyMesh->GetSkeletalMeshAsset());
        CloakShadow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        CloakShadow->SetGenerateOverlapEvents(false);
        CloakShadow->SetCanEverAffectNavigation(false);
        CloakShadow->SetLeaderPoseComponent(BodyMesh);
        CloakShadow->bUseBoundsFromLeaderPoseComponent = true;
        CloakShadow->SetRenderInMainPass(false);
        CloakShadow->SetRenderInDepthPass(false);
        CloakShadow->SetHiddenInGame(true);
        CloakShadow->SetCastHiddenShadow(true);
        CloakShadow->RegisterComponent();
    }
    for (int32 Slot = 0; Slot < UncloakedMaterials.Num(); ++Slot)
    {
        CloakShadow->SetMaterial(Slot, UncloakedMaterials[Slot]);
        BodyMesh->SetMaterial(Slot, CloakInstance);
    }
    // Opaque, pose-following geometry owns the shadow during translucency.
    // It adds no independent animation evaluation or collision body.
    CloakShadow->SetCastShadow(bUncloakedCastsShadow);
    BodyMesh->SetCastShadow(false);
    CloakInstance->SetScalarParameterValue(TEXT("CloakAmount"), CloakBlend);
    bCloakVisualsApplied = true;
}

void AMantisM27Monster::RestoreCloakVisuals()
{
    if (!bCloakVisualsApplied) return;
    for (int32 Slot = 0; Slot < UncloakedMaterials.Num(); ++Slot) GetMesh()->SetMaterial(Slot, UncloakedMaterials[Slot]);
    GetMesh()->SetCastShadow(bUncloakedCastsShadow);
    if (CloakShadow) CloakShadow->SetCastShadow(false);
    CloakBlend = 0.f;
    bCloakVisualsApplied = false;
}

void AMantisM27Monster::TickCloak(float DeltaSeconds)
{
    if (Health <= 0.f || State == ENurseState::Dead)
    {
        if (HasAuthority()) CancelPounce();
        if (HasAuthority() && bCloaked) SetCloaked(false);
        RestoreCloakVisuals();
        return;
    }
    if (HasAuthority() && bCloaked)
    {
        Health = FMath::Min(MaxHealth, Health + MaxHealth * CloakHealFractionPerSecond * DeltaSeconds);
        if (!bCloakAttackCommitted && GetWorld()->GetTimeSeconds() - CloakStartedAt >= CloakMinimumSeconds &&
            Health >= MaxHealth * CloakRecoveryThreshold)
        {
            bCloakAttackCommitted = true;
            NextCloakGoalAt = 0.;
            CloakGoal = FVector::ZeroVector;
            // Drop the orbit request once, then let the existing tree pick a
            // pounce or a real melee approach. Do not wait to hit full health.
            if (auto* AI = Cast<AMonsterAIController>(GetController()))
            {
                AI->StopMovement();
                AI->UpdateKnowledge();
            }
        }
        // Regenerated hunters approach/choose a pounce while concealed. The
        // attack itself breaks cloak and captures its one-attack bonus.
        if (!CombatTarget() && IsCloakRecoveryReady())
            SetCloaked(false);
    }
    if (!bCloaked && !bCloakVisualsApplied) return;
    if (bCloaked && !bCloakVisualsApplied) PrepareCloakVisuals();
    const float NextBlend = FMath::FInterpConstantTo(CloakBlend, bCloaked ? 1.f : 0.f, DeltaSeconds, 1.f / FMath::Max(.01f, CloakFadeSeconds));
    if (CloakInstance && NextBlend != CloakBlend) CloakInstance->SetScalarParameterValue(TEXT("CloakAmount"), NextBlend);
    CloakBlend = NextBlend;
    if (!bCloaked && CloakBlend <= 0.f) RestoreCloakVisuals();
}

void AMantisM27Monster::NavigateWhileCloaked(AMonsterAIController* AI, const FVector& TargetFeet)
{
    if (!HasAuthority() || !bCloaked || IsCloakRecoveryReady() || !AI || Combat->IsBusy()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now >= NextCloakGoalAt)
    {
        NextCloakGoalAt = Now + .85;
        const FVector Feet = GetNavAgentLocation();
        FVector Away = (Feet - TargetFeet).GetSafeNormal2D();
        if (Away.IsNearlyZero()) Away = -GetActorForwardVector();
        const float Distance = FVector::Dist2D(Feet, TargetFeet);
        if (AI->bNavigationFailed) CloakOrbitDirection *= -1.f;
        if (Now - CloakStartedAt < .85)
            CloakGoal = TargetFeet + Away * FMath::Max(CloakOrbitRadius, Distance + 350.f);
        else if (Distance < CloakOrbitRadius * .85f && !AI->bNavigationFailed)
            CloakGoal = TargetFeet + Away * CloakOrbitRadius;
        else
        {
            const float Radius = FMath::Max(CloakOrbitRadius, Distance - 80.f);
            CloakGoal = TargetFeet + Away.RotateAngleAxis((AI->bNavigationFailed ? 65.f : 32.f) * CloakOrbitDirection, FVector::UpVector) * Radius;
        }
        // Stay inside the shared home leash; ordinary navigation projects the
        // feet-height goal and performs collision/pathfinding at its own cadence.
        const FVector FromHome = CloakGoal - Combat->Home();
        const float Leash = FMath::Max(100.f, Combat->LeashRange() - 180.f);
        if (FromHome.Size2D() > Leash) CloakGoal = Combat->Home() + FromHome.GetSafeNormal2D() * Leash;
        CloakGoal.Z = TargetFeet.Z;
    }
    Combat->SetLocomotion(true);
    AI->NavigateTo(CloakGoal, 55.f);
}
