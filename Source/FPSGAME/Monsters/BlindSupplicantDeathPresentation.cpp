#include "BlindSupplicantMonster.h"
#include "BlindSupplicantAnimInstance.h"
#include "HumanoidKnockdownComponent.h"
#include "MonsterCombatTuning.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodyInstance.h"
#include "TimerManager.h"

void ABlindSupplicantMonster::StartDeathPresentation()
{
    CancelPendingAttack();
    GetWorldTimerManager().ClearTimer(WallPresentationTimer);
    bPresentingWallListen = false;
    StopWallMimic();
    auto* CharacterMesh = GetMesh();
    CharacterMesh->SetSimulatePhysics(false);
    CharacterMesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    DeathPresentationStart = GetWorld()->GetTimeSeconds();
    DeathGroundZ = GetActorLocation().Z - GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if (DeathClip)
    {
        if (auto* Animation = PosePlayer())
            Animation->TransitionTo(DeathClip, false, true, AnimationBlendSeconds);
    }
    else StartDeathRagdoll();
}

void ABlindSupplicantMonster::UpdateDeathPresentation()
{
    if (State != ENurseState::Dead || bRagdollStarted || DeathPresentationStart < 0. || !DeathClip) return;
    const float Handoff = DeathClip->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction;
    const float Elapsed = FMath::Max(0.f, static_cast<float>(GetWorld()->GetTimeSeconds() - DeathPresentationStart));
    if (auto* Animation = PosePlayer()) Animation->SetCombatTime(FMath::Min(Elapsed, Handoff));
    if (Elapsed >= Handoff) StartDeathRagdoll();
}

void ABlindSupplicantMonster::ClearDeathHandoffPenetration()
{
    auto* CharacterMesh = GetMesh();
    // Update actual anatomical volumes before the first solver step. The clip
    // owns the fall; this only clears small floor/slope overlap at the handoff.
    CharacterMesh->UpdateKinematicBonesToAnim(CharacterMesh->GetComponentSpaceTransforms(),
        ETeleportType::TeleportPhysics, false, EAllowKinematicDeferral::DisallowDeferral);
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(M07DeathHandoffFloor), false, this);
    float Lift = 0.f;
    for (const auto* Body : CharacterMesh->Bodies)
    {
        if (!Body || !Body->IsValidBodyInstance()) continue;
        const FBox Bounds = Body->GetBodyBounds();
        if (!Bounds.IsValid) continue;
        const FVector Bottom(Bounds.GetCenter().X, Bounds.GetCenter().Y, Bounds.Min.Z);
        FHitResult Floor;
        const FVector Start(Bottom.X, Bottom.Y, FMath::Max(double(DeathGroundZ + 40.f), Bottom.Z + 20.));
        if (GetWorld()->LineTraceSingleByObjectType(Floor, Start, Bottom - FVector(0, 0, 30), Objects, Query) &&
            Floor.ImpactNormal.Z > .65f)
            Lift = FMath::Max(Lift, static_cast<float>(Floor.ImpactPoint.Z + 1.f - Bottom.Z));
    }
    // Major sinking must be fixed in the authored skeletal fall, not hidden
    // by shifting a corpse a body-length upward.
    Lift = FMath::Clamp(Lift, 0.f, 20.f);
    if (Lift <= .1f) return;
    CharacterMesh->AddWorldOffset(FVector(0, 0, Lift), false, nullptr, ETeleportType::TeleportPhysics);
    CharacterMesh->ForceClothNextUpdateTeleportAndReset();
    CharacterMesh->UpdateKinematicBonesToAnim(CharacterMesh->GetComponentSpaceTransforms(),
        ETeleportType::TeleportPhysics, false, EAllowKinematicDeferral::DisallowDeferral);
}

void ABlindSupplicantMonster::StartDeathRagdoll()
{
    if (State != ENurseState::Dead || bRagdollStarted) return;
    const float Handoff = DeathClip ? DeathClip->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction : 0.f;
    if (DeathClip)
        if (auto* Animation = PosePlayer()) Animation->HoldClipAtTime(Handoff);
    GetMesh()->TickAnimation(0.f, false);
    GetMesh()->RefreshBoneTransforms();
    ClearDeathHandoffPenetration();
    bRagdollStarted = true;
    if (Knockdown) Knockdown->StartDeath(DeathClip, Handoff);
    else Super::StartDeathPresentation();
}
