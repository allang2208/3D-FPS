#include "MantisM27Monster.h"
#include "AIController.h"
#include "FatZombieAnimInstance.h"
#include "HumanoidKnockdownComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "FPSCombatHealthComponent.h"
#include "../Skills/IceWallCombat.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

AMantisM27Monster::AMantisM27Monster(const FObjectInitializer& Initializer) : Super(Initializer)
{
    Tags.Remove(TEXT("NurseZombie")); Tags.Add(TEXT("MantisM27"));
    MonsterDisplayName = FText::FromString(TEXT("螳螂 M27"));
    bReplicates = true; SetReplicateMovement(true);
    // Preserve the 190.27 cm source and use the existing 192 cm human nav agent.
    GetCapsuleComponent()->InitCapsuleSize(34.f, 96.f);
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed = SourceMoveSpeed;
    MaxHealth = Health = 280.f; AttackDamage = 32.f;
    Level = 7; Rank = EMonsterRank::Normal; ExperienceReward = 320;
    AggroRadius = 1500.f; AttackRange = 190.f;
    ContactTime = .48f; ContactEnd = .68f; RecoveryTime = .45f; CorpseSeconds = 20.f;
}

void AMantisM27Monster::AlignVisual()
{
    if (!VisualMesh) return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    const auto& Ref = VisualMesh->GetRefSkeleton();
    auto Position = [&Ref](int32 Bone)
    {
        FTransform T = Ref.GetRefBonePose()[Bone];
        for (int32 P = Ref.GetParentIndex(Bone); P != INDEX_NONE; P = Ref.GetParentIndex(P)) T *= Ref.GetRefBonePose()[P];
        return T.GetLocation();
    };
    const int32 Head = Ref.FindBoneIndex(TEXT("head")), Front = Ref.FindBoneIndex(TEXT("headfront"));
    if (Head != INDEX_NONE && Front != INDEX_NONE)
    {
        const FVector Direction = Position(Front)-Position(Head);
        GetMesh()->SetRelativeRotation(FRotator(0, -Direction.Rotation().Yaw, 0));
    }
    const auto Bounds = VisualMesh->GetBounds();
    GetMesh()->SetRelativeLocation(FVector(0,0,-GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()-Bounds.Origin.Z+Bounds.BoxExtent.Z));
}

void AMantisM27Monster::OnConstruction(const FTransform& Transform)
{ Super::OnConstruction(Transform); AlignVisual(); }
void AMantisM27Monster::BeginPlay()
{ AlignVisual(); Super::BeginPlay(); InitializeMantisAudio(); }

UFatZombieAnimInstance* AMantisM27Monster::PosePlayer()
{
    if (!Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance())) GetMesh()->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
    return Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance());
}
double AMantisM27Monster::ServerClock() const
{
    const auto* GS = GetWorld()->GetGameState();
    return GS ? GS->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
}
void AMantisM27Monster::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AMantisM27Monster, AttackSequence);
    DOREPLIFETIME(AMantisM27Monster, AttackStartedAt);
    DOREPLIFETIME(AMantisM27Monster, bCloaked);
    DOREPLIFETIME(AMantisM27Monster, PouncePhaseStartedAt);
    DOREPLIFETIME(AMantisM27Monster, PouncePhase);
}
void AMantisM27Monster::PresentAttack()
{
    UAnimSequence* Chosen = (AttackSequence & 1) ? LeftSlashClip.Get() : RightSlashClip.Get();
    if (Chosen) AttackClip = Chosen;
    if (auto* Animation = PosePlayer())
    {
        Animation->TransitionTo(AttackClip, false, true, .08f);
        if (!HasAuthority()) Animation->SetCombatTime(FMath::Clamp(float(ServerClock()-AttackStartedAt),0.f,GetAttackDuration()));
    }
}
void AMantisM27Monster::OnRep_AttackSequence()
{ if (State == ENurseState::Attack && PouncePhase == EM27PouncePhase::None) PresentAttack(); }

bool AMantisM27Monster::IsMeleeRecoveryPose() const
{
    return State == ENurseState::Recovery && PouncePhase == EM27PouncePhase::None && IsValid(CombatTarget());
}

void AMantisM27Monster::StartStateAnimation(UAnimSequence* Clip, bool bLoop)
{
    if (State == ENurseState::Attack)
    {
        if (PouncePhase != EM27PouncePhase::None) { PresentPounce(); return; }
        if (HasAuthority())
        {
            if (auto* AI = Cast<AAIController>(GetController())) AI->StopMovement();
            BeginShadowStrike();
            ++AttackSequence; AttackStartedAt = ServerClock();
            bContactConsumed = false; LockedFacing = GetActorForwardVector(); ForceNetUpdate();
        }
        PresentAttack(); return;
    }
    bContactConsumed = true;
    bMovingPresentation = State == ENurseState::Chase && GetVelocity().SizeSquared2D() > FMath::Square(12.f);
    if (State == ENurseState::Chase) Clip = bMovingPresentation ? WalkClip.Get() : IdleClip.Get();
    FMonsterClipTransition Settings;
    Settings.bContinueOutgoingLoop = true;
    Settings.InitialPlayRate = bMovingPresentation ? FMath::Clamp(GetVelocity().Size2D()/SourceMoveSpeed,.2f,2.5f) : 1.f;
    if (auto* Animation = PosePlayer()) Animation->TransitionTo(Clip, bLoop, false, .18f, Settings);
}
void AMantisM27Monster::Tick(float DeltaSeconds)
{
    TickCloak(DeltaSeconds);
    if (PouncePhase != EM27PouncePhase::None)
    {
        if (HasAuthority() && (State != ENurseState::Attack || (Knockdown && Knockdown->IsControlling()))) CancelPounce();
        if (PouncePhase != EM27PouncePhase::None && State == ENurseState::Attack)
        {
            // The pounce owns one clock; the generic melee tick must not hit or
            // finish recovery while a real capsule flight is still in progress.
            ACharacter::Tick(DeltaSeconds);
            TickPounce(DeltaSeconds);
            UpdateMantisAudio();
            return;
        }
    }
    if (HasAuthority() && State == ENurseState::Attack && !(Knockdown && Knockdown->IsControlling()) &&
        ServerClock()-AttackStartedAt < FMath::Max(0.f, ContactTime-.035f))
    {
        if (APawn* Victim = CombatTarget(); IsValid(Victim))
        {
            const FRotator Facing(0, (Victim->GetActorLocation()-GetActorLocation()).Rotation().Yaw, 0);
            SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), Facing, DeltaSeconds, 540.f));
            LockedFacing = GetActorForwardVector();
        }
    }
    Super::Tick(DeltaSeconds);
    UpdateMantisAudio();
    if (State == ENurseState::Dead || (Knockdown && Knockdown->IsControlling())) return;
    if (!HasAuthority() && State == ENurseState::Attack)
        SetAttackAnimationTime(FMath::Clamp(float(ServerClock()-AttackStartedAt),0.f,GetAttackDuration()));
    else if (!HasAuthority() && State == ENurseState::Chase) SetWalkAnimationRate(1.f);
}
void AMantisM27Monster::SetWalkAnimationRate(float)
{
    const float Speed = GetVelocity().Size2D();
    const bool Moving = Speed > (bMovingPresentation ? 6.f : 14.f);
    if (auto* Animation = PosePlayer())
    {
        if (Moving != bMovingPresentation)
        {
            bMovingPresentation = Moving;
            FMonsterClipTransition Settings; Settings.bContinueOutgoingLoop = true;
            Settings.InitialPlayRate = Moving ? FMath::Clamp(Speed/SourceMoveSpeed,.2f,2.5f) : 1.f;
            Animation->TransitionTo(Moving ? WalkClip.Get() : IdleClip.Get(),true,false,.18f,Settings);
        }
        Animation->SetLocomotionRate(Moving ? FMath::Clamp(Speed/SourceMoveSpeed,.2f,2.5f) : 1.f);
    }
}
void AMantisM27Monster::SetAttackAnimationTime(float Seconds)
{ if (auto* Animation = PosePlayer()) Animation->SetCombatTime(Seconds); }
void AMantisM27Monster::SampleBlade(float Time, FVector (&Points)[3])
{
    SetAttackAnimationTime(Time);
    GetMesh()->TickAnimation(0.f,false); GetMesh()->RefreshBoneTransforms();
    const bool Left = (AttackSequence & 1) != 0;
    Points[0] = GetMesh()->GetSocketLocation(Left ? TEXT("blade_root_l") : TEXT("blade_root_r"));
    Points[1] = GetMesh()->GetSocketLocation(Left ? TEXT("blade_mid_l") : TEXT("blade_mid_r"));
    Points[2] = GetMesh()->GetSocketLocation(Left ? TEXT("blade_tip_l") : TEXT("blade_tip_r"));
}
void AMantisM27Monster::SweepBlade(const FVector (&From)[3], const FVector (&To)[3])
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M27BladeContact),false,this);
    for (int32 Segment=0; Segment<2 && !bContactConsumed; ++Segment)
    {
        const FVector Span = To[Segment+1]-To[Segment];
        const FQuat Rotation = Span.IsNearlyZero() ? FQuat::Identity : FQuat::FindBetweenNormals(FVector::UpVector,Span.GetSafeNormal());
        TArray<FHitResult> Hits;
        GetWorld()->SweepMultiByObjectType(Hits,(From[Segment]+From[Segment+1])*.5f,(To[Segment]+To[Segment+1])*.5f,Rotation,
            FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeCapsule(BladeHitRadius,Span.Size()*.5f+BladeHitRadius),Query);
        for (const auto& Hit : Hits)
        {
            if (TryScytheHit(Cast<APawn>(Hit.GetActor()))) return;
        }
    }
}
bool AMantisM27Monster::TryScytheHit(APawn* Victim)
{
    if (bContactConsumed || !IsValid(Victim) || !Victim->IsPlayerControlled()) return false;
    const float Reach = MonsterCombatTuning::AttackDistance(AttackRange);
    const float VictimRadius = Victim->GetSimpleCollisionRadius();
    if (!CanMeleeFrom(Victim, GetActorLocation(), Reach+VictimRadius)) return false;
    const FVector Offset = Victim->GetActorLocation()-GetActorLocation();
    const FVector Planar(Offset.X, Offset.Y, 0);
    const float HalfAngle = 65.f;
    const bool Inside = Planar.IsNearlyZero() || FVector::DotProduct(Planar.GetSafeNormal(), LockedFacing) >=
        FMath::Cos(FMath::DegreesToRadians(HalfAngle));
    if (!Inside && FMath::PointDistToSegmentSquared(Planar, FVector::ZeroVector,
        LockedFacing.RotateAngleAxis(-HalfAngle,FVector::UpVector)*Reach) > FMath::Square(VictimRadius) &&
        FMath::PointDistToSegmentSquared(Planar, FVector::ZeroVector,
        LockedFacing.RotateAngleAxis(HalfAngle,FVector::UpVector)*Reach) > FMath::Square(VictimRadius)) return false;
    bContactConsumed = true; // Includes a blocked/parried contact; never reroll it.
    if (ApplyMeleeDamage(Victim) > 0.f) ++SuccessfulHits;
    return true;
}
void AMantisM27Monster::SweepMeleeEnvelope()
{
    // The two narrow blade segments can pass either side of a close capsule.
    // Fill that gap with a frontal scythe envelope, only in the authored contact
    // window. It shares range, line of sight and the single-hit consumption.
    const float Reach = MonsterCombatTuning::AttackDistance(AttackRange);
    TArray<FOverlapResult> Hits;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M27ScytheEnvelope),false,this);
    GetWorld()->OverlapMultiByObjectType(Hits,GetActorLocation(),FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(FVector(Reach,Reach,110.f)),Query);
    for (const auto& Hit : Hits)
        if (TryScytheHit(Cast<APawn>(Hit.GetActor()))) return;
}
void AMantisM27Monster::ProcessAttackContact(float Previous, float Current)
{
    if (!HasAuthority() || bCloaked || State!=ENurseState::Attack || bContactConsumed || Current<ContactTime || Previous>ContactEnd) return;
    if (IceWallCombat::ApplyMelee(this,CombatTarget(),MonsterCombatTuning::AttackDistance(AttackRange),AttackDamage*ActiveAttackDamageScale,.1f))
    { bContactConsumed=true; return; }
    const float Start=FMath::Max(Previous,ContactTime), End=FMath::Min(Current,ContactEnd);
    // At most four intervals cover a whole skipped window; no unbounded catch-up.
    const int32 Steps=FMath::Clamp(FMath::CeilToInt((End-Start)*60.f),1,4);
    FVector From[3],To[3]; SampleBlade(Start,From);
    for (int32 Step=1;Step<=Steps && State==ENurseState::Attack && !bContactConsumed;++Step)
    {
        SampleBlade(FMath::Lerp(Start,End,float(Step)/Steps),To); SweepBlade(From,To);
        for (int32 Point=0;Point<3;++Point) From[Point]=To[Point];
    }
    if (State==ENurseState::Attack && !bContactConsumed) SweepMeleeEnvelope();
    if (State==ENurseState::Attack) SetAttackAnimationTime(FMath::Min(Current,GetAttackDuration()));
}
void AMantisM27Monster::StartHitPresentation(UAnimSequence* Clip,float)
{
    CancelPounce();
    ActiveAttackDamageScale=1.f;
    bContactConsumed=true;
    if (auto* Animation=PosePlayer()) Animation->BeginHitReaction(Clip,-GetActorForwardVector(),Combat->IsParryReaction());
}
void AMantisM27Monster::SetHitPresentationTime(UAnimSequence*,float Elapsed,float Remaining)
{ if (auto* Animation=PosePlayer()) Animation->SetHitReactionTime(Elapsed,Remaining); }
void AMantisM27Monster::StartDeathPresentation()
{
    CancelPounce();
    bContactConsumed=true;
    if (Knockdown) Knockdown->StartDeath(DeathClip,0.f);
}
