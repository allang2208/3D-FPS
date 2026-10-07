#include "M10Mawcrawler.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterCharacterMovementComponent.h"
#include "M10MovementComponent.h"
#include "M10AnimInstance.h"
#include "MonsterAIController.h"
#include "FatZombieAnimInstance.h"
#include "FPSCombatHealthComponent.h"
#include "MonsterCombatTuning.h"
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
#include "Components/StaticMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundAttenuation.h"

AM10Mawcrawler::AM10Mawcrawler(const FObjectInitializer& Initializer)
    : Super(Initializer.SetDefaultSubobjectClass<UM10MovementComponent>(CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick=true;
    Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    CorpseRagdoll=CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    CorpseRagdoll->Rig=EMonsterCorpseRig::Mawcrawler;
    HowlVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("HowlVoice"));
    HowlVoice->SetupAttachment(GetMesh(),TEXT("mouth_socket"));HowlVoice->bAutoActivate=false;
    HowlVoice->bOverrideAttenuation=true;HowlVoice->AttenuationOverrides.bAttenuate=true;
    HowlVoice->AttenuationOverrides.bSpatialize=true;HowlVoice->AttenuationOverrides.FalloffDistance=1800.f;
    BodyVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("BodyVoice"));
    BodyVoice->SetupAttachment(GetMesh());BodyVoice->bAutoActivate=false;
    BodyVoice->bOverrideAttenuation=true;BodyVoice->AttenuationOverrides.bAttenuate=true;
    BodyVoice->AttenuationOverrides.bSpatialize=true;BodyVoice->AttenuationOverrides.FalloffDistance=1100.f;
    CrawlVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("CrawlVoice"));
    CrawlVoice->SetupAttachment(GetMesh());CrawlVoice->bAutoActivate=false;
    CrawlVoice->bOverrideAttenuation=true;CrawlVoice->AttenuationOverrides.bAttenuate=true;
    CrawlVoice->AttenuationOverrides.bSpatialize=true;CrawlVoice->AttenuationOverrides.FalloffDistance=1400.f;
    GasVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("GasVoice"));
    GasVoice->SetupAttachment(GetMesh(),TEXT("rump"));GasVoice->bAutoActivate=false;
    GasVoice->bOverrideAttenuation=true;GasVoice->AttenuationOverrides.bAttenuate=true;
    GasVoice->AttenuationOverrides.bSpatialize=true;GasVoice->AttenuationOverrides.FalloffDistance=1600.f;
    for(int32 I=0;I<3;++I)
    {
        auto* Wave=CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("HowlWave%d"),I));
        Wave->SetupAttachment(GetRootComponent());Wave->SetAbsolute(true,true,true);
        Wave->SetCollisionEnabled(ECollisionEnabled::NoCollision);Wave->SetGenerateOverlapEvents(false);
        Wave->SetCanEverAffectNavigation(false);Wave->SetCastShadow(false);Wave->SetVisibility(false);
        HowlWaves.Add(Wave);
    }
    GetCapsuleComponent()->InitCapsuleSize(225.f,225.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    GetMesh()->SetRelativeLocation(FVector(0,0,-225.f));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->SetAnimInstanceClass(UM10AnimInstance::StaticClass());
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    auto* Move=GetCharacterMovement();Move->MaxWalkSpeed=WalkSpeed;
    Move->MaxAcceleration=480.f;Move->BrakingDecelerationWalking=720.f;
    Move->RotationRate=FRotator(0,150.f,0);Move->bOrientRotationToMovement=true;
    Move->bCanWalkOffLedges=false;Move->bRunPhysicsWithNoController=true;
    CastChecked<UMonsterCharacterMovementComponent>(Move)->ConfigureWideBodyStairs(225.f,450.f);
    bUseControllerRotationYaw=false;BaseEyeHeight=-180.f;
    AIControllerClass=AMonsterAIController::StaticClass();AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("M10Mawcrawler"));
}
void AM10Mawcrawler::ApplyVisual()
{
    if(!VisualMesh)return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    const auto Bounds=VisualMesh->GetBounds();
    GetMesh()->SetRelativeLocation(FVector(0,0,-GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()-(Bounds.Origin.Z-Bounds.BoxExtent.Z)));
}
void AM10Mawcrawler::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225.f,450.f);
    ApplyVisual();
}
void AM10Mawcrawler::BeginPlay()
{
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225.f,450.f);
    Super::BeginPlay();ApplyVisual();Home=GetActorLocation();
    if(HasAuthority()){MaxHealth*=float(MonsterCoreStats::HealthMultiplier());Health=MaxHealth;}
    GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;
    GetMesh()->AddTickPrerequisiteActor(this);GetMesh()->AddTickPrerequisiteComponent(Combat);
    if(BodyVoice&&IdleSound)BodyVoice->SetSound(IdleSound);
    if(CrawlVoice&&CrawlSound)CrawlVoice->SetSound(CrawlSound);
    if(GasVoice&&GasSound)GasVoice->SetSound(GasSound);
    PrepareHowlPresentation();PrepareRearGas();PresentState();
    if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void AM10Mawcrawler::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AM10Mawcrawler,State);DOREPLIFETIME(AM10Mawcrawler,Health);
    DOREPLIFETIME(AM10Mawcrawler,HowlStartedAt);
    DOREPLIFETIME(AM10Mawcrawler,RearGasStartedAt);
    DOREPLIFETIME(AM10Mawcrawler,ThreatSerial);
}
void AM10Mawcrawler::OnRep_State(){StateSeconds=0.f;PresentState();}
void AM10Mawcrawler::Play(UAnimSequence* Clip,bool Loop,bool ExternalClock,float Blend)
{
    if(auto* Anim=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))Anim->TransitionTo(Clip,Loop,ExternalClock,Blend);
}
void AM10Mawcrawler::Sample(float Time)
{
    if(auto* Anim=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))Anim->SetCombatTime(Time);
}
void AM10Mawcrawler::PresentState()
{
    StopHowlPresentation();
    if(State!=EM10State::RearGas)StopRearGas();
    const bool Moving=State==EM10State::Crawl||State==EM10State::Returning;
    GetCharacterMovement()->bOrientRotationToMovement=Moving;
    UpdateLoopAudio();
    if((State==EM10State::Dying||State==EM10State::Corpse)&&CorpseRagdoll->TryStartSoftDeath(GetMesh()))return;
    if(State==EM10State::Corpse)return;
    // State-driven one-shots play on every client from the replicated state.
    if(GetNetMode()!=NM_DedicatedServer)
    {
        if(State==EM10State::Bite&&BiteSound)
            UGameplayStatics::PlaySoundAtLocation(this,BiteSound,Mouth(),1.f,1.f,0.f,OneShotAttenuation(1600.f));
        else if(State==EM10State::Stagger&&HitSound)
            UGameplayStatics::PlaySoundAtLocation(this,HitSound,GetMesh()->GetSocketLocation(TEXT("body_front")),.9f,1.f,0.f,OneShotAttenuation(1200.f));
        else if(State==EM10State::Dying&&DeathSound)
            UGameplayStatics::PlaySoundAtLocation(this,DeathSound,GetMesh()->GetSocketLocation(TEXT("body_front")),1.f,1.f,0.f,OneShotAttenuation(1800.f));
    }
    if(State==EM10State::Stagger){StartHitPresentation();return;}
    Play(Moving?MoveClip:State==EM10State::Bite?BiteClip:State==EM10State::Howl?HowlClip:State==EM10State::RearGas?RearGasClip:State==EM10State::Dying?DeathClip:IdleClip,
        Moving||State==EM10State::Idle,State==EM10State::Bite||State==EM10State::Dying||State==EM10State::Howl||State==EM10State::RearGas);
    if(State==EM10State::Dying)
    {
        GetCharacterMovement()->DisableMovement();GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
}
void AM10Mawcrawler::SetState(EM10State NewState)
{
    State=NewState;StateSeconds=0.f;
    if(NewState!=EM10State::Crawl&&NewState!=EM10State::Returning&&HasAuthority())GetCharacterMovement()->StopMovementImmediately();
    PresentState();ForceNetUpdate();
}
void AM10Mawcrawler::SetLocomotion(bool Moving,bool Returning)
{
    if(Busy())return;
    const auto Next=Moving?(Returning?EM10State::Returning:EM10State::Crawl):EM10State::Idle;
    if(State!=Next)SetState(Next);
}
FVector AM10Mawcrawler::Mouth() const{return GetMesh()->GetSocketLocation(TEXT("mouth_socket"));}
bool AM10Mawcrawler::CanSee(const AActor* Victim) const
{
    if(!IsValid(Victim))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M10BiteSight),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Hit;return !GetWorld()->LineTraceSingleByChannel(Hit,Mouth(),Victim->GetActorLocation(),ECC_Visibility,Query);
}
bool AM10Mawcrawler::CanAttack(APawn* Victim) const
{
    return PrefersRearAttack(Victim)?CanRearGas(Victim):(CanBite(Victim)||CanHowl(Victim));
}
bool AM10Mawcrawler::PrefersRearAttack(const APawn* Victim) const
{
    if(!IsValid(Victim))return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    // Select the nearer end only where gas can reach. A distant rear target
    // releases the defensive hold so navigation can turn and pursue it.
    return FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())<0.f&&IsInRearGasRange(Victim);
}
bool AM10Mawcrawler::CanBite(APawn* Victim) const
{
    if(!IsValid(Victim)||Busy()||CooldownLeft>0.f||!GetCharacterMovement()->IsMovingOnGround())return false;
    if(const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();Vitals&&Vitals->IsDead())return false;
    if(FVector::Dist2D(Victim->GetActorLocation(),GetActorLocation())>BiteTriggerRange)return false;
    const float Facing=(Victim->GetActorLocation()-GetActorLocation()).Rotation().Yaw;
    if(FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,Facing))>BiteFacingAngle)return false;
    if(const auto* Move=Cast<UM10MovementComponent>(GetCharacterMovement());Move&&FMath::Abs(Move->GetTurnRate())>5.f)return false;
    return CanSee(Victim)||IceWallCombat::BlockingWall(this,Victim,BiteTriggerRange);
}
bool AM10Mawcrawler::GetCloseFacingYaw(float& Yaw) const
{
    if(Busy()||State==EM10State::Returning||!Target.IsValid())return false;
    const bool Rear=PrefersRearAttack(Target.Get());
    const float Distance=FVector::DistSquared2D(Target->GetActorLocation(),GetActorLocation());
    if(!Rear&&Distance>FMath::Square(BiteTriggerRange+45.f))return false;
    const float Bearing=(Target->GetActorLocation()-GetActorLocation()).Rotation().Yaw;
    // Within gas range, keep the rear posture even during cooldown. Farther
    // targets fall through to the navigation heading instead of holding the rump.
    Yaw=FRotator::NormalizeAxis(Bearing+(Rear?180.f:0.f));return true;
}
bool AM10Mawcrawler::StartAttack(APawn* Victim)
{
    if(!HasAuthority()||!CanAttack(Victim))return false;
    if(ThreatCooldownLeft<=0.f){ThreatCooldownLeft=ThreatCooldown;++ThreatSerial;ForceNetUpdate();PresentThreat();}
    if(PrefersRearAttack(Victim))
    {
        Target=Victim;LockedYaw=GetActorRotation().Yaw;RearGasStartedAt=GetWorld()->GetTimeSeconds();
        RearGasCooldownLeft=RearGasCooldown;bRearGasReleased=false;SetState(EM10State::RearGas);
        if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
        return true;
    }
    if(!CanBite(Victim))
    {
        Target=Victim;LockedYaw=GetActorRotation().Yaw;HowlStartedAt=GetWorld()->GetTimeSeconds();
        HowlCooldownLeft=HowlCooldown;NextHowlPulse=0;SetState(EM10State::Howl);
        if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
        return true;
    }
    Target=Victim;bConsumed=false;CooldownLeft=BiteCooldown;BiteLungeProgress=0.f;
    LockedYaw=GetActorRotation().Yaw;SetState(EM10State::Bite);
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
void AM10Mawcrawler::BiteContact()
{
    if(bConsumed||!HasAuthority()||State!=EM10State::Bite)return;bConsumed=true;
    APawn* Victim=Target.Get();if(!IsValid(Victim))return;
    if(IceWallCombat::ApplyMelee(this,Victim,BiteTriggerRange,PhysicalAttack))return;
    const FVector From=Mouth(),Delta=Victim->GetActorLocation()-From;
    // The new neck thrust can reach beyond the movement capsule. A wall between
    // the torso and mouth still blocks the bite even if the mouth passed its plane.
    FCollisionQueryParams JawQuery(SCENE_QUERY_STAT(M10BiteThrustWall),false,this);JawQuery.AddIgnoredActor(Victim);
    FHitResult JawBlock;
    if(GetWorld()->LineTraceSingleByChannel(JawBlock,GetMesh()->GetSocketLocation(TEXT("body_front")),From,ECC_Visibility,JawQuery))return;
    float Radius=0.f,HalfHeight=0.f;Victim->GetSimpleCollisionCylinder(Radius,HalfHeight);
    const float Horizontal=Delta.Size2D()-Radius;
    if(Horizontal>MouthReach||FMath::Abs(Delta.Z)>HalfHeight+52.5f||
        FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())<.35f||!CanSee(Victim))return;
    FHitResult Hit;Hit.Location=Hit.ImpactPoint=From+Delta.GetSafeNormal()*FMath::Max(0.f,Delta.Size()-Radius);
    Hit.ImpactNormal=-GetActorForwardVector();
    UGameplayStatics::ApplyPointDamage(Victim,PhysicalAttack,GetActorForwardVector(),Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
}
void AM10Mawcrawler::Tick(float Dt)
{
    Super::Tick(Dt);StateSeconds+=Dt;
    if(HasAuthority()){CooldownLeft=FMath::Max(0.f,CooldownLeft-Dt);HowlCooldownLeft=FMath::Max(0.f,HowlCooldownLeft-Dt);RearGasCooldownLeft=FMath::Max(0.f,RearGasCooldownLeft-Dt);ThreatCooldownLeft=FMath::Max(0.f,ThreatCooldownLeft-Dt);}
    if(State==EM10State::Crawl||State==EM10State::Returning)
        if(auto* Anim=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))Anim->SetLocomotionRate(GetVelocity().Size2D()/FMath::Max(1.f,AnimationWalkSpeed));
    if(State==EM10State::Bite)
    {
        const float Duration=BiteClip?BiteClip->GetPlayLength():1.5f;
        if(HasAuthority())AdvanceBiteLunge(StateSeconds);
        Sample(FMath::Min(StateSeconds,Duration));
        if(HasAuthority())
        {
            SetActorRotation(FRotator(0,LockedYaw,0));
            if(!Target.IsValid()){SetState(EM10State::Idle);return;}
            if(!bConsumed&&StateSeconds>=BiteContactSeconds)
            {
                Sample(BiteContactSeconds);GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();
                BiteContact();Sample(FMath::Min(StateSeconds,Duration));
            }
            if(StateSeconds>=Duration){SetState(EM10State::Idle);if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();}
        }
    }
    else if(State==EM10State::Howl)TickHowl();
    else if(State==EM10State::RearGas)TickRearGas();
    else if(State==EM10State::Stagger&&HasAuthority()&&StateSeconds>=ReactionSeconds)Combat->FinishReaction();
    else if(State==EM10State::Dying)
    {
        const float Duration=DeathClip?DeathClip->GetPlayLength():2.5f;
        const float Handoff=Duration*MonsterCombatTuning::DeathAnimationFraction;
        Sample(FMath::Min(StateSeconds,HasAuthority()&&!CorpseRagdoll->WasAttempted()?Handoff:Duration));
        if(!HasAuthority())return;
        CorpseRagdoll->RecordDeathPose(GetMesh(),Dt);
        if(!CorpseRagdoll->WasAttempted()&&StateSeconds>=Handoff&&CorpseRagdoll->Start(GetMesh()))
        {SetState(EM10State::Corpse);SetActorTickEnabled(false);}
        else if(CorpseRagdoll->WasAttempted()&&StateSeconds>=Duration)
        {Sample(Duration);CorpseRagdoll->FreezeAnimatedPose(GetMesh());SetState(EM10State::Corpse);SetActorTickEnabled(false);}
    }
}
USoundAttenuation* AM10Mawcrawler::OneShotAttenuation(float Falloff) const
{
    auto* Attenuation=NewObject<USoundAttenuation>(const_cast<AM10Mawcrawler*>(this));
    Attenuation->Attenuation.bAttenuate=true;Attenuation->Attenuation.bSpatialize=true;
    Attenuation->Attenuation.FalloffDistance=Falloff;return Attenuation;
}
void AM10Mawcrawler::OnRep_Threat(){PresentThreat();}
void AM10Mawcrawler::PresentThreat()
{
    if(GetNetMode()==NM_DedicatedServer||!ThreatSound)return;
    UGameplayStatics::PlaySoundAtLocation(this,ThreatSound,Mouth(),1.f,1.f,0.f,OneShotAttenuation(1900.f));
}
void AM10Mawcrawler::UpdateLoopAudio()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const bool Alive=!Dead()&&State!=EM10State::Corpse;
    if(BodyVoice)
    {
        if(Alive&&BodyVoice->Sound){if(!BodyVoice->IsPlaying())BodyVoice->Play();}
        else if(BodyVoice->IsPlaying())BodyVoice->Stop();
    }
    if(CrawlVoice)
    {
        const bool Moving=State==EM10State::Crawl||State==EM10State::Returning;
        if(Alive&&Moving&&CrawlVoice->Sound){if(!CrawlVoice->IsPlaying())CrawlVoice->Play();}
        else if(CrawlVoice->IsPlaying())CrawlVoice->Stop();
    }
}
void AM10Mawcrawler::InterruptAttack(float Seconds)
{
    if(!HasAuthority()||Dead())return;
    bConsumed=true;ReactionSeconds=FMath::Max(.1f,Seconds);SetState(EM10State::Stagger);Combat->BeginReaction(ReactionSeconds);
}
void AM10Mawcrawler::StartHitPresentation(){if(!Dead())Play(Combat->HitClip,false,true,.08f);}
void AM10Mawcrawler::SetHitPresentationTime(float Elapsed,float Remaining)
{
    if(Dead()||!Combat->HitClip)return;
    const float Length=Combat->HitClip->GetPlayLength();
    Sample(FMath::Clamp(Elapsed<.15f?Elapsed:Remaining>.4f?.15f:Length-FMath::Max(0.f,Remaining),0.f,Length));
}
void AM10Mawcrawler::FinishHitReaction(){if(State==EM10State::Stagger&&!Dead())SetState(EM10State::Idle);}
float AM10Mawcrawler::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||Dead()||Damage<=0.f)return 0.f;
    const float Surface=DamageSurfaceMultiplier(Event);
    auto* Weapon=CombatFormulaRuntime::ActiveWeaponHit;
    const bool FreshWeapon=Weapon&&Weapon->Target==this&&!Weapon->bResolved&&
        !CombatFormulaRuntime::IsMagic(Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr);
    float Reduced=CombatFormulaRuntime::MitigateMonster(this,Damage,Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr,Causer);
    Reduced*=Surface;
    // Keep the visible base/additional damage receipt equal to health loss.
    if(FreshWeapon&&Weapon->bResolved)Weapon->Mitigated=Weapon->Mitigated.Scaled(Surface);
    const float Applied=UDevelopmentTuningSubsystem::ShouldOneHitKill(this,EventInstigator,Causer)?Health:
        FMath::Min(Health,Reduced);
    if(Applied<=0.f)return 0.f;
    Health-=Applied;Super::TakeDamage(Applied,Event,EventInstigator,Causer);
    if(Health<=0.f)
    {
        bConsumed=true;Target.Reset();CorpseRagdoll->PrepareDeath(GetMesh());SetState(EM10State::Dying);SetLifeSpan(CorpseSeconds);
        if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
        ColdSteelSkills::NotifyKillByOwner(GetGameInstance(),EventInstigator,this);
        if(auto* PC=Cast<APlayerController>(EventInstigator);PC&&PC->IsLocalController()&&GetGameInstance())
            GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);
    }
    else Combat->ReceiveHit(Applied,EventInstigator?EventInstigator->GetPawn().Get():Cast<APawn>(Causer),MonsterToughness::FormOf(Event.DamageTypeClass));
    return Applied;
}
