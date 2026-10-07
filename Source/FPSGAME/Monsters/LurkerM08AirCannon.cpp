#include "LurkerM08Monster.h"
#include "M08AirCannonProjectile.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "QuadrupedAnimationTemplate.h"
#include "Animation/AnimSequence.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Math/RotationMatrix.h"

namespace
{
const FName AirAction(TEXT("AttackAirCannon"));
constexpr float AirAimLockLead = .30f;
bool LivingTarget(const APawn* Victim)
{
    const auto* Health = IsValid(Victim) ? Victim->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
    return Health && !Health->IsDead();
}
}

FVector ALurkerM08Monster::AirCannonOrigin() const
{
    FTransform Frame;
    return AirCannonFrame(Frame) ? Frame.GetLocation() : GetActorLocation();
}

bool ALurkerM08Monster::AirCannonFrame(FTransform& Frame) const
{
    if (AirCannonRim.Num() != 16) return false;
    FVector Points[16], Average = FVector::ZeroVector;
    // Same linear blend skinning as the visible rim, on only 16 authored
    // vertices. No runtime mesh traversal or allocation of the full skin.
    for (int32 I = 0; I < 16; ++I)
    {
        Points[I] = FVector::ZeroVector;
        for (const auto& Influence : AirCannonRim[I].Influences)
            Points[I] += GetMesh()->GetSocketTransform(Influence.Bone, RTS_World)
                .TransformPosition(Influence.BoneLocalPosition) * Influence.Weight;
        Average += Points[I] / 16.f;
    }
    FVector Normal = FVector::ZeroVector;
    for (int32 I = 0; I < 16; ++I)
        Normal += FVector::CrossProduct(Points[I] - Average, Points[(I + 1) % 16] - Average);
    if (!Normal.Normalize()) return false;
    if (FVector::DotProduct(Normal, GetActorForwardVector()) < 0.f) Normal = -Normal;
    FVector Across = FVector::VectorPlaneProject(Points[0] - Points[8], Normal).GetSafeNormal();
    if (Across.IsNearlyZero()) return false;
    FVector Up = FVector::CrossProduct(Normal, Across).GetSafeNormal();
    if (FVector::DotProduct(Up, GetActorUpVector()) < 0.f) { Across = -Across; Up = -Up; }
    // Projected polygon centroid retains the real lip's asymmetric shape;
    // averaging the top bone and torso would drift during arch compression.
    FVector Centre = FVector::ZeroVector; double Area = 0.;
    for (int32 I = 0; I < 16; ++I)
    {
        const FVector A = Points[I] - Average, B = Points[(I + 1) % 16] - Average;
        const double Weight = FVector::DotProduct(FVector::CrossProduct(A, B), Normal);
        Centre += (Average + (A + B) / 3.f) * Weight; Area += Weight;
    }
    if (FMath::Abs(Area) < UE_SMALL_NUMBER) return false;
    Centre /= Area;
    double Width = 0., Height = 0.;
    for (const FVector& Point : Points)
    {
        Width = FMath::Max(Width, FMath::Abs(FVector::DotProduct(Point - Centre, Across)));
        Height = FMath::Max(Height, FMath::Abs(FVector::DotProduct(Point - Centre, Up)));
    }
    Frame = FTransform(FRotationMatrix::MakeFromZX(Normal, Across).ToQuat(), Centre,
        FVector(Width / 34., Height / 34., FMath::Min(Width, Height) / 34.));
    return true;
}

bool ALurkerM08Monster::CanAirCannon(APawn* Victim) const
{
    if (Busy() || Combat->IsControlled() || !HasAttackSupport() || !LivingTarget(Victim)
        || GetWorld()->GetTimeSeconds() < AirCannonReadyAt) return false;
    const auto* Def = AnimationSet ? AnimationSet->FindAction(AirAction) : nullptr;
    if (!Def || !Def->Sequence || Def->ContactStartSeconds < 0.f || !AirRingMesh || !AirRingMaterial) return false;
    FTransform MuzzleFrame;
    if (!AirCannonFrame(MuzzleFrame)) return false;
    const FVector Delta = Victim->GetActorLocation() - GetActorLocation();
    if (Delta.Size() < AirCannonMinRange || Delta.Size() > AirCannonRange
        || FVector::DotProduct(Delta.GetSafeNormal(), GetActorForwardVector()) < .2f) return false;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M08AirSight), false, this);
    Query.AddIgnoredActor(Victim);
    return !GetWorld()->LineTraceSingleByChannel(Hit, MuzzleFrame.GetLocation(), Victim->GetActorLocation(), ECC_Visibility, Query);
}

bool ALurkerM08Monster::CanAttack(APawn* Victim) const
{
    return CanAirCannon(Victim) || Super::CanAttack(Victim);
}

bool ALurkerM08Monster::StartAttack(APawn* Victim)
{
    if (!HasAuthority()) return false;
    if (!CanAirCannon(Victim)) return Super::CanAttack(Victim) && Super::StartAttack(Victim);
    StopSurfaceNavigation();
    SetLocomotion(false, false);
    AirCannonTarget = Victim;
    AirCannon = FLurkerAirCannonState();
    AirCannon.bActive = true;
    AirCannon.StartedAt = GetWorld()->GetTimeSeconds();
    AirCannon.AimPoint = Victim->GetActorLocation();
    // An interrupted wind-up still spends this attempt's cooldown.
    AirCannonReadyAt = AirCannon.StartedAt + FMath::Max(0.f, AirCannonCooldown);
    bAirCannonFired = false;
    GetCharacterMovement()->StopMovementImmediately();
    OnRep_AirCannon();
    UpdateAirCannonPose(0.f);
    if (auto* AI = Cast<AMonsterAIController>(GetController())) { AI->StopMovement(); AI->UpdateKnowledge(); }
    ForceNetUpdate();
    return true;
}

FVector ALurkerM08Monster::PredictAirCannonTarget(APawn* Victim, float ReleaseDelay) const
{
    const FVector Velocity = Victim->GetVelocity();
    const FVector Position = Victim->GetActorLocation() + Velocity * ReleaseDelay;
    const FVector Offset = Position - AirCannonOrigin();
    const double Speed = FMath::Max(1.f, AirCannonSpeed);
    const double A = Velocity.SizeSquared() - Speed * Speed;
    const double B = 2. * FVector::DotProduct(Offset, Velocity);
    const double C = Offset.SizeSquared();
    double Time = Offset.Size() / Speed;
    const double Discriminant = B * B - 4. * A * C;
    if (FMath::Abs(A) < 1.e-6)
    {
        if (B < -1.e-6) Time = -C / B;
    }
    else if (Discriminant >= 0.)
    {
        const double Root = FMath::Sqrt(Discriminant);
        const double T0 = (-B - Root) / (2. * A), T1 = (-B + Root) / (2. * A);
        if (T0 > 0. && T1 > 0.) Time = FMath::Min(T0, T1);
        else if (T0 > 0.) Time = T0;
        else if (T1 > 0.) Time = T1;
    }
    return Position + Velocity * FMath::Clamp(Time, 0., double(AirCannonRange) / Speed);
}

void ALurkerM08Monster::OnRep_AirCannon()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    if (AirCannon.bActive)
    {
        AirChargeRing->SetStaticMesh(AirChargeMesh ? AirChargeMesh.Get() : AirRingMesh.Get());
        AirChargeRing->SetMaterial(0, AirChargeMaterial ? AirChargeMaterial.Get() : AirRingMaterial.Get());
        if (!AirChargePoseHandle.IsValid())
            AirChargePoseHandle = GetMesh()->RegisterOnBoneTransformsFinalizedDelegate(
                FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateUObject(this, &ThisClass::UpdateAirChargeAttachment));
        const auto* GameState = GetWorld()->GetGameState();
        const double Now = !HasAuthority() && GameState ? GameState->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
        const float Clock = FMath::Max(0.f, float(Now - AirCannon.StartedAt));
        UpdateAirCannonVisual(Clock);
        UpdateAirChargeAttachment();
        if (!AirChargeAudio && AirChargeSound && !AirCannon.bAimLocked && !AirChargeRing->bHiddenInGame)
            AirChargeAudio = UGameplayStatics::SpawnSoundAttached(AirChargeSound, AirChargeRing, NAME_None,
                FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, .9f, 1.f, Clock, AirSoundAttenuation);
    }
    else
    {
        if (AirChargePoseHandle.IsValid())
        {
            GetMesh()->UnregisterOnBoneTransformsFinalizedDelegate(AirChargePoseHandle);
            AirChargePoseHandle.Reset();
        }
        AirChargeRing->SetHiddenInGame(true);
        AirChargeFraction = 0.f;
        if (AirChargeAudio) { AirChargeAudio->Stop(); AirChargeAudio = nullptr; }
        if (!Dead() && !Combat->IsControlled() && State != EWolfState::Stagger)
            if (auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance()); Anim && Anim->ActiveAction == AirAction)
                Anim->ResumeLocomotion(.16f);
    }
}

void ALurkerM08Monster::UpdateAirCannonPose(float SourceTime)
{
    if (auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance()))
    {
        if (Anim->ActiveAction != AirAction) Anim->PlayTemplateAction(AirAction, true);
        Anim->SetActionTime(SourceTime);
        Anim->ManualSpeed = 0.f;
    }
}

void ALurkerM08Monster::UpdateAirCannonVisual(float SourceTime)
{
    if (GetNetMode() == NM_DedicatedServer) return;
    const auto* Def = AnimationSet ? AnimationSet->FindAction(AirAction) : nullptr;
    if (!Def) { AirChargeRing->SetHiddenInGame(true); return; }
    const float Release = Def->ContactStartSeconds;
    const bool Charge = SourceTime >= 0.f && SourceTime < Release;
    AirChargeRing->SetHiddenInGame(!Charge);
    if (!Charge)
    {
        if (SourceTime >= Release && AirChargeAudio) { AirChargeAudio->Stop(); AirChargeAudio = nullptr; }
        return;
    }
    AirChargeFraction = FMath::Clamp(SourceTime / FMath::Max(.01f, Release), 0.f, 1.f);
    AirChargeRing->SetCustomPrimitiveDataFloat(0, .9f + .1f * AirChargeFraction);
    AirChargeRing->SetCustomPrimitiveDataFloat(1, AirChargeFraction);
    // Match the server's lock deadline locally; replication latency must not
    // erase the final white cue before the projectile is released.
    AirChargeRing->SetCustomPrimitiveDataFloat(2,
        AirCannon.bAimLocked || SourceTime >= Release - AirAimLockLead ? 1.f : 0.f);
    // Position is applied after the current frame's finalized skin pose.
}

void ALurkerM08Monster::UpdateAirChargeAttachment()
{
    if (!AirCannon.bActive || Dead() || Combat->IsControlled()) return;
    FTransform Frame;
    if (!AirCannonFrame(Frame)) return;
    Frame.SetScale3D(Frame.GetScale3D() * FMath::Lerp(1.08f, .90f, AirChargeFraction));
    AirChargeRing->SetWorldTransform(Frame);
}

void ALurkerM08Monster::EndPlay(const EEndPlayReason::Type Reason)
{
    if (AirChargePoseHandle.IsValid())
    {
        GetMesh()->UnregisterOnBoneTransformsFinalizedDelegate(AirChargePoseHandle);
        AirChargePoseHandle.Reset();
    }
    if (AirChargeAudio) { AirChargeAudio->Stop(); AirChargeAudio = nullptr; }
    if (IdleVoice) IdleVoice->Stop();
    if (CrawlVoice) CrawlVoice->Stop();
    Super::EndPlay(Reason);
}

void ALurkerM08Monster::TickAirCannon(float Dt)
{
    if (!AirCannon.bActive) return;
    if (Dead() || Combat->IsControlled() || State == EWolfState::Stagger)
    {
        if (HasAuthority()) EndAirCannon();
        else { AirChargeRing->SetHiddenInGame(true); if (AirChargeAudio) { AirChargeAudio->Stop(); AirChargeAudio = nullptr; } }
        return;
    }
    const auto* Def = AnimationSet ? AnimationSet->FindAction(AirAction) : nullptr;
    if (!Def || !Def->Sequence) { if (HasAuthority()) EndAirCannon(); return; }
    const auto* GameState = GetWorld()->GetGameState();
    const double Now = !HasAuthority() && GameState ? GameState->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
    const float Clock = FMath::Max(0.f, float(Now - AirCannon.StartedAt));
    const float Release = Def->ContactStartSeconds;
    if (HasAuthority())
    {
        if (!HasAttackSupport() || (!bAirCannonFired && !LivingTarget(AirCannonTarget.Get()))) { EndAirCannon(); return; }
        GetCharacterMovement()->StopMovementImmediately();
        if (!AirCannon.bAimLocked)
        {
            FaceAttackDirection(AirCannonTarget->GetActorLocation() - GetActorLocation(), Dt);
            if (Clock >= Release - AirAimLockLead)
            {
                AirCannon.AimPoint = PredictAirCannonTarget(AirCannonTarget.Get(), FMath::Max(0.f, Release - Clock));
                AirCannon.bAimLocked = true;
                ForceNetUpdate();
            }
        }
        if (!bAirCannonFired && Clock >= Release)
        {
            bAirCannonFired = true;
            // Sample the authored release, even when a frame crosses it. Only
            // this event refreshes bones synchronously; ordinary frames use mesh tick.
            UpdateAirCannonPose(Release);
            GetMesh()->TickAnimation(0.f, false);
            GetMesh()->RefreshBoneTransforms();
            FireAirCannon();
        }
        if (Clock >= Def->Sequence->GetPlayLength()) { EndAirCannon(); return; }
    }
    UpdateAirCannonPose(FMath::Min(Clock, Def->Sequence->GetPlayLength()));
    UpdateAirCannonVisual(Clock);
}

void ALurkerM08Monster::FireAirCannon()
{
    if (!HasAuthority() || Dead() || Combat->IsControlled()) return;
    FTransform MuzzleFrame;
    if (!AirCannonFrame(MuzzleFrame)) return;
    const FVector Origin = MuzzleFrame.GetLocation();
    const FVector Direction = (FVector(AirCannon.AimPoint) - Origin).GetSafeNormal();
    if (Direction.IsNearlyZero() || FVector::DotProduct(Direction, GetActorForwardVector()) < .15f) return;
    FActorSpawnParameters Params; Params.Owner = this; Params.Instigator = this;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if (auto* Projectile = GetWorld()->SpawnActor<AM08AirCannonProjectile>(Origin, Direction.Rotation(), Params))
        Projectile->Launch(this, Direction, MuzzleFrame);
}

void ALurkerM08Monster::EndAirCannon()
{
    AirCannon.bActive = false;
    AirCannonTarget.Reset();
    OnRep_AirCannon();
    if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
    ForceNetUpdate();
}
