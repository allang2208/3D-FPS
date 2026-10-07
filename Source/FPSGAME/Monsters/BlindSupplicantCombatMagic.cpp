#include "BlindSupplicantMonster.h"
#include "BlindSupplicantAnimInstance.h"
#include "M07MagicAttack.h"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "FPSCombatHealthComponent.h"
#include "HumanoidKnockdownComponent.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/IceWallCombat.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"

namespace M07SpellAim
{
FVector UpperBodyPoint(const APawn* Target)
{
    // Stay inside the target capsule, including while crouched. A center aim
    // incorrectly treats waist-high cover as hiding the entire player.
    return Target->GetActorLocation() + Target->GetActorUpVector() *
        Target->GetSimpleCollisionHalfHeight() * .65f;
}

bool ClearSegment(const APawn* Caster, const APawn* Target, const FVector& Start, const FVector& End)
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M07MagicSight), true, Caster);
    Query.AddIgnoredActor(Target);
    return !Caster->GetWorld()->LineTraceTestByChannel(Start, End, ECC_Visibility, Query);
}

FVector ProjectileIntercept(const FVector& Origin, const FVector& TargetPoint,
    const FVector& TargetVelocity, float SpeedCmS, float RangeCm)
{
    // Released M07 projectiles fly straight at a fixed world speed; they do
    // not inherit the caster's velocity. Solve |R + V*t| = Speed*t once.
    const double Speed = FMath::Clamp(SpeedCmS, 1.f, 10000.f);
    const double MaxFlightTime = FMath::Max(1.f, RangeCm) / Speed;
    const FVector Offset = TargetPoint - Origin;
    const double VelocitySquared = TargetVelocity.SizeSquared();
    const double A = VelocitySquared - Speed * Speed;
    const double B = 2.0 * FVector::DotProduct(Offset, TargetVelocity);
    const double C = Offset.SizeSquared();
    if (C <= UE_DOUBLE_SMALL_NUMBER || VelocitySquared <= UE_DOUBLE_SMALL_NUMBER) return TargetPoint;

    double FlightTime = MaxFlightTime + 1.0;
    const auto ConsiderRoot = [&FlightTime, MaxFlightTime](double Root)
    {
        if (Root > 0.0 && Root <= MaxFlightTime && Root < FlightTime) FlightTime = Root;
    };
    if (FMath::Abs(A) <= 1.e-6 * FMath::Max(VelocitySquared, Speed * Speed))
    {
        if (FMath::Abs(B) > UE_DOUBLE_SMALL_NUMBER) ConsiderRoot(-C / B);
    }
    else
    {
        const double Discriminant = B * B - 4.0 * A * C;
        if (Discriminant >= 0.0)
        {
            const double Root = FMath::Sqrt(Discriminant);
            // Stable quadratic roots avoid cancellation for fast approaching targets.
            const double Q = -.5 * (B + (B >= 0.0 ? Root : -Root));
            if (FMath::Abs(Q) > UE_DOUBLE_SMALL_NUMBER)
            {
                ConsiderRoot(Q / A);
                ConsiderRoot(C / Q);
            }
        }
    }
    // No intercept inside the existing flight range: retain a direct shot.
    return FlightTime <= MaxFlightTime ? TargetPoint + TargetVelocity * FlightTime : TargetPoint;
}
}

void ABlindSupplicantMonster::ApplyPlayerSkillCooldownDefaults()
{
    if (!bUsePlayerSkillCooldowns) return;
    // Read formal skill definitions once, outside AI queries and animation ticks.
    // A monster uses level-one base CD; player equipment/training/cheats do not apply.
    struct FSkillCooldowns
    {
        float Fire = ColdSteelSkills::LoadDefinition(TEXT("fireball")).Fireball.Cooldown;
        float Ice = ColdSteelSkills::LoadDefinition(TEXT("iceSpike")).IceSpike.Cooldown;
        float Lightning = ColdSteelSkills::LoadDefinition(TEXT("lightningStrike")).Lightning.Cooldown;
    };
    static const FSkillCooldowns Defaults;
    FireballCooldown = Defaults.Fire;
    IceColumnCooldown = Defaults.Ice;
    LightningCooldown = Defaults.Lightning;
}

bool ABlindSupplicantMonster::IsLivingPlayer(const APawn* Victim) const
{
    if (!IsValid(Victim) || !Victim->IsPlayerControlled()) return false;
    const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    return Vitals && !Vitals->IsDead();
}

bool ABlindSupplicantMonster::HasAttackSight(const APawn* Victim) const
{
    if (!IsValid(Victim) || !GetWorld()) return false;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M07AttackSight), false, this);
    Query.AddIgnoredActor(Victim);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation() + FVector(0, 0, 60),
        Victim->GetActorLocation(), ECC_Visibility, Query);
}

bool ABlindSupplicantMonster::HasMagicSight(const APawn* Victim) const
{
    if (!IsValid(Victim) || !GetWorld()) return false;
    // A stable head-height origin avoids sampling the lowered idle hand or
    // oscillating between grounded and floating animation poses in the BT.
    const FVector Origin = GetActorLocation() + GetActorUpVector() * GetSimpleCollisionHalfHeight() * .8f;
    return M07SpellAim::ClearSegment(this, Victim, Origin, M07SpellAim::UpperBodyPoint(Victim));
}

int32 ABlindSupplicantMonster::ReadyMagicIndex(const APawn* Victim) const
{
    if (!bMagicAttacksEnabled || !MagicGatherClip || !MagicReleaseClip || MagicAttack <= 0.f ||
        !IsLivingPlayer(Victim)) return INDEX_NONE;
    const float Distance = FVector::Dist2D(GetActorLocation(), Victim->GetActorLocation());
    if (Distance < FMath::Max(MagicMinimumDistance, MonsterCombatTuning::AttackDistance(AttackRange) - 15.f))
        return INDEX_NONE;
    const float Ranges[] = {FireballRange, IceColumnRange, LightningRange};
    const float Multipliers[] = {FireballDamageMultiplier, IceColumnDamageMultiplier, LightningDamageMultiplier};
    const double Now = GetWorld()->GetTimeSeconds();
    if (MagicGlobalReadyTime > Now) return INDEX_NONE;
    for (int32 Offset = 0; Offset < 3; ++Offset)
    {
        const int32 Index = (NextMagicIndex + Offset) % 3;
        if (MagicReadyTimes[Index] <= Now && Multipliers[Index] > 0.f &&
            FVector::Dist(GetActorLocation(), Victim->GetActorLocation()) <= Ranges[Index])
            return HasMagicSight(Victim) ? Index : INDEX_NONE;
    }
    return INDEX_NONE;
}

bool ABlindSupplicantMonster::CanAttackTarget(APawn* Victim) const
{
    if (!AttackCooldownReady() || State == ENurseState::Dead || !IsLivingPlayer(Victim)) return false;
    const float Reach = MonsterCombatTuning::AttackDistance(AttackRange) - 15.f;
    if (IceWallCombat::BlockingWall(this, Victim, Reach)) return true;
    const FVector Delta = Victim->GetActorLocation() - GetActorLocation();
    if (Delta.Size2D() <= Reach && FMath::Abs(Delta.Z) < 170.f && HasAttackSight(Victim)) return true;
    return ReadyMagicIndex(Victim) != INDEX_NONE;
}

float ABlindSupplicantMonster::CombatStoppingRange() const
{
    const float MeleeStop = FMath::Max(40.f, MonsterCombatTuning::AttackDistance(AttackRange) - 30.f);
    const int32 Ready = ReadyMagicIndex(CombatTarget());
    if (Ready == INDEX_NONE) return MeleeStop;
    const float Ranges[] = {FireballRange, IceColumnRange, LightningRange};
    return FMath::Max(MeleeStop, Ranges[Ready] * .70f);
}

bool ABlindSupplicantMonster::PrepareAttack(APawn* Victim)
{
    if (!HasAuthority() || !CanAttackTarget(Victim)) return false;
    StopMagicCharge();
    LockedAttackTarget = Victim;
    LockedAimPoint = Victim->GetActorLocation();
    LockedAttackDirection = (LockedAimPoint - GetActorLocation()).GetSafeNormal2D();
    bAttackCommitted = bAttackCancelled = bMagicReleaseStarted = false;
    AudioAttackKind = 0; AudioMagicReleased = false;
    const float MeleeReach = MonsterCombatTuning::AttackDistance(AttackRange) - 15.f;
    const bool Near = FVector::Dist2D(GetActorLocation(), LockedAimPoint) <= MeleeReach ||
        IceWallCombat::BlockingWall(this, Victim, MeleeReach);
    const int32 ElementIndex = Near ? INDEX_NONE : ReadyMagicIndex(Victim);
    if (ElementIndex != INDEX_NONE)
    {
        ActiveAttack = static_cast<EAttack>(static_cast<uint8>(EAttack::Fireball) + ElementIndex);
        AudioAttackKind = 2;
        const float Multipliers[] = {FireballDamageMultiplier, IceColumnDamageMultiplier, LightningDamageMultiplier};
        AttackDamageSnapshot = MagicAttack * Multipliers[ElementIndex];
        ActiveGatherDuration = MagicGatherClip->GetPlayLength();
        ActiveAttackDuration = ActiveGatherDuration + MagicReleaseClip->GetPlayLength();
        const float Cooldowns[] = {FireballCooldown, IceColumnCooldown, LightningCooldown};
        ReservedElementReadyTime = MagicReadyTimes[ElementIndex];
        ReservedGlobalReadyTime = MagicGlobalReadyTime;
        const double ReadyTime = GetWorld()->GetTimeSeconds() + FMath::Max(0.f, Cooldowns[ElementIndex]);
        MagicReadyTimes[ElementIndex] = MagicGlobalReadyTime = ReadyTime;
        bMagicCooldownReserved = true;
    }
    else
    {
        ActiveAttack = bNextAttackLeft || !MeleeRightClip ? EAttack::SweepLeft : EAttack::SweepRight;
        AudioAttackKind = 1;
        bNextAttackLeft = !bNextAttackLeft;
        AttackClip = ActiveAttack == EAttack::SweepLeft ? MeleeLeftClip : MeleeRightClip;
        if (!AttackClip) { ActiveAttack = EAttack::None; return false; }
        ActiveMeleePlaybackRate = FMath::Clamp(MeleePlaybackRate, .5f, 2.5f);
        const float Center = ActiveAttack == EAttack::SweepLeft ? LeftContactTime : RightContactTime;
        ContactTime = FMath::Max(0.f, Center - ContactWindowSeconds * .5f) / ActiveMeleePlaybackRate;
        ContactEnd = (Center + ContactWindowSeconds * .5f) / ActiveMeleePlaybackRate;
        ActiveGatherDuration = 0.f;
        ActiveAttackDuration = AttackClip->GetPlayLength() / ActiveMeleePlaybackRate;
        AttackDamageSnapshot = AttackDamage;
    }
    return true;
}

bool ABlindSupplicantMonster::IsMagicAttack() const
{
    return ActiveAttack == EAttack::Fireball || ActiveAttack == EAttack::IceColumn || ActiveAttack == EAttack::Lightning;
}

EM07MagicElement ABlindSupplicantMonster::ActiveMagicElement() const
{
    return static_cast<EM07MagicElement>(static_cast<uint8>(ActiveAttack) - static_cast<uint8>(EAttack::Fireball));
}

float ABlindSupplicantMonster::GetAttackDuration() const
{
    return ActiveAttackDuration > 0.f ? ActiveAttackDuration : Super::GetAttackDuration();
}

FVector ABlindSupplicantMonster::AttackClawPosition() const
{
    const FName Finger = ActiveAttack == EAttack::SweepRight ? TEXT("middle_03_r") : TEXT("middle_03_l");
    const FName Hand = ActiveAttack == EAttack::SweepRight ? TEXT("hand_r") : TEXT("hand_l");
    return GetMesh()->GetSocketLocation(GetMesh()->DoesSocketExist(Finger) ? Finger : Hand);
}

FVector ABlindSupplicantMonster::CastingPalmPosition() const
{
    // Hand bone is the wrist; the metacarpal cluster defines the actual palm.
    return GetMesh()->GetSocketLocation(TEXT("middle_metacarpal_l"));
}

FVector ABlindSupplicantMonster::CastingSpellPosition() const
{
    // Use the caster's forward axis so turning the wrist cannot swing the
    // charge back into the chest. ReleaseMagic uses this same origin.
    const float ForwardOffset = ActiveMagicElement() == EM07MagicElement::Lightning
        ? 0.f : MagicChargeForwardOffsetCm;
    return CastingPalmPosition() + GetActorForwardVector() * ForwardOffset;
}

void ABlindSupplicantMonster::UpdateMagicChargePose()
{
    if (!MagicCharge) return;
    const EM07MagicElement Element = ActiveMagicElement();
    const FRotator Facing = Element == EM07MagicElement::Lightning
        ? GetMesh()->GetSocketRotation(TEXT("middle_metacarpal_l")) : GetActorRotation();
    MagicCharge->SetWorldLocationAndRotation(CastingSpellPosition(), Facing);
    // Ice reads explicit world positions as well as the component transform.
    AM07MagicAttack::ConfigureCharge(MagicCharge, Element, MagicChargeFraction);
}

void ABlindSupplicantMonster::BeginMagicCharge()
{
    if (!IsMagicAttack() || GetNetMode() == NM_DedicatedServer) return;
    StopMagicCharge();
    if (auto* System = AM07MagicAttack::ChargeSystem(ActiveMagicElement()))
    {
        MagicCharge = UNiagaraFunctionLibrary::SpawnSystemAttached(System, GetMesh(), NAME_None,
            FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::SnapToTarget, false);
        if (MagicCharge)
        {
            MagicCharge->SetCastShadow(false);
            MagicCharge->SetAbsolute(true, true, true);
            MagicChargeFraction = 0.f;
            // Follow the evaluated palm, after its final bone transforms.
            // This uses the existing pose update, without another bone refresh.
            MagicChargePoseHandle = GetMesh()->RegisterOnBoneTransformsFinalizedDelegate(
                FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateUObject(this, &ThisClass::UpdateMagicChargePose));
            UpdateMagicChargePose();
        }
    }
}

void ABlindSupplicantMonster::StopMagicCharge()
{
    if (MagicChargePoseHandle.IsValid())
    {
        GetMesh()->UnregisterOnBoneTransformsFinalizedDelegate(MagicChargePoseHandle);
        MagicChargePoseHandle.Reset();
    }
    if (MagicCharge) { MagicCharge->DeactivateImmediate(); MagicCharge->DestroyComponent(); MagicCharge = nullptr; }
}

void ABlindSupplicantMonster::CancelPendingAttack()
{
    if (bMagicCooldownReserved && !bAttackCommitted && IsMagicAttack())
    {
        MagicReadyTimes[static_cast<int32>(ActiveMagicElement())] = ReservedElementReadyTime;
        MagicGlobalReadyTime = ReservedGlobalReadyTime;
    }
    bMagicCooldownReserved = false;
    bAttackCancelled = true;
    StopMagicCharge();
}

void ABlindSupplicantMonster::InterruptAttack(float Seconds)
{
    CancelPendingAttack();
    Super::InterruptAttack(Seconds);
}

void ABlindSupplicantMonster::ReleaseMagic()
{
    if (!HasAuthority() || bAttackCommitted || bAttackCancelled || State != ENurseState::Attack || !IsMagicAttack()) return;
    APawn* Victim = LockedAttackTarget.Get();
    if (!IsLivingPlayer(Victim) || CombatTarget() != Victim ||
        (Knockdown && Knockdown->IsControlling())) { CancelPendingAttack(); return; }
    // Sample only at commitment, so the release transform comes from this pose.
    GetMesh()->TickAnimation(0.f, false);
    GetMesh()->RefreshBoneTransforms();
    const FVector Origin = CastingSpellPosition();
    const EM07MagicElement Element = ActiveMagicElement();
    const int32 Index = static_cast<int32>(Element);
    const float Ranges[] = {FireballRange, IceColumnRange, LightningRange};
    const float Speeds[] = {FireballSpeed, IceColumnSpeed, 1.f};
    const float Radii[] = {FireballImpactRadius, IceColumnImpactRadius, 1.f};
    // Gathering/release latency has already elapsed at this contact frame.
    // Use the current target snapshot rather than adding that delay twice.
    // Lightning resolves immediately; only fire/ice need flight-time lead.
    const FVector TargetPoint = M07SpellAim::UpperBodyPoint(Victim);
    if (!M07SpellAim::ClearSegment(this, Victim, Origin, TargetPoint))
    { CancelPendingAttack(); return; }
    LockedAimPoint = TargetPoint;
    if (Element != EM07MagicElement::Lightning)
    {
        LockedAimPoint = M07SpellAim::ProjectileIntercept(Origin, LockedAimPoint, Victim->GetVelocity(),
            Speeds[Index], Ranges[Index]);
        // Keep the existing lead shot when its straight segment is clear.
        // A predicted position behind cover must not override the visible aim.
        if (!LockedAimPoint.Equals(TargetPoint, .1f) &&
            !M07SpellAim::ClearSegment(this, Victim, Origin, LockedAimPoint)) LockedAimPoint = TargetPoint;
    }
    const FTransform Transform((LockedAimPoint - Origin).Rotation(), Origin);
    auto* Spell = GetWorld()->SpawnActorDeferred<AM07MagicAttack>(AM07MagicAttack::StaticClass(), Transform,
        this, this, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if (!Spell) { CancelPendingAttack(); return; }
    // Establish the edge before FinishSpawning; instant lightning can synchronously kill this caster.
    bAttackCommitted = true;
    // The CD reserved at successful gathering start remains; release does not restart it.
    bMagicCooldownReserved = false;
    NextMagicIndex = (Index + 1) % 3;
    StopMagicCharge();
    Spell->Initialize(this, LockedAimPoint, Element, AttackDamageSnapshot, Ranges[Index], Speeds[Index], Radii[Index]);
    if (IsValid(Spell) && !Spell->IsActorBeingDestroyed()) Spell->FinishSpawning(Transform);
}

void ABlindSupplicantMonster::SweepClaw(FVector From, FVector To)
{
    if (bAttackCommitted || bAttackCancelled) return;
    // The V32 claw tip stays about a metre to the side of a frontal target.
    // Cover the whole palm/claw span instead of extruding only the fingertip
    // sphere. The same volume follows the arc and the configured reach.
    const FName HandBone = ActiveAttack == EAttack::SweepRight ? TEXT("hand_r") : TEXT("hand_l");
    const FVector HandToClaw = AttackClawPosition() - GetMesh()->GetSocketLocation(HandBone);
    const FVector CenterOffset = HandToClaw * -.5f;
    const float Radius = FMath::Max(1.f, SweepHitRadius);
    const FQuat Orientation = HandToClaw.IsNearlyZero() ? FQuat::Identity :
        FQuat::FindBetweenNormals(FVector::UpVector, HandToClaw.GetSafeNormal());
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M07SweepContact), false, this);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByObjectType(Hits, From + CenterOffset, To + CenterOffset, Orientation,
        FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeCapsule(Radius, Radius + HandToClaw.Size() * .5f), Query);
    for (const FHitResult& Hit : Hits)
    {
        auto* Victim = Cast<APawn>(Hit.GetActor());
        if (!IsLivingPlayer(Victim)) continue;
        const FVector Delta = Victim->GetActorLocation() - GetActorLocation();
        if (Delta.Size2D() > MonsterCombatTuning::AttackDistance(AttackRange) + Victim->GetSimpleCollisionRadius() ||
            FVector::DotProduct(Delta.GetSafeNormal2D(), LockedAttackDirection) < .20f || !HasAttackSight(Victim)) continue;
        bAttackCommitted = true;
        UGameplayStatics::ApplyDamage(Victim, AttackDamageSnapshot, GetController(), this, UEnemyMeleeDamage::StaticClass());
        ++SuccessfulHits;
        return;
    }
}

void ABlindSupplicantMonster::ProcessAttackContact(float Previous, float Current)
{
    if (bAttackCancelled || State != ENurseState::Attack) return;
    if (IsMagicAttack())
    {
        if (!IsLivingPlayer(LockedAttackTarget.Get()) || CombatTarget() != LockedAttackTarget.Get())
        { CancelPendingAttack(); return; }
        const float Contact = ActiveGatherDuration + FMath::Clamp(MagicReleaseContactTime, 0.f, MagicReleaseClip->GetPlayLength());
        if (Previous <= Contact && Current >= Contact) ReleaseMagic();
        return;
    }
    if (ActiveAttack != EAttack::SweepLeft && ActiveAttack != EAttack::SweepRight) return;
    // Only evaluate the additional contact pose during the short horizontal sweep window.
    if (Current >= ContactTime && Previous <= ContactEnd && !bAttackCommitted)
    {
        // Faster sweeps may cross a window boundary within a frame. Sample
        // the actual clipped arc, not the windup or a pose after recovery.
        FVector From = PreviousClaw;
        if (Previous < ContactTime)
        {
            SetAttackAnimationTime(ContactTime);
            GetMesh()->TickAnimation(0.f, false);
            GetMesh()->RefreshBoneTransforms();
            From = AttackClawPosition();
        }
        SetAttackAnimationTime(FMath::Min(Current, ContactEnd));
        GetMesh()->TickAnimation(0.f, false);
        GetMesh()->RefreshBoneTransforms();
        const FVector Claw = AttackClawPosition();
        SetAttackAnimationTime(FMath::Min(Current, ActiveAttackDuration));
        if (IceWallCombat::ApplyMelee(this, LockedAttackTarget.Get(), MonsterCombatTuning::AttackDistance(AttackRange),
            AttackDamageSnapshot, .20f)) { bAttackCommitted = true; return; }
        SweepClaw(From, Claw);
        if (State != ENurseState::Attack || bAttackCancelled) return;
        const float Extension = FMath::Max(0.f, MonsterCombatTuning::AttackDistance(AttackRange) - SweepHitRadius -
            FVector::DotProduct(Claw - GetActorLocation(), LockedAttackDirection));
        SweepClaw(Claw, Claw + LockedAttackDirection * Extension);
    }
    PreviousClaw = AttackClawPosition();
}
