#include "HundredEyedSlagMonster.h"
#include "SlagBlackMist.h"
#include "FPSCombatHealthComponent.h"
#include "HandBrainMonster.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "Animation/AnimSequence.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "NiagaraComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"

bool AHundredEyedSlagMonster::SpecialAttacking() const
{
    return State == ESlagState::EyeLaserWindup || State == ESlagState::EyeLaserFire
        || State == ESlagState::EyeLaserRecover;
}

void AHundredEyedSlagMonster::EndPlay(const EEndPlayReason::Type Reason)
{
    if (BackMist) { BackMist->StopEmission(); BackMist = nullptr; }
    ClearLaserFX();
    Super::EndPlay(Reason);
}

FVector AHundredEyedSlagMonster::LaserFocus() const
{
    // The beam leaves the main eye, so its charge no longer floats between eyes.
    return LaserEye(0) + GetActorForwardVector()*3.f;
}

FVector AHundredEyedSlagMonster::LaserEye(int32 Index) const
{
    return GetMesh()->GetSocketTransform(TEXT("front_plate")).TransformPosition(EyeBindOffsets[Index]);
}

void AHundredEyedSlagMonster::ClearLaserFX()
{
    for (const auto& Renderer : EyeLaserRenderers) if (Renderer) Renderer->SetVisibility(false);
    for (const auto& ChargeFX : EyeChargeSystems)
        if (ChargeFX) { ChargeFX->SetVisibility(false); ChargeFX->DeactivateImmediate(); }
}

void AHundredEyedSlagMonster::UpdateLaserFX(float Energy, bool Firing)
{
    if (GetNetMode() == NM_DedicatedServer || EyeLaserRenderers.Num() != 7) return;
    auto* PC = GetWorld()->GetFirstPlayerController();
    if (!PC || !PC->PlayerCameraManager
        || FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(),GetActorLocation()) > FMath::Square(2600.f))
    { ClearLaserFX(); return; }
    if (EyeLaserMaterials.IsEmpty())
    {
        auto* Glow = EyeLaserRenderers[6]->CreateDynamicMaterialInstance(0);
        auto* Core = EyeLaserRenderers[5]->CreateDynamicMaterialInstance(0);
        if (!Glow || !Core) return;
        EyeLaserMaterials.Add(Glow); EyeLaserMaterials.Add(Core);
        Glow->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.008f,.003f));
        Core->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.65f,.25f));
        Glow->SetScalarParameterValue(TEXT("Opacity"),.55f);
        Core->SetScalarParameterValue(TEXT("Opacity"),.8f);
        for (int32 I : {4,6}) EyeLaserRenderers[I]->SetMaterial(0,Glow);
        EyeLaserRenderers[5]->SetMaterial(0,Core);
    }
    if (!EyeCoreMaterial)
    {
        EyeCoreMaterial = EyeLaserRenderers[0]->CreateDynamicMaterialInstance(0);
        if (EyeCoreMaterial) EyeLaserRenderers[1]->SetMaterial(0,EyeCoreMaterial);
    }
    if (!EyeVortexMaterial)
    {
        EyeVortexMaterial = EyeLaserRenderers[2]->CreateDynamicMaterialInstance(0);
        if (EyeVortexMaterial) EyeLaserRenderers[3]->SetMaterial(0,EyeVortexMaterial);
    }
    Energy = FMath::Clamp(Energy,0.f,1.f);
    const float Pulse = 1.f+.07f*FMath::Sin(StateSeconds*22.f);
    EyeLaserMaterials[0]->SetScalarParameterValue(TEXT("Intensity"),Firing ? 22.f : (4.f+16.f*Energy)*Pulse);
    EyeLaserMaterials[1]->SetScalarParameterValue(TEXT("Intensity"),18.f);
    const float ChargeStrength = FMath::SmoothStep(0.f,1.f,Energy)*Pulse;
    if (EyeCoreMaterial) EyeCoreMaterial->SetScalarParameterValue(TEXT("ChargeStrength"),Firing ? 2.f : .25f+1.75f*ChargeStrength);
    if (EyeVortexMaterial)
    {
        EyeVortexMaterial->SetScalarParameterValue(TEXT("ChargeStrength"),ChargeStrength);
        EyeVortexMaterial->SetScalarParameterValue(TEXT("Intensity"),Firing ? 10.f : 7.f+5.f*Energy);
    }
    const FVector Forward = GetActorForwardVector();
    const FQuat EyeRotation = FRotationMatrix::MakeFromX(Forward).ToQuat();
    for (int32 I = 0; I < EyeChargeSystems.Num(); ++I)
    {
        auto* ChargeFX = EyeChargeSystems[I].Get();
        if (!ChargeFX) continue;
        if (Firing) { ChargeFX->SetVisibility(false); ChargeFX->DeactivateImmediate(); continue; }
        const float Scale = I == 0 ? 1.f : .65f;
        ChargeFX->SetWorldTransform(FTransform(EyeRotation,LaserEye(I)+Forward*2.f,FVector(Scale)));
        ChargeFX->SetVariableFloat(TEXT("User.Charge"),Energy);
        ChargeFX->SetVisibility(true);
        if (!ChargeFX->IsActive()) ChargeFX->Activate(true);
    }
    const FVector Focus = LaserFocus();
    for (int32 I = 0; I < 2; ++I)
    {
        const float EyeScale = I == 0 ? 1.f : .65f;
        const FVector Eye = LaserEye(I)+Forward*2.f;
        const float CoreRadius = (6.f+2.f*Energy)*EyeScale;
        // Flatten the imported energy sphere onto the eye; preserve the iris silhouette.
        EyeLaserRenderers[I]->SetWorldTransform(FTransform(EyeRotation,Eye,
            FVector(CoreRadius*.35f/50.f,CoreRadius/50.f,CoreRadius/50.f)));
        EyeLaserRenderers[I]->SetVisibility(Energy > .02f);
        const FVector Halo = Eye+Forward*2.f;
        const float RadiusCM = (15.f+3.f*Energy)*EyeScale;
        EyeLaserRenderers[I+2]->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(Forward).ToQuat(),
            Halo,FVector(RadiusCM/50.f)));
        EyeLaserRenderers[I+2]->SetVisibility(Energy > .02f);
    }
    EyeLaserRenderers[4]->SetVisibility(false);
    const FVector Delta = LaserEnd-Focus;
    for (int32 I = 5; I < 7; ++I)
    {
        const float Radius = I == 5 ? 2.5f : 7.f;
        EyeLaserRenderers[I]->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(Delta).ToQuat(),
            (Focus+LaserEnd)*.5,FVector(Radius/50.f,Radius/50.f,Delta.Size()/100.f)));
        EyeLaserRenderers[I]->SetVisibility(Firing && Delta.SizeSquared() > 1.f);
    }
}

void AHundredEyedSlagMonster::ReleaseEyeLaser(bool DamagePulse)
{
    if (!HasAuthority() || State != ESlagState::EyeLaserFire) return;
    const FVector Origin = LaserFocus();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SlagEyeLaser),false,this);
    if (!DamagePulse)
    {
        // Keep the visible beam clipped to current cover every frame, even
        // between damage pulses. Damage reuses this same beam segment.
        LaserEnd = Origin+LaserDirection*LaserRange;
        FHitResult Wall;
        if (GetWorld()->LineTraceSingleByChannel(Wall,Origin,LaserEnd,ECC_Visibility,Query)) LaserEnd = Wall.ImpactPoint;
        return;
    }
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByObjectType(Hits,Origin,LaserEnd,FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(LaserHitRadius),Query);
    TSet<TWeakObjectPtr<APawn>> PulseHitVictims;
    for (const FHitResult& Hit : Hits)
    {
        APawn* Victim = Cast<APawn>(Hit.GetActor());
        if (!IsValid(Victim) || !Victim->IsPlayerControlled() || PulseHitVictims.Contains(Victim)) continue;
        const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
        if (Vitals && Vitals->IsDead()) continue;
        FCollisionQueryParams Occlusion = Query;
        Occlusion.AddIgnoredActor(Victim);
        FHitResult Cover;
        if (GetWorld()->LineTraceSingleByChannel(Cover,Origin,Hit.ImpactPoint,ECC_Visibility,Occlusion)) continue;
        // Multiple collision bodies still receive only one hit in this
        // pulse; later pulses may damage the same living target again.
        PulseHitVictims.Add(Victim);
        UGameplayStatics::ApplyDamage(Victim,MagicAttack*LaserDamageMultiplier,
            GetController(),this,UHandBrainMagicDamage::StaticClass());
        if (State != ESlagState::EyeLaserFire || Dead()) return;
    }
}

void AHundredEyedSlagMonster::TickSpecialAttack(float Dt)
{
    auto Sample = [this](FName Name,float Duration) {
        if (auto* Asset = Clip(Name)) SampleClip(Name,Asset->GetPlayLength()*FMath::Clamp(StateSeconds/FMath::Max(.1f,Duration),0.f,1.f));
    };
    const bool Windup = State == ESlagState::EyeLaserWindup;
    APawn* Victim = Target.Get();
    const auto* Vitals = IsValid(Victim) ? Victim->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
    if (Status->BlocksMovement() || (Windup && (!IsValid(Victim) || (Vitals && Vitals->IsDead()) || !GetCharacterMovement()->IsMovingOnGround())))
    { EnterState(ESlagState::Recovery); return; }
    switch (State)
    {
    case ESlagState::EyeLaserWindup:
    {
        GetCharacterMovement()->StopMovementImmediately();
        const float ChargeSeconds = FMath::Max(1.5f,LaserWindupSeconds);
        const float Phase = FMath::Clamp(StateSeconds/ChargeSeconds,0.f,1.f);
        if (!bLaserAimLocked)
        {
            SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(),
                (Victim->GetActorLocation()-GetActorLocation()).GetSafeNormal2D().Rotation(),Dt,120.f));
        }
        Sample(TEXT("EyeLaserWindup"),ChargeSeconds);
        GetMesh()->TickAnimation(0.f,false); GetMesh()->RefreshBoneTransforms();
        if (!bLaserAimLocked)
        {
            LaserDirection = (Victim->GetActorLocation()+FVector(0,0,10.f)-LaserFocus()).GetSafeNormal();
            if (Phase >= .8f) bLaserAimLocked = true;
        }
        UpdateLaserFX(Phase,false);
        if (StateSeconds >= ChargeSeconds) EnterState(ESlagState::EyeLaserFire);
        break;
    }
    case ESlagState::EyeLaserFire:
    {
        GetCharacterMovement()->StopMovementImmediately();
        const float FireSeconds = FMath::Max(.1f,LaserFireSeconds);
        Sample(TEXT("EyeLaserFire"),FireSeconds);
        GetMesh()->TickAnimation(0.f,false); GetMesh()->RefreshBoneTransforms();
        ReleaseEyeLaser(false);
        const float DamageUntil = FMath::Min(StateSeconds,FireSeconds);
        const float Interval = FMath::Max(.05f,LaserDamageIntervalSeconds);
        // Use the attack clock, not one hit per frame. Catch up all elapsed
        // pulses at low FPS and exclude a pulse at/after the expiry boundary.
        while (LaserNextDamageSeconds < FireSeconds-UE_KINDA_SMALL_NUMBER
            && LaserNextDamageSeconds <= DamageUntil+UE_KINDA_SMALL_NUMBER)
        {
            LaserNextDamageSeconds += Interval;
            ReleaseEyeLaser(true);
            if (State != ESlagState::EyeLaserFire || Dead()) return;
        }
        UpdateLaserFX(1.f,true);
        if (StateSeconds >= FireSeconds) EnterState(ESlagState::EyeLaserRecover);
        break;
    }
    case ESlagState::EyeLaserRecover:
        Sample(TEXT("EyeLaserRecover"),LaserRecoverSeconds);
        if (StateSeconds >= LaserRecoverSeconds) EnterState(ESlagState::Recovery);
        break;
    default: break;
    }
}
