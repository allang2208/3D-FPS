#include "BoundCongregate.h"
#include "BoundCongregateAnimInstance.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/IceWallCombat.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

ABoundCongregate::ABoundCongregate(const FObjectInitializer& Initializer)
    :Super(Initializer.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick=true;bReplicates=true;
    Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    CorpseRagdoll=CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    Voice=CreateDefaultSubobject<UAudioComponent>(TEXT("BodyVoice"));Voice->SetupAttachment(GetMesh());Voice->bAutoActivate=false;
    Voice->bOverrideAttenuation=true;Voice->AttenuationOverrides.bAttenuate=true;
    Voice->AttenuationOverrides.bSpatialize=true;Voice->AttenuationOverrides.FalloffDistance=1400.f;
    ActionVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("ActionVoice"));ActionVoice->SetupAttachment(GetMesh(),TEXT("maw"));ActionVoice->bAutoActivate=false;
    ActionVoice->bOverrideAttenuation=true;ActionVoice->AttenuationOverrides.bAttenuate=true;
    ActionVoice->AttenuationOverrides.bSpatialize=true;ActionVoice->AttenuationOverrides.FalloffDistance=1700.f;
    GetCapsuleComponent()->InitCapsuleSize(225.f,225.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    GetMesh()->SetRelativeLocation(FVector(0,0,-225));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->SetAnimInstanceClass(UBoundCongregateAnimInstance::StaticClass());
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    auto* Move=CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement());
    Move->ConfigureWideBodyStairs(225,450);Move->MaxWalkSpeed=WalkSpeed;
    Move->MaxAcceleration=150;Move->BrakingDecelerationWalking=240;Move->RotationRate=FRotator(0,50,0);
    Move->bOrientRotationToMovement=true;Move->bCanWalkOffLedges=false;
    bUseControllerRotationYaw=false;BaseEyeHeight=-80;
    AIControllerClass=AMonsterAIController::StaticClass();AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("BoundCongregate"));
}
void ABoundCongregate::ApplyVisual()
{
    if(!VisualMesh)return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    GetMesh()->SetRelativeRotation(FRotator(0,MeshYaw,0));
    const auto B=VisualMesh->GetBounds();
    GetMesh()->SetRelativeLocation(FVector(0,0,-GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()-(B.Origin.Z-B.BoxExtent.Z)));
    GetMesh()->SetAnimInstanceClass(UBoundCongregateAnimInstance::StaticClass());
}
void ABoundCongregate::OnConstruction(const FTransform& T)
{
    Super::OnConstruction(T);ApplyVisual();
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225,450);
}
void ABoundCongregate::BeginPlay()
{
    Super::BeginPlay();ApplyVisual();Home=GetActorLocation();
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225,450);
    GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;
    if(HasAuthority()){MaxHealth*=float(MonsterCoreStats::HealthMultiplier());Health=MaxHealth;NetState.StartedAt=Clock();}
    Combat->HitClip=HitClip;GetMesh()->AddTickPrerequisiteActor(this);GetMesh()->AddTickPrerequisiteComponent(Combat);
    if(GetNetMode()!=NM_DedicatedServer&&BreathSound){Voice->SetSound(BreathSound);Voice->Play();}
    PresentState();if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
double ABoundCongregate::Clock() const
{
    const auto* GS=GetWorld()?GetWorld()->GetGameState():nullptr;
    return GS?GS->GetServerWorldTimeSeconds():GetWorld()?GetWorld()->GetTimeSeconds():0.;
}
double ABoundCongregate::StateElapsed() const {return FMath::Max(0.,Clock()-NetState.StartedAt);}
void ABoundCongregate::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(ABoundCongregate,NetState);
    DOREPLIFETIME(ABoundCongregate,Health);DOREPLIFETIME(ABoundCongregate,MaxHealth);
    DOREPLIFETIME(ABoundCongregate,TentacleHealth);
}
void ABoundCongregate::GetActorEyesViewPoint(FVector& P,FRotator& R) const
{P=GetMesh()->GetSocketLocation(TEXT("scent_01"));R=GetActorRotation();}
void ABoundCongregate::OnRep_State(){PresentState();}
void ABoundCongregate::SetState(EBoundCongregateState State)
{
    NetState.State=State;NetState.StartedAt=Clock();
    if(Busy())GetCharacterMovement()->StopMovementImmediately();
    PresentState();ForceNetUpdate();
}
void ABoundCongregate::PresentState()
{
    UpdateTentacleHitShapeState();
    // Enclose a deployed distal organ even when the body's physics bounds are
    // off screen. Keep the normal bounds outside tentacle attacks; never enlarge
    // the gameplay capsule or the imported bounds used for floor alignment.
    const float Reach=TentacleActive()?FMath::Min(TentacleRange,float(FVector::Distance(GetActorLocation(),NetState.TentacleAim))):0.f;
    GetMesh()->SetBoundsScale(VisualMesh?1.f+Reach/FMath::Max(100.f,VisualMesh->GetBounds().SphereRadius):1.f);
    NextFlurrySound=0;ActionVoice->SetVolumeMultiplier(1.f);
    if(Dead())
    {
        Voice->Stop();GetCharacterMovement()->DisableMovement();GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if(DeathSound&&GetNetMode()!=NM_DedicatedServer){ActionVoice->SetSound(DeathSound);ActionVoice->Play();}
        if(CorpseRagdoll->TryStartSoftDeath(GetMesh())){SetActorTickEnabled(false);return;}
    }
    GetCharacterMovement()->bOrientRotationToMovement=!Busy();
    // Locomotion selection belongs to the velocity-driven animation instance.
    // A replicated Crawl/Idle notification must not reset its current foot phase.
    if(auto* Anim=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance());Anim&&TentacleActive()&&!Controlled()&&NetState.State!=EBoundCongregateState::Bite)
    {
        if(NetState.State==EBoundCongregateState::TentacleWindup||Anim->ActiveClip!=IdleClip||!Anim->bLooping)
            Anim->TransitionTo(IdleClip,true,false,.2f);
    }
    else if(Anim&&Busy())
    {
        UAnimSequence* Clip=Dead()?DeathClip.Get():Controlled()?HitClip.Get():NetState.State==EBoundCongregateState::Flurry?FlurryClip.Get():BiteClip.Get();
        Anim->TransitionTo(Clip,false,true,.16f);Anim->SetCombatTime(float(StateElapsed()));
    }
    if(NetState.State==EBoundCongregateState::Bite&&BiteSound&&GetNetMode()!=NM_DedicatedServer)
        {ActionVoice->SetSound(BiteSound);ActionVoice->Play();}
}
void ABoundCongregate::Sample(float T)
{if(auto* Anim=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))Anim->SetCombatTime(T);}
void ABoundCongregate::SetLocomotion(bool Moving,bool Returning)
{
    if(Busy()||!HasAuthority())return;
    const auto S=Moving?EBoundCongregateState::Crawl:EBoundCongregateState::Idle;
    if(NetState.State!=S)SetState(S);
}
bool ABoundCongregate::HasSight(APawn* Victim) const
{
    if(!IsValid(Victim))return false;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(CongregateSight),false,this);Q.AddIgnoredActor(Victim);FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit,GetMesh()->GetSocketLocation(TEXT("maw")),Victim->GetActorLocation(),ECC_Visibility,Q);
}
bool ABoundCongregate::CanAttack(APawn* Victim) const
{
    if(!IsValid(Victim)||Busy()||Clock()<NextAttack||!GetCharacterMovement()->IsMovingOnGround())return false;
    if(const auto* H=Victim->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return false;
    return CanBite(Victim)||CanFlurry(Victim)||CanTentacle(Victim);
}
bool ABoundCongregate::StartAttack(APawn* Victim)
{
    if(!HasAuthority()||!CanAttack(Victim))return false;
    // Rotate eligible close attacks so the short whip cooldown cannot starve
    // the bite/flurry. Outside their reach this falls back to the same whip.
    for(uint8 Offset=0;Offset<3;++Offset)
    {
        const uint8 Choice=(AttackChoice+Offset)%3;
        if(Choice==2)
        {
            if(BeginTentacle(Victim)){AttackChoice=0;return true;}
            continue;
        }
        if(Choice==0?!CanBite(Victim):!CanFlurry(Victim))continue;
        Target=Victim;AttackYaw=GetActorRotation().Yaw;bContactConsumed=false;NextFlurryHit=0;
        NetState.ReleasedWrap=0.f;
        if(Choice==0)NextBite=Clock()+BiteCooldown;else NextFlurry=Clock()+FlurryCooldown;
        AttackChoice=(Choice+1)%3;
        SetState(Choice==0?EBoundCongregateState::Bite:EBoundCongregateState::Flurry);
        if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
        return true;
    }
    return false;
}
void ABoundCongregate::Contact()
{
    APawn* Victim=Target.Get();if(!IsValid(Victim))return;
    // A miss leaves the remaining jaw-closing window available. A blocked or
    // valid contact consumes the bite even if armour/parry prevents damage.
    if(IceWallCombat::ApplyMelee(this,Victim,BiteTriggerRange,BiteDamage))
    {bContactConsumed=true;return;}
    const FVector From=GetMesh()->GetSocketLocation(TEXT("maw"));const FVector D=Victim->GetActorLocation()-From;
    float R=0,H=0;Victim->GetSimpleCollisionCylinder(R,H);
    if(D.Size2D()-R>BiteReach||FMath::Abs(D.Z)>H+40||FVector::DotProduct(D.GetSafeNormal2D(),GetActorForwardVector())<.35||!HasSight(Victim))return;
    bContactConsumed=true;
    FHitResult Hit;Hit.Location=Hit.ImpactPoint=From+D.GetSafeNormal()*FMath::Max(0.f,float(D.Size())-R);
    Hit.ImpactNormal=-GetActorForwardVector();
    const float Applied=UGameplayStatics::ApplyPointDamage(Victim,BiteDamage,GetActorForwardVector(),Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
    if(Applied>0.f)
    {
        auto* Status=UCombatStatusFormula::GetOrAdd(Victim);
        Status->AddBleeding(this,3);Status->AddCripple(5.f);
    }
}
void ABoundCongregate::Tick(float Dt)
{
    Super::Tick(Dt);const float T=float(StateElapsed());
    if(Controlled())
    {if(HasAuthority()&&T>=ReactionSeconds)Combat->FinishReaction();}
    else if(NetState.State==EBoundCongregateState::Bite||NetState.State==EBoundCongregateState::Flurry)TickMelee(Dt);
    else if(TentacleActive()&&!Controlled())
    {
        if(HasAuthority())TickTentacle(Dt);
    }
    else if(Dead())
    {
        const float Length=DeathClip?DeathClip->GetPlayLength():2.2f;Sample(FMath::Min(T,Length));
        if(T>=Length){CorpseRagdoll->FreezeAnimatedPose(GetMesh());SetActorTickEnabled(false);}
    }
    else if(HasAuthority()&&Target.IsValid()&&GetVelocity().SizeSquared2D()<9&&
        FVector::DistSquared2D(Target->GetActorLocation(),GetActorLocation())<FMath::Square(FMath::Max3(BiteTriggerRange,FlurryRange,TentacleRange)+50))
    {
        FRotator R=GetActorRotation();R.Yaw=FMath::FixedTurn(R.Yaw,(Target->GetActorLocation()-GetActorLocation()).Rotation().Yaw,GetCharacterMovement()->RotationRate.Yaw*Dt);SetActorRotation(R);
    }
    // A bounded distance/visibility budget; blend back to skin before suspending.
    if(GetNetMode()==NM_DedicatedServer){if(!bClothSuspended){GetMesh()->SuspendClothingSimulation();bClothSuspended=true;}return;}
    ClothBudgetElapsed+=Dt;
    if(ClothBudgetElapsed>=.5f&&!Dead())
    {
        ClothBudgetElapsed=0;const APawn* Player=UGameplayStatics::GetPlayerPawn(this,0);
        const float Distance2=Player?FVector::DistSquared(Player->GetActorLocation(),GetActorLocation()):MAX_flt;
        bWantsCloth=Distance2<FMath::Square(bClothSuspended?2200.f:2700.f)&&GetMesh()->WasRecentlyRendered(1.0f);
        if(bWantsCloth&&bClothSuspended){GetMesh()->ResumeClothingSimulation();GetMesh()->ForceClothNextUpdateTeleportAndReset();bClothSuspended=false;}
    }
    GetMesh()->ClothBlendWeight=FMath::FInterpConstantTo(GetMesh()->ClothBlendWeight,bWantsCloth?1.f:0.f,Dt,1.5f);
    if(!bWantsCloth&&GetMesh()->ClothBlendWeight<.02f&&!bClothSuspended){GetMesh()->SuspendClothingSimulation();bClothSuspended=true;}
}
void ABoundCongregate::InterruptAttack(float Seconds)
{
    if(!HasAuthority()||Dead())return;bContactConsumed=true;ReactionSeconds=FMath::Max(.1f,Seconds);
    // A body stagger cannot release a living restraint. Resume pulling after
    // the reaction; killing the monster still clears capture normally.
    if(!NetState.CapturedTarget)EndTentacle(false);
    SetState(EBoundCongregateState::Stagger);Combat->BeginReaction(ReactionSeconds);
}
void ABoundCongregate::StartHitPresentation()
{if(!Dead())if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->TransitionTo(HitClip,false,true,.08f);}
void ABoundCongregate::SetHitPresentationTime(float Elapsed,float Remaining)
{if(!Dead()&&HitClip)Sample(FMath::Clamp(Elapsed<.15f?Elapsed:Remaining>.35f?.15f:HitClip->GetPlayLength()-Remaining,0.f,HitClip->GetPlayLength()));}
void ABoundCongregate::FinishHitReaction(){if(HasAuthority()&&Controlled())SetState(NetState.CapturedTarget?EBoundCongregateState::TentacleDrag:EBoundCongregateState::Idle);}
float ABoundCongregate::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||Dead()||Damage<=0)return 0;
    // Gun contacts on the deployed organ are handled by ApplyTentacleShot.
    // A spell or ordinary melee query hitting its capsule cannot redirect that
    // point hit into the main body's health or break the restraint indirectly.
    if(Event.IsOfType(FPointDamageEvent::ClassID)&&IsTentaclePart(static_cast<const FPointDamageEvent&>(Event).HitInfo))return 0.f;
    const float Reduced=CombatFormulaRuntime::MitigateMonster(this,Damage,Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr,Causer);
    const float Applied=UDevelopmentTuningSubsystem::ShouldOneHitKill(this,EventInstigator,Causer)?Health:FMath::Min(Health,Reduced);
    if(Applied<=0)return 0;Health-=Applied;Super::TakeDamage(Applied,Event,EventInstigator,Causer);
    if(Health<=0)
    {
        bContactConsumed=true;
        // Capture the displayed flurry/bite/deployed-tentacle pose before
        // releasing the victim or resetting the procedural attack drivers.
        CorpseRagdoll->PrepareDeath(GetMesh());CorpseRagdoll->TryStartSoftDeath(GetMesh());
        EndTentacle(false);Target.Reset();SetState(EBoundCongregateState::Dead);SetLifeSpan(CorpseSeconds);
        if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
        ColdSteelSkills::NotifyKillByOwner(GetGameInstance(),EventInstigator,this);
        if(auto* PC=Cast<APlayerController>(EventInstigator);PC&&PC->IsLocalController()&&GetGameInstance())
            GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);
    }
    else Combat->ReceiveHit(Applied,EventInstigator?EventInstigator->GetPawn().Get():Cast<APawn>(Causer),MonsterToughness::FormOf(Event.DamageTypeClass));
    return Applied;
}
