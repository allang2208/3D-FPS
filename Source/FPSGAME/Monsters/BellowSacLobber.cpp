#include "BellowSacLobber.h"
#include "../Combat/RangedAttackQuery.h"
#include "BellowSacProjectile.h"
#include "QuadrupedAnimationTemplate.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "MonsterCorpseRagdollComponent.h"
#include "ZombieDogAppearanceComponent.h"
#include "FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "../Skills/EnemyAttackDamage.h"

namespace BellowTiming
{
    constexpr float Lock = .85f, Release = 1.2f, LobEnd = 2.2f;
    constexpr float ShoveContact = .4f, ShoveEnd = 1.05f;
}
ABellowSacLobber::ABellowSacLobber(const FObjectInitializer& Initializer) : Super(Initializer)
{
    MonsterDisplayName = FText::FromString(TEXT("鼓囊 M-09"));
    bHowlOnEncounter = false; bUsePredictiveHunting = false; bUseRagdoll = false;
    WoundAppearance->bEnabled = false;
    WalkSpeed = ChaseSpeed = 80.f; AggroRadius = 3200.f; LeashRadius = 3200.f;
    BiteDamage = PounceDamage = 0.f;
    Level = 3; MaxHealth = 240.f;
    BaseEyeHeight = 35.f; AttackTrackingYawRate = 120.f;
    Tags.Remove(TEXT("Wolf")); Tags.AddUnique(TEXT("BellowSacLobber"));
}
double ABellowSacLobber::Clock() const
{
    const auto* GS = GetWorld()->GetGameState();
    return GS ? GS->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
}
void ABellowSacLobber::BeginPlay()
{
    Super::BeginPlay();
    InitializeBellowAudio();
    if (CorpseRagdoll && GetNetMode()!=NM_DedicatedServer)
        CorpseRagdoll->OnSoftBodyImpact.AddUObject(this,&ABellowSacLobber::OnCorpseGroundImpact);
    // First engagement arms its own staggered delay, not time since spawn.
    EncounterReadyAt = -1.;
}
bool ABellowSacLobber::Busy() const { return AttackClock.Kind != EBellowAttack::None || Super::Busy(); }
FVector ABellowSacLobber::Muzzle() const
{
    // Original SmartRig end bone. Local bone units are metres beneath its 100x FBX root.
    return GetMesh()->GetSocketTransform(TEXT("Bone_028")).TransformPosition(FVector(0,.13f,0));
}
bool ABellowSacLobber::Visible(APawn* Victim) const
{
    if (!IsValid(Victim) || !Victim->IsPlayerControlled()) return false;
    const auto* HealthComponent = Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if (HealthComponent && HealthComponent->IsDead()) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BellowSight), false, this);
    Query.AddIgnoredActor(Victim); FHitResult Hit;
    return !RangedAttackQuery::LineTraceSingle(GetWorld(), this, Hit, Muzzle(), Victim->GetPawnViewLocation(), ECC_Visibility, Query);
}
bool ABellowSacLobber::GroundTarget(APawn* Victim, FVector& Ground) const
{
    if (!IsValid(Victim)) return false;
    const FVector Feet = Victim->GetNavAgentLocation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BellowGround), false, this);
    Query.AddIgnoredActor(Victim); FHitResult Hit;
    if (!RangedAttackQuery::LineTraceSingle(GetWorld(), this, Hit, Feet+FVector(0,0,35), Feet-FVector(0,0,400), ECC_Visibility, Query)
        || Hit.ImpactNormal.Z < .4f) return false;
    Ground = Hit.ImpactPoint + Hit.ImpactNormal * (ABellowSacProjectile::CollisionRadius + 1.f);
    return true;
}
bool ABellowSacLobber::BuildArc(const FVector& Origin, const FVector& Ground, FVector& Velocity, const AActor* IntendedTarget) const
{
    const FVector Gravity(0,0,GetWorld()->GetGravityZ());
    const float BaseTime = FMath::Clamp(FVector::Dist2D(Origin,Ground) / 1000.f, .75f, 1.45f);
    for (float Extra : {0.f,.25f,.5f})
    {
        const float Duration = BaseTime + Extra;
        const FVector Launch = (Ground-Origin-Gravity*(.5f*Duration*Duration))/Duration;
        const int32 Steps = FMath::CeilToInt(Duration*20.f);
        FVector Previous = Origin; bool Clear = true;
        for (int32 I=1; I<=Steps; ++I)
        {
            const float T = Duration*I/Steps;
            const FVector Point = Origin+Launch*T+Gravity*(.5f*T*T);
            FHitResult Hit;
            if (ABellowSacProjectile::Sweep(GetWorld(),this,this,Previous,Point,ABellowSacProjectile::CollisionRadius,Hit,IntendedTarget))
            {
                Clear = I==Steps && FVector::DistSquared(Hit.Location,Ground)<FMath::Square(35.f);
                break;
            }
            Previous = Point;
        }
        if (Clear) { Velocity=Launch; return true; }
    }
    return false;
}
bool ABellowSacLobber::HasLane(APawn* Victim) const
{
    if (!IsValid(Victim)) return false;
    const float Distance = GetHorizontalDistanceTo(Victim);
    if (Distance < LobMinRange || Distance > LobMaxRange || !Visible(Victim)) return false;
    if (LaneTarget.Get()!=Victim || Clock()>=NextLaneQuery)
    {
        FVector Ground, Velocity;
        bClearLane=GroundTarget(Victim,Ground)&&BuildArc(Muzzle(),Ground,Velocity,Victim);
        LaneTarget=Victim; NextLaneQuery=Clock()+.35;
    }
    return bClearLane;
}
bool ABellowSacLobber::CanAttack(APawn* Victim) const
{
    if (!IsValid(Victim) || Busy() || Combat->IsControlled() || !GetCharacterMovement()->IsMovingOnGround()) return false;
    if (!AnimationSet || !Visible(Victim)) return false;
    if (GetHorizontalDistanceTo(Victim)<=ShoveRange && FMath::Abs(Victim->GetActorLocation().Z-GetActorLocation().Z)<130.f)
        return Clock()>=NextShoveAt && AnimationSet->FindSequence(TEXT("AttackShove"));
    return EncounterReadyAt>=0. && Clock()>=EncounterReadyAt && Clock()>=NextLobAt &&
        (!ActiveCapsule.IsValid() || ActiveCapsule->IsSpent()) && SacMesh && TelegraphMesh &&
        AnimationSet->FindSequence(TEXT("AttackLob")) && HasLane(Victim);
}
bool ABellowSacLobber::StartAttack(APawn* Victim)
{
    if (!HasAuthority() || !CanAttack(Victim)) return false;
    SetLocomotion(false,false);
    AttackTarget=Victim; bLocked=bReleased=false;
    AttackClock.Kind=GetHorizontalDistanceTo(Victim)<=ShoveRange?EBellowAttack::Shove:EBellowAttack::Lob;
    AttackClock.StartedAt=Clock();
    FaceAttackDirection(Victim->GetActorLocation()-GetActorLocation(),.1f);
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->bOrientRotationToMovement=false;
    OnRep_Attack(); ForceNetUpdate();
    if (auto* AI=Cast<AMonsterAIController>(GetController())) { AI->StopMovement(); AI->UpdateKnowledge(); }
    return true;
}
void ABellowSacLobber::OnRep_Attack()
{
    UpdatePressureAudio();
    if (AttackClock.Kind!=EBellowAttack::None && !Dead() && State!=EWolfState::Stagger)
        SampleAttack(FMath::Max(0.f,float(Clock()-AttackClock.StartedAt)));
    else if (!Super::Busy())
        if (auto* Anim=Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance())) Anim->ResumeLocomotion(.22f);
}
void ABellowSacLobber::SampleAttack(float Seconds,bool EvaluateMouth)
{
    if (auto* Anim=Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance()))
    {
        const FName Action=AttackClock.Kind==EBellowAttack::Lob?TEXT("AttackLob"):TEXT("AttackShove");
        if (Anim->ActiveAction!=Action) Anim->PlayTemplateAction(Action,true);
        Anim->SetActionTime(Seconds);
        if (EvaluateMouth)
        {
            Anim->FinishPoseTransition();
            GetMesh()->TickAnimation(0.f,false); GetMesh()->RefreshBoneTransforms();
        }
    }
}
void ABellowSacLobber::FinishAttack(bool Resume)
{
    if (AttackClock.Kind==EBellowAttack::None) return;
    if (PressureVoice) PressureVoice->Stop();
    if (HasAuthority())
    {
        // The full animation is part of the attack interval, not an extra wait.
        if (AttackClock.Kind==EBellowAttack::Lob)
            NextLobAt=AttackClock.StartedAt+FMath::Max(BellowTiming::LobEnd,FMath::FRandRange(LobCooldownMin,LobCooldownMax));
        else NextShoveAt=Clock()+2.5;
        AttackClock.Kind=EBellowAttack::None; AttackTarget.Reset(); ForceNetUpdate();
    }
    if (Resume && !Super::Busy())
        if (auto* Anim=Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance())) Anim->ResumeLocomotion(.22f);
    if (HasAuthority()) if (auto* AI=Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
}
void ABellowSacLobber::ReleaseCapsule()
{
    bReleased=true;
    // Sample the exact release pose even if this frame crossed the release event.
    SampleAttack(BellowTiming::Release,true);
    const FVector Origin=Muzzle(); FVector Velocity;
    if (!bLocked || !BuildArc(Origin,LockedGround,Velocity,AttackTarget.Get())) { NextLaneQuery=0.; return; }
    FActorSpawnParameters Params; Params.Owner=this; Params.Instigator=this;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if (auto* Projectile=GetWorld()->SpawnActor<ABellowSacProjectile>(Origin,FRotator::ZeroRotator,Params))
    {
        Projectile->Launch(this,Velocity,BlastDamage,BlastRadius,ImpactFuse,SacMesh,TelegraphMesh,SacMaterial,TelegraphMaterial);
        ActiveCapsule=Projectile;
        MulticastBellowAccent(FMath::RandBool()?TEXT("SpitA"):TEXT("SpitB"),Origin,Clock(),1.1f);
    }
}
void ABellowSacLobber::ApplyShove()
{
    bReleased=true;
    APawn* Victim=AttackTarget.Get();
    if (!Visible(Victim) || GetHorizontalDistanceTo(Victim)>ShoveRange+25.f ||
        FMath::Abs(Victim->GetActorLocation().Z-GetActorLocation().Z)>130.f ||
        FVector::DotProduct(GetActorForwardVector(),(Victim->GetActorLocation()-GetActorLocation()).GetSafeNormal2D())<.65f) return;
    UGameplayStatics::ApplyDamage(Victim,ShoveDamage,GetController(),this,UEnemyMeleeDamage::StaticClass());
}
void ABellowSacLobber::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdatePressureAudio();
    UpdateFootstepAudio(DeltaSeconds);
    if (AttackClock.Kind==EBellowAttack::None) return;
    if (Dead() || Combat->IsControlled() || State==EWolfState::Stagger)
    { if (HasAuthority()) FinishAttack(false); return; }
    const bool Lob=AttackClock.Kind==EBellowAttack::Lob;
    const float Elapsed=FMath::Max(0.f,float(Clock()-AttackClock.StartedAt));
    if (HasAuthority())
    {
        const auto* VictimHealth=AttackTarget.IsValid()?AttackTarget->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if (!bReleased && (!AttackTarget.IsValid() || (VictimHealth && VictimHealth->IsDead())))
        { FinishAttack(true); return; }
        if (!bLocked)
        {
            if (!Visible(AttackTarget.Get())) { FinishAttack(true); return; }
            FaceAttackDirection(AttackTarget->GetActorLocation()-GetActorLocation(),DeltaSeconds);
            if (!Lob || Elapsed>=BellowTiming::Lock)
            {
                if (Lob && GetHorizontalDistanceTo(AttackTarget.Get())<LobMinRange)
                { FinishAttack(true); return; }
                bLocked=!Lob || GroundTarget(AttackTarget.Get(),LockedGround);
                if (!bLocked) { FinishAttack(true); return; }
            }
        }
        if (!bReleased && Elapsed>=(Lob?BellowTiming::Release:BellowTiming::ShoveContact))
        {
            if (Lob) ReleaseCapsule(); else ApplyShove();
            if (Dead() || Combat->IsControlled() || State==EWolfState::Stagger) { FinishAttack(false); return; }
        }
        if (Elapsed>=(Lob?BellowTiming::LobEnd:BellowTiming::ShoveEnd)) { FinishAttack(true); return; }
    }
    SampleAttack(FMath::Min(Elapsed,Lob?BellowTiming::LobEnd:BellowTiming::ShoveEnd));
}
void ABellowSacLobber::NavigateCombat(AMonsterAIController* AI, APawn* Victim, const FVector& LastKnown)
{
    if (EncounterReadyAt<0. && Victim) EncounterReadyAt=Clock()+FMath::FRandRange(1.f,1.8f);
    const bool Clear=Victim && HasLane(Victim);
    // Hold an available firing lane even across floors; blocked arcs close via normal stairs.
    if (Clear && GetHorizontalDistanceTo(Victim)<=PreferredRange+250.f)
    { AI->StopMovement(); SetLocomotion(false,false); }
    else
    {
        const float Stop=Clear?PreferredRange:ShoveRange-45.f;
        if (Victim && FMath::Abs(GetActorLocation().Z-Victim->GetActorLocation().Z)<100.f && GetHorizontalDistanceTo(Victim)<=Stop)
        { AI->StopMovement(); SetLocomotion(false,false); }
        else { SetLocomotion(true,false); AI->NavigateTo(LastKnown,Stop); }
    }
}
void ABellowSacLobber::OnDeathPresentationStarted()
{
    PlayDeathAudio();
    // Fired capsules own their flight/fuse; death only cancels the un-emitted attack.
    if (HasAuthority()) { AttackClock.Kind=EBellowAttack::None; AttackTarget.Reset(); ForceNetUpdate(); }
}
void ABellowSacLobber::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps); DOREPLIFETIME(ABellowSacLobber,AttackClock);
}
