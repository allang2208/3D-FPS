#include "UnknownHumanoid.h"
#include "UnknownHumanoidBow.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "UnknownSpellCombat.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "WitchProjectile.h"
#include "../Characters/FPSModularOutfitComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSFireballProjectile.h"
#include "../Skills/MagicOcclusion.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/FPSBallisticsComponent.h"
#include "../Weapons/FPSWeaponFXComponent.h"
#include "../Weapons/Super90Spread.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/OverlapResult.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    constexpr float MeleeSweepRadius = 16.f;

    FVector MissDirection(const FVector& Start,const FVector& Aim,float TargetRadius,float PelletCone)
    {
        // Aim beside the capsule, with enough clearance for the outer pellets of a shell.
        const FVector Offset=Aim-Start;
        const double Distance=FMath::Max(1.,Offset.Size2D());
        const double EdgeAngle=FMath::Asin(FMath::Clamp(TargetRadius/Distance,0.,1.));
        const double Margin=FMath::DegreesToRadians(FMath::FRandRange(1.f,4.f));
        const double Angle=FMath::Min(EdgeAngle+PelletCone+Margin,FMath::DegreesToRadians(80.));
        const double Side=FMath::RandBool()?1.:-1.;
        return Offset.GetSafeNormal().RotateAngleAxisRad(Side*Angle,FVector::UpVector);
    }
}

AUnknownHumanoid::AUnknownHumanoid()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    SetReplicateMovement(true);
    Tags.Add(TEXT("Enemy"));
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    static ConstructorHelpers::FClassFinder<AMonsterAIController> ControllerAsset(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    AIControllerClass = ControllerAsset.Class;
    // Same shared human navigation profile as the facility staff.
    GetCapsuleComponent()->InitCapsuleSize(34.f,92.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->SetRelativeLocationAndRotation(FVector(0,0,-92),FRotator(0,-90,0));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->MaxStepHeight = 40.f;
    GetCharacterMovement()->GetNavAgentPropertiesRef().AgentStepHeight = 40.f;
    GetCharacterMovement()->GetNavMovementProperties()->bUseAccelerationForPaths = true;
    GetCharacterMovement()->RotationRate = FRotator(0,540,0);
    bUseControllerRotationYaw = false;
    Combat = CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("MonsterCombat"));
    Status = CreateDefaultSubobject<UCombatStatusFormula>(TEXT("CombatStatus"));
    Clothing = CreateDefaultSubobject<UFPSModularOutfitComponent>(TEXT("PlayerOutfit"));
    Clothing->SetExternalWorldBody(GetMesh());
    Ballistics = CreateDefaultSubobject<UFPSBallisticsComponent>(TEXT("Ballistics"));
    HeldWeapon = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("HeldWeapon"));
    HeldWeapon->SetupAttachment(GetMesh());
    HeldWeapon->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HeldWeapon->SetCanEverAffectNavigation(false);
}

void AUnknownHumanoid::BeginPlay()
{
    Home = GetActorLocation();
    Super::BeginPlay();
    if (HasAuthority() && !Sheet && !Configure(EUnknownRole::Melee,10)) { Destroy(); return; }
    OnRep_Loadout();
}

void AUnknownHumanoid::EndPlay(const EEndPlayReason::Type Reason)
{
    bPendingContact=false; ShotsLeft=0;
    AttackTarget.Reset(); TacticalTarget.Reset();
    if(BowPoseFinalized.IsValid())GetMesh()->UnregisterOnBoneTransformsFinalizedDelegate(BowPoseFinalized);
    if (AppearanceLoad) AppearanceLoad->CancelHandle();
    if (WeaponAudioLoad) WeaponAudioLoad->CancelHandle();
    Super::EndPlay(Reason);
}

void AUnknownHumanoid::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AUnknownHumanoid,Loadout);
    DOREPLIFETIME(AUnknownHumanoid,Motion);
    DOREPLIFETIME(AUnknownHumanoid,GunAimPoint);
    DOREPLIFETIME(AUnknownHumanoid,bGunTracking);
    DOREPLIFETIME(AUnknownHumanoid,bBowBlades);
    DOREPLIFETIME(AUnknownHumanoid,Health);
    DOREPLIFETIME(AUnknownHumanoid,MaxHealth);
    DOREPLIFETIME(AUnknownHumanoid,Defense);
    DOREPLIFETIME(AUnknownHumanoid,MagicDefense);
    DOREPLIFETIME(AUnknownHumanoid,CritResistance);
    DOREPLIFETIME(AUnknownHumanoid,AttributeWeight);
}

float AUnknownHumanoid::ServerTime() const
{
    const auto* State = GetWorld()->GetGameState();
    return State ? State->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
}

bool AUnknownHumanoid::Controlled() const
{
    return Motion.Action==EUnknownAction::Stagger || Status->IsFrozen() || Status->IsStunned() || Status->IsPetrified();
}

FVector AUnknownHumanoid::AimOrigin() const
{
    return bIsCrouched?GetPawnViewLocation():GetActorLocation()+FVector(0,0,49);
}

float AUnknownHumanoid::MeleeWindup() const
{
    return MeleeContactFraction*AttackSeconds;
}

FVector AUnknownHumanoid::MeleeDirection(const APawn& Target) const
{
    return (Target.GetActorLocation()+FVector(0,0,14)-AimOrigin()).GetSafeNormal();
}

bool AUnknownHumanoid::InMeleeStartRange(const APawn& Target) const
{
    // Predict a short part of the windup. Steering, braking at the target and a player's
    // ability to dodge make extrapolating an entire slow swing from one velocity unreliable.
    const float Horizon=FMath::Min(MeleeWindup(),.32f);
    const FVector Direction=MeleeDirection(Target);
    const FVector TargetCenter=Target.GetActorLocation()+Target.GetVelocity()*Horizon;
    const double Travel=FMath::Max(0.,FVector::Dist2D(GetActorLocation(),TargetCenter)-PreferredRange);
    const FVector Advance=(GetVelocity()*FVector(1,1,0)*Horizon).GetClampedToMaxSize(Travel);
    const FVector Start=AimOrigin()+Advance;
    float Radius,HalfHeight;
    Target.GetSimpleCollisionCylinder(Radius,HalfHeight);
    const FVector Axis(0,0,FMath::Max(0.f,HalfHeight-Radius));
    FVector WeaponPoint,BodyPoint;
    FMath::SegmentDistToSegmentSafe(Start,Start+Direction*AttackRange,TargetCenter-Axis,TargetCenter+Axis,WeaponPoint,BodyPoint);
    return FVector::DistSquared(WeaponPoint,BodyPoint)<=FMath::Square(Radius+MeleeSweepRadius);
}

bool AUnknownHumanoid::CanPursueDuringSwing(const APawn* VisibleTarget) const
{
    return Motion.Action==EUnknownAction::Swing
        && VisibleTarget && AttackTarget.Get()==VisibleTarget && !Controlled();
}

bool AUnknownHumanoid::CanAttack(APawn* Target) const
{
    if (!Sheet || !IsValid(Target) || !Target->IsPlayerControlled() || Busy() || Controlled() || ServerTime()<NextAttack) return false;
    if (const auto* Vitals=Target->FindComponentByClass<UFPSCombatHealthComponent>(); Vitals && Vitals->IsDead()) return false;
    if (Loadout.Role==EUnknownRole::Magic && !HasChosenMagic()) return false;
    if (IsRanged())
    {
        if (const auto* AI=Cast<AMonsterAIController>(GetController()); AI &&
            (!AI->bDecisionEnabled || TacticalTarget.Get()!=Target)) return false;
        if (CanActOutOfSight()) return true;
        if (Position==EUnknownPosition::Sheltered) return false;
        // The player's thunder lance plants the feet while charging. Do not
        // start that commitment in the middle of a withdrawal or cover route.
        if (ChosenMagicId()==TEXT("thunderLance") && (bRetreating || Position==EUnknownPosition::SeekCover ||
            Position==EUnknownPosition::MoveToPeek || Position==EUnknownPosition::Adjust || ServerTime()<CrowdYieldUntil)) return false;
        // Walking/retreating fire is permitted; a cover dash first lowers the
        // weapon and must decelerate before acquiring another aimed burst.
        if ((UsesMobileGunCombat() && Magazine<=0) || bSprintIntent ||
            GetVelocity().SizeSquared2D()>FMath::Square(WalkSpeed*Status->MovementMultiplier()*1.1f)) return false;
    }
    if ((!IsRanged() || Loadout.Role==EUnknownRole::Bow) && Stamina<StaminaCost) return false;
    if (!FacingTarget(*Target)) return false;
    if (IsRanged())
        return FVector::DistSquared(GetActorLocation(),Target->GetActorLocation())<=FMath::Square(AttackRange) &&
            HasFiringLane(AimOrigin(),*Target,Target->GetActorLocation());
    if (!InMeleeStartRange(*Target)) return false;
    FHitResult Hit;
    const bool Blocked = RangedAttackQuery::LineTraceSingle(GetWorld(),this,Hit,AimOrigin(),Target->GetActorLocation(),ECC_Visibility,
        FCollisionQueryParams(SCENE_QUERY_STAT(UnknownSight),false,this));
    return !Blocked || Hit.GetActor()==Target;
}

void AUnknownHumanoid::Pursue(AMonsterAIController& AI, APawn* Visible, FVector LastKnown)
{
    if (ServerTime()<CrowdYieldUntil && HandleCrowdTraffic(AI,CrowdYieldPoint,false)) return;
    const FVector Destination=Visible && !IsRanged()?Visible->GetNavAgentLocation():LastKnown;
    const float Distance = FVector::Dist2D(GetNavAgentLocation(),Destination);
    if (PursueBowRetreat(AI,Visible)) return;
    if (!Visible && PursueLastSighting(AI,LastKnown)) return;
    bSprintIntent = !Visible || Distance>AttackRange;
    const auto RangedTravel=[&]()
    {
        if (!IsRanged()) return;
        const bool Escape=UsesMobileGunCombat()?
            Position==EUnknownPosition::SeekCover && (Health<MaxHealth*.3f || Magazine==0):
            bRetreating && Distance<360.f && !SelfCast();
        // A clear lane allows a fighting withdrawal. An urgent cover dash or
        // an obstructed approach prioritizes movement over shooting.
        bSprintIntent=!Busy() && (Escape || !Visible || !bHasFiringLane || Distance>AttackRange);
    };
    RangedTravel();
    if (IsRanged() && Position!=EUnknownPosition::Open)
    {
        if (Position==EUnknownPosition::Sheltered || Position==EUnknownPosition::Peeking)
        {
            if (HandleCrowdTraffic(AI,GetNavAgentLocation(),false)) return;
            AI.StopMovement();
            bSprintIntent=false;
            return;
        }
        bSprintIntent=Position==EUnknownPosition::SeekCover || Distance<PreferredRange*.65f;
        RangedTravel();
        MoveRanged(AI,Position==EUnknownPosition::SeekCover?CoverPoint:FiringPoint,24.f,true);
        return;
    }
    if (IsRanged())
    {
        // Seeing the head above a low obstacle is not enough to stop at weapon range.
        const bool Clear=Visible && bHasFiringLane;
        // Hold a usable range between attacks instead of stepping forward and stopping
        // again on every burst or cast cooldown. Close-range retreat is planned separately.
        if (Clear && FVector::Dist(GetNavAgentLocation(),Destination)<=FMath::Max(PreferredRange,AttackRange*.91f))
        {
            if (HandleCrowdTraffic(AI,GetNavAgentLocation(),false)) return;
            AI.StopMovement();
            bSprintIntent=false;
            return;
        }
        MoveRanged(AI,Destination,Clear && FMath::Abs(GetNavAgentLocation().Z-Destination.Z)<50.f?PreferredRange:38.f,false);
        return;
    }
    if (bBowBlades)
    {
        // Defensive blades retain the archer's obstacle recovery when sight
        // is lost or a withdrawal falls back to a close counterattack.
        MoveRanged(AI,Destination,Visible?PreferredRange:38.f,false);
        return;
    }
    const bool ClosePursuit=Visible && !IsRanged() && Distance<AttackRange+RunSpeed*.5f;
    if (HandleCrowdTraffic(AI,Destination,true)) return;
    AI.NavigateTo(Destination,Visible?PreferredRange:45.f,ClosePursuit?.16f:.65f);
}

void AUnknownHumanoid::SetAction(EUnknownAction Action, float Duration)
{
    Motion.Action = Action;
    Motion.Duration = Duration;
    Motion.Started = ServerTime();
    Motion.Windup = 0.f;
    Motion.Preparation = Motion.Recovery = 0.f;
    Motion.Skill = NAME_None;
    ++Motion.Serial;
    bPendingContact = false;
    if (Action!=EUnknownAction::Swing) bSprintIntent=false;
    ForceNetUpdate();
    OnRep_Motion();
}

void AUnknownHumanoid::OnRep_Motion()
{
    if (Dead())
    {
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
}

bool AUnknownHumanoid::StartAttack(APawn* Target)
{
    if (!HasAuthority() || !CanAttack(Target)) return false;
    AttackTarget = Target;
    switch (bBowBlades?EUnknownRole::Melee:Loadout.Role)
    {
    case EUnknownRole::Melee:
        ShotsLeft=bBowBlades?2:1;
        SetAction(EUnknownAction::Swing,AttackSeconds);
        Motion.Windup=MeleeWindup();
        Stamina = FMath::Max(0.f,Stamina-StaminaCost);
        ResourceDelay = Sheet->StaminaSettings().RecoveryDelay;
        ContactAt = Motion.Started+Motion.Windup;
        break;
    case EUnknownRole::Gun:
        if (WantsReload()) { SetAction(EUnknownAction::Reload,Magazine==0?ReloadSeconds:TacticalReloadSeconds); return true; }
        ShotsLeft = FMath::Min(BurstSize,Magazine);
        SetAction(EUnknownAction::Fire,AimSeconds+AttackSeconds*ShotsLeft);
        Motion.Windup=AimSeconds;
        ContactAt = Motion.Started+Motion.Windup;
        break;
    case EUnknownRole::Magic:
        StartMagicAttack();
        break;
    case EUnknownRole::Bow:
        return StartBowAttack(Target);
    }
    if (Motion.Action==EUnknownAction::Swing)
        MulticastMeleeSound(false,AimOrigin());
    bPendingContact = true;
    return true;
}

float AUnknownHumanoid::RollDamage(APawn* Victim, float Damage, float Roll, bool Weak, float Bonus) const
{
    const float Resistance = CombatFormulaRuntime::MonsterCriticalResistance(Victim);
    const bool Critical = Weak || Roll<CoreCombatFormula::CriticalChance(CriticalChance,Resistance);
    if (Weak) Damage *= 1.f+WeakpointPercent/100.f;
    return Critical ? CoreCombatFormula::CriticalDamage(Damage,Bonus) : Damage;
}

float AUnknownHumanoid::HitWithRound(const FHitResult& Hit, float Damage, FVector Direction, float Roll)
{
    auto* Victim = Cast<APawn>(Hit.GetActor());
    if (!HasAuthority() || !UnknownSpell::IsTarget(this,Victim)) return 0;
    return UGameplayStatics::ApplyPointDamage(Victim,RollDamage(Victim,Damage,Roll,ColdSteelSkills::IsCriticalHit(Hit),CriticalBonus),
        Direction,Hit,GetController(),this,UEnemyRangedDamage::StaticClass());
}

void AUnknownHumanoid::ReleaseAttack()
{
    bPendingContact = false;
    const auto StopBurst=[&]()
    {
        if (Motion.Action!=EUnknownAction::Fire) return;
        ShotsLeft=0;
        // Do not wait out an entire burst after its lane/target disappears.
        // Tick performs the normal recovery and reload handoff on this frame.
        Motion.Duration=FMath::Max(0.f,ServerTime()-Motion.Started);
        ForceNetUpdate();
    };
    auto* Target = AttackTarget.Get();
    if (!UnknownSpell::IsTarget(this,Target) || Controlled()) { StopBurst(); CancelRangedAction(); return; }
    const FVector Start = AimOrigin();
    const FVector Aim = Target->GetActorLocation()+FVector(0,0,14);
    const bool Swing=Motion.Action==EUnknownAction::Swing;
    FRotator SwingAim = GetActorRotation();
    SwingAim.Pitch = MeleeDirection(*Target).Rotation().Pitch;
    const FVector Direction = Swing ? SwingAim.Vector() : (Aim-Start).GetSafeNormal();
    if (Swing)
    {
        if (bBowBlades && --ShotsLeft>0) { bPendingContact=true; ContactAt=Motion.Started+MeleeSecondContact; }
        const FVector Tip = Start+Direction*AttackRange;
        FHitResult Hit;
        if(!RangedAttackQuery::TraceToPlayer(GetWorld(),this,Hit,Start,Tip,MeleeSweepRadius,
            FCollisionQueryParams(SCENE_QUERY_STAT(UnknownSwing),false,this)))return;
        if(auto* Victim=Cast<APawn>(Hit.GetActor()); UnknownSpell::IsTarget(this,Victim))
        {
            MulticastMeleeSound(true,Hit.ImpactPoint);
            const float Damage = RollDamage(Victim,WeaponDamage.Total(),FMath::FRand()*100.f,ColdSteelSkills::IsCriticalHit(Hit),CriticalBonus);
            UGameplayStatics::ApplyPointDamage(Victim,Damage,Direction,Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
        }
    }
    else if (Motion.Action==EUnknownAction::Fire)
    {
        const auto* AI=Cast<AMonsterAIController>(GetController());
        if (Magazine<=0 || (AI && (!AI->bDecisionEnabled || TacticalTarget.Get()!=Target)) || !FacingTarget(*Target) ||
            FVector::DistSquared(GetActorLocation(),Target->GetActorLocation())>FMath::Square(AttackRange) ||
            !HasFiringLane(Start,*Target,Target->GetActorLocation())) { StopBurst(); return; }
        const bool OnTarget=FMath::RandHelper(100)<ShotAccuracyPercent;
        const FVector ShotDirection=OnTarget?Direction:MissDirection(Start,Aim,Target->GetSimpleCollisionRadius(),PelletCone);
        const float CriticalRoll=FMath::FRand()*100.f;
        const float FlightSpeed=UFPSBallisticsComponent::ScaledBulletSpeed(BulletSpeed);
        const float RangeCM=EffectiveRange*3.f;
        APawn* MissedTarget=OnTarget?nullptr:Target;
        const FVector VisualMuzzle=GunTracers?TracerMuzzle(Start,GunMuzzle(Start)):Start;
        for (int32 N=0; N<Pellets; ++N)
        {
            // One central pellet and the normal spread around it share the shell's accuracy roll.
            const FVector PelletDirection=N==0?ShotDirection:FMath::VRandCone(ShotDirection,PelletCone);
            Ballistics->LaunchHostile(Start,PelletDirection,FlightSpeed,RangeCM,
                EffectiveRange,WeaponDamage.Total()/Pellets,CriticalRoll,MissedTarget,N==0?GunTracers.Get():nullptr,VisualMuzzle);
        }
        MulticastShot(Start,ShotDirection,FlightSpeed,RangeCM,MissedTarget);
        --Magazine;
        if (--ShotsLeft>0) { bPendingContact=true; ContactAt+=AttackSeconds; }
    }
    else if (Motion.Action==EUnknownAction::Cast || Motion.Action==EUnknownAction::DrawBow)
    {
        const auto* AI=Cast<AMonsterAIController>(GetController());
        if (AI && (!AI->bDecisionEnabled || TacticalTarget.Get()!=Target)) { CancelRangedAction(); return; }
        if (Motion.Action==EUnknownAction::Cast)
        {
            if (SelfCast() || FacingTarget(*Target)) ReleaseMagic(Target,Aim);
            else CancelRangedAction();
        }
        else ReleaseBowAttack(Target);
    }
}

void AUnknownHumanoid::FireballImpact(const FVector& Center, const FFireballCast& CastData, const FHitResult* Direct)
{
    if (!HasAuthority() || Dead()) return;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(UnknownBlast),false,this);
    TArray<APawn*,TInlineAllocator<8>> Victims;
    for (auto It=GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* Player=It->Get()) if (auto* Pawn=Player->GetPawn().Get())
        {
            Query.AddIgnoredActor(Pawn);
            Victims.Add(Pawn);
        }
    for (APawn* Victim : Victims)
    {
        const bool DirectHit = Direct && Direct->GetActor()==Victim;
        float Distance = 0.f;
        if (!DirectHit && !MagicOcclusion::BlastExposure(GetWorld(),this,Victim,Center,CastData.Radius,Query,Distance)) continue;
        const bool Weak = DirectHit && ColdSteelSkills::IsCriticalHit(*Direct);
        const float Damage=CastData.Damage*(1.f-.5f*(DirectHit?0.f:Distance/CastData.Radius));
        UnknownSpell::Hit(this,Victim,Damage,CastData.CriticalChance,CastData.CriticalDamageBonus,
            CastData.MagicDamageBonus,CastData.MagicPenetration,UWitchMagicDamage::StaticClass(),Weak);
    }
}

void AUnknownHumanoid::Interrupt(float Duration)
{
    if (Dead()) return;
    if(auto* Fire=FindComponentByClass<UFPSFireMagicComponent>())Fire->FinishDragonBreathForRemoval();
    SetAction(EUnknownAction::Stagger,Duration);
    Combat->BeginReaction(Duration);
}

void AUnknownHumanoid::UpdateResources(float Delta)
{
    Health = FMath::Min(MaxHealth,Health+HealthRegen*Delta);
    const bool Run = bSprintIntent && (!Busy() || CanPursueDuringSwing(AttackTarget.Get())) && !bExhausted && !Status->BlocksMovement();
    const auto& Tuning = Sheet->StaminaSettings();
    const bool Drawing=Archery && Motion.Action==EUnknownAction::DrawBow && bPendingContact;
    if (Drawing)
    {
        const double Through=FMath::Min(double(ServerTime()),ContactAt);
        const float Held=FMath::Max(0.,Through-Archery->DrawAccountedAt);
        Archery->DrawAccountedAt=Through;
        Stamina=FMath::Max(0.f,Stamina-Held*float(Archery->Stats.ChargeStamina));
        Archery->Mana=FMath::Max(0.f,Archery->Mana-Held*Archery->HoldMana);
        ResourceDelay=Tuning.RecoveryDelay;
    }
    else if (Run && GetVelocity().SizeSquared2D()>100.f)
    {
        Stamina = FMath::Max(0.f,Stamina-Delta*SprintDrain);
        ResourceDelay = Tuning.RecoveryDelay;
        bExhausted = Stamina<=0.f;
    }
    else
    {
        Stamina = FMath::Min(MaxStamina,Stamina+FMath::Max(0.f,Delta-ResourceDelay)*RecoveryRate);
        ResourceDelay = FMath::Max(0.f,ResourceDelay-Delta);
        if (Stamina>=MaxStamina*Tuning.SprintRestartRatio) bExhausted=false;
    }
    if (Archery && (!Drawing || Archery->HoldMana==0.f))
        Archery->Mana=FMath::Min(Archery->MaxMana,Archery->Mana+Delta*Archery->ManaRegen);
    float Speed=Run?RunSpeed:WalkSpeed;
    if (Motion.Action==EUnknownAction::DrawBow ||
        (Motion.Action==EUnknownAction::Cast && Motion.Skill==TEXT("dragonBreath"))) Speed=AimWalkSpeed;
    if (Motion.Action==EUnknownAction::Cast && Motion.Skill==TEXT("thunderLance") &&
        ServerTime()<Motion.Started+Motion.Windup) Speed=0.f;
    Speed*=Status->MovementMultiplier();
    if(ServerTime()<CrowdSpeedUntil)Speed=FMath::Min(Speed,CrowdSpeedLimit);
    GetCharacterMovement()->MaxWalkSpeed = Status->BlocksMovement()?0.f:Speed;
}

void AUnknownHumanoid::Tick(float Delta)
{
    Super::Tick(Delta);
    if (HasAuthority() && Sheet && !Dead())
    {
        // The replicated presentation uses the same body point as ReleaseAttack.
        // Do not follow a hidden target's live position after sight is lost.
        if(bGunTracking && bTacticalTargetVisible && TacticalTarget.IsValid())
            GunAimPoint=TacticalTarget->GetActorLocation()+FVector(0,0,14);
        UpdateResources(Delta);
        const float Now = ServerTime();
        const uint16 Serial = Motion.Serial;
        if (bPendingContact && Now>=ContactAt) ReleaseAttack();
        if (Serial==Motion.Serial && Busy() && Now>=Motion.Started+Motion.Duration && !bPendingContact)
        {
            if (Motion.Action==EUnknownAction::Reload)
                Magazine=Capacity;
            if (Motion.Action==EUnknownAction::Fire) NextAttack=Now+FMath::Max3(AttackSeconds,AimSeconds,BurstRecovery);
            if (Motion.Action==EUnknownAction::Stagger && (Combat->StunSecondsRemaining()>0.f || Status->BlocksMovement())) return;
            if (bHasCover && Position==EUnknownPosition::Peeking &&
                (UnderPressure()||WantsReload()||(UsesMobileGunCombat()&&Now>=PositionUntil)) &&
                (Motion.Action==EUnknownAction::Fire || Motion.Action==EUnknownAction::Cast || Motion.Action==EUnknownAction::DrawBow))
            { Position=EUnknownPosition::SeekCover; }
            const bool EndReaction = Motion.Action==EUnknownAction::Stagger;
            SetAction(EUnknownAction::Ready);
            if (EndReaction) Combat->FinishReaction();
        }
        // An empty gun can reload even if the last shot killed the only target.
        if (Loadout.Role==EUnknownRole::Gun && Magazine==0 && Capacity>0 && !Busy() && !Controlled())
            SetAction(EUnknownAction::Reload,ReloadSeconds);
    }
    UpdateGunRecoil();
}

float AUnknownHumanoid::TakeDamage(float Amount, const FDamageEvent& Event, AController* InstigatorController, AActor* Causer)
{
    if (!HasAuthority() || Dead() || Amount<=0.f) return 0;
    const float Damage = UDevelopmentTuningSubsystem::ShouldOneHitKill(this,InstigatorController,Causer) ? Health :
        CombatFormulaRuntime::MitigateMonster(this,Amount,Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr,Causer);
    const float Applied = FMath::Clamp(Damage,0.f,Health);
    if (Applied<=0.f) return 0;
    LastIncomingHit = ServerTime();
    if(auto* Armor=FindComponentByClass<UFPSIceArmorComponent>())
        Armor->ObserveAcceptedDamage(InstigatorController&&InstigatorController->GetPawn()?
            InstigatorController->GetPawn().Get():Causer,
            Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr,Applied);
    Health -= Applied;
    const bool Killed = Health<=0.f;
    if (Killed)
    {
        SetAction(EUnknownAction::Dead);
        if(auto* Fire=FindComponentByClass<UFPSFireMagicComponent>())Fire->FinishFireMagicForRemoval();
        if(auto* Blizzard=FindComponentByClass<UFPSBlizzardComponent>())Blizzard->FinishZonesForRemoval();
        if(auto* Electric=FindComponentByClass<UFPSElectricMagicComponent>())Electric->ClearEffects();
        if(auto* Armor=FindComponentByClass<UFPSIceArmorComponent>())Armor->FinishForRemoval();
        if(auto* Haste=FindComponentByClass<UFPSLightningHasteComponent>())Haste->FinishForRemoval();
        GetCharacterMovement()->DisableMovement();
        GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if (auto* AI=Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
        SetLifeSpan(12.f);
    }
    Super::TakeDamage(Applied,Event,InstigatorController,Causer);
    if (Killed)
    {
        ColdSteelSkills::NotifyKillByOwner(GetGameInstance(),InstigatorController,this);
        ColdSteelSkills::AwardKillByOwner(GetGameInstance(),InstigatorController,this,Loadout.Level*10);
    }
    else Combat->ReceiveHit(Applied,InstigatorController?InstigatorController->GetPawn().Get():Cast<APawn>(Causer),MonsterToughness::FormOf(Event.DamageTypeClass));
    return Applied;
}
