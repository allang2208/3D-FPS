#include "SpiralPillarM14.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "M14SoftBodyDeath.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterAIController.h"
#include "MonsterCombatTuning.h"
#include "FatZombieAnimInstance.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/IceWallCombat.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Sight.h"

ASpiralPillarM14::ASpiralPillarM14(const FObjectInitializer& Initializer)
    : Super(Initializer.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick=true;bReplicates=true;
    Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    CorpseRagdoll=CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    CorpseRagdoll->Rig=EMonsterCorpseRig::SpiralPillar;
    SoftBodyDeath=CreateDefaultSubobject<UM14SoftBodyDeathComponent>(TEXT("SoftBodyDeath"));
    GetCapsuleComponent()->InitCapsuleSize(110.f,150.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    GetMesh()->SetRelativeLocation(FVector(0,0,-150.f));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    auto* Move=GetCharacterMovement();Move->MaxWalkSpeed=WalkSpeed;
    Move->MaxAcceleration=100.f;Move->BrakingDecelerationWalking=180.f;
    Move->RotationRate=FRotator(0,25.f,0);Move->bOrientRotationToMovement=true;
    Move->bCanWalkOffLedges=false;Move->MaxStepHeight=25.f;
    // Reuse the existing large-creature navmesh; do not require a map rebuild.
    Move->SetUpdateNavAgentWithOwnersCollisions(false);
    Move->GetNavAgentPropertiesRef().AgentRadius=225.f;
    Move->GetNavAgentPropertiesRef().AgentHeight=450.f;
    Move->GetNavAgentPropertiesRef().AgentStepHeight=30.f;
    bUseControllerRotationYaw=false;BaseEyeHeight=100.f;
    AIControllerClass=AMonsterAIController::StaticClass();AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("SpiralPillarM14"));
}
void ASpiralPillarM14::ApplyVisual()
{
    if(!VisualMesh)return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    const auto& Ref=VisualMesh->GetRefSkeleton();
    TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 Jaw=Ref.FindBoneIndex(TEXT("mouth_socket")),Body=Ref.FindBoneIndex(TEXT("spine_01"));
    if(Jaw!=INDEX_NONE&&Body!=INDEX_NONE)
        GetMesh()->SetRelativeRotation(FRotator(0,-(Frames[Jaw].GetLocation()-Frames[Body].GetLocation()).Rotation().Yaw,0));
    const int32 Base=Ref.FindBoneIndex(TEXT("base"));
    for(int32 I=0;I<8;++I)
    {
        const int32 Toe=Ref.FindBoneIndex(FName(*FString::Printf(TEXT("roottoe_%02d"),I)));
        if(Toe==INDEX_NONE||Base==INDEX_NONE)continue;
        const FVector Radial=(Frames[Toe].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
        // Blender's authored toe is 46 cm outward and 8.5 cm down in the bind pose.
        SweepTipOffsets[I]=Frames[Toe].InverseTransformVector(Radial*46.f-FVector::UpVector*8.5f);
        if(I==0)bPositiveXIsRight=GetMesh()->GetRelativeTransform().TransformVector(Radial).Y>0.f;
    }
    const auto Bounds=VisualMesh->GetBounds();
    GetMesh()->SetRelativeLocation(FVector(0,0,-GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()-(Bounds.Origin.Z-Bounds.BoxExtent.Z)));
}
void ASpiralPillarM14::OnConstruction(const FTransform& Transform){Super::OnConstruction(Transform);ApplyVisual();}
void ASpiralPillarM14::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);
    if(auto* AI=Cast<AMonsterAIController>(NewController))
    {
        // Configure this species' listener as well as its combat range; the
        // shared controller's 16 m default cannot acquire a 30 m spit target.
        auto* Sight=NewObject<UAISenseConfig_Sight>(AI);
        Sight->SightRadius=AggroRadius;Sight->LoseSightRadius=AggroRadius+300.f;
        Sight->PeripheralVisionAngleDegrees=100.f;Sight->SetMaxAge(12.f);
        Sight->DetectionByAffiliation.bDetectEnemies=Sight->DetectionByAffiliation.bDetectFriendlies=Sight->DetectionByAffiliation.bDetectNeutrals=true;
        AI->GetPerceptionComponent()->ConfigureSense(*Sight);AI->GetPerceptionComponent()->RequestStimuliListenerUpdate();
    }
}
void ASpiralPillarM14::BeginPlay()
{
    Super::BeginPlay();ApplyVisual();Home=GetActorLocation();PreviousYaw=GetActorRotation().Yaw;
    if(HasAuthority()){MaxHealth*=float(MonsterCoreStats::HealthMultiplier());Health=MaxHealth;}
    GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;
    GetMesh()->AddTickPrerequisiteActor(this);GetMesh()->AddTickPrerequisiteComponent(Combat);
    PresentState();if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void ASpiralPillarM14::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ASpiralPillarM14,State);DOREPLIFETIME(ASpiralPillarM14,Health);
}
void ASpiralPillarM14::OnRep_State(){StateSeconds=0.f;PresentState();}
void ASpiralPillarM14::Play(UAnimSequence* Clip,bool Loop,bool Clock,float Blend)
{
    if(auto* Anim=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))Anim->TransitionTo(Clip,Loop,Clock,Blend);
}
void ASpiralPillarM14::Sample(float Seconds)
{
    if(auto* Anim=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))Anim->SetCombatTime(Seconds);
}
void ASpiralPillarM14::PresentState()
{
    const bool Moving=State==EM14State::Crawl||State==EM14State::Returning;
    GetCharacterMovement()->bOrientRotationToMovement=Moving;
    if((State==EM14State::Dying||State==EM14State::Corpse)&&SoftBodyDeathData&&
        SoftBodyDeath->Start(GetMesh(),SoftBodyDeathData,GetVelocity()))
    {
        GetCharacterMovement()->DisableMovement();GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Combat->SetComponentTickEnabled(false);
        // Client presentation also finishes if the replicated Corpse state arrives early.
        SetActorTickEnabled(true);return;
    }
    if(!SoftDeathMorphTargets.IsEmpty()&&(State==EM14State::Dying||State==EM14State::Corpse))
    {
        GetMesh()->SetBoundsScale(2.75f);
        ApplySoftDeath(State==EM14State::Corpse?MAX_flt:0.f);
    }
    if(State==EM14State::Corpse)return;
    if(State==EM14State::Stagger){StartHitPresentation();return;}
    Play(Moving?MoveClip.Get():IsAttacking()?AttackClip(State):State==EM14State::Dying?DeathClip.Get():IdleClip.Get(),
        Moving||State==EM14State::Idle,IsAttacking()||State==EM14State::Dying,State==EM14State::Dying?.42f:.16f);
    if(State==EM14State::Dying)
    {
        GetCharacterMovement()->DisableMovement();GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Combat->SetComponentTickEnabled(false);
    }
}
void ASpiralPillarM14::SetState(EM14State Next)
{
    State=Next;StateSeconds=0.f;
    if(HasAuthority()&&Next!=EM14State::Crawl&&Next!=EM14State::Returning)GetCharacterMovement()->StopMovementImmediately();
    PresentState();ForceNetUpdate();
}
void ASpiralPillarM14::SetLocomotion(bool Moving,bool Returning)
{
    if(Busy())return;const auto Next=Moving?(Returning?EM14State::Returning:EM14State::Crawl):EM14State::Idle;
    if(State!=Next)SetState(Next);
}
FVector ASpiralPillarM14::Mouth() const{return GetMesh()->GetSocketLocation(TEXT("mouth_socket"));}
bool ASpiralPillarM14::IsWeakpointHit(const FHitResult& Hit) const
{
    // Keep lethal hit receipts classifiable after death; resolve the crit once in shared combat.
    return Hit.GetActor()==this&&(!Hit.GetComponent()||Hit.GetComponent()==GetMesh())&&
        !Hit.BoneName.IsNone()&&(Hit.BoneName==TEXT("maw")||GetMesh()->BoneIsChildOf(Hit.BoneName,TEXT("maw")));
}
bool ASpiralPillarM14::CanSee(const APawn* Victim) const
{
    if(!IsValid(Victim))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M14BiteSight),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Hit;return !GetWorld()->LineTraceSingleByChannel(Hit,Mouth(),Victim->GetActorLocation(),ECC_Visibility,Query);
}
bool ASpiralPillarM14::CanAttack(APawn* Victim) const
{
    return ChooseAttack(Victim)!=EM14State::Idle;
}
bool ASpiralPillarM14::StartAttack(APawn* Victim)
{
    if(!HasAuthority())return false;
    const EM14State Attack=ChooseAttack(Victim);if(Attack==EM14State::Idle)return false;
    Target=Victim;AttackTarget=Victim;LockedYaw=GetActorRotation().Yaw;bConsumed=false;
    SweepVictims.Reset();NextSweepSample=SweepStartSeconds;bSpitAimLocked=false;
    WhirlwindVictims.Reset();WhirlwindSample=1;
    SpitAimPoint=Victim->GetActorLocation();
    SpitAimVelocity=Victim->GetVelocity();SpitAimSampleSeconds=0.f;
    if(Attack==EM14State::Spit){SpitCooldownLeft=SpitCooldown;CooldownLeft=SpitClip->GetPlayLength()+.6f;}
    else if(Attack==EM14State::Whirlwind)
    {WhirlwindCooldownLeft=WhirlwindCooldown;CooldownLeft=WhirlwindClip->GetPlayLength()+.4f;}
    else if(Attack==EM14State::TrunkSlam)
    {SlamCooldownLeft=SlamCooldown;CooldownLeft=TrunkSlamClip->GetPlayLength()+.5f;}
    else if(Attack==EM14State::SweepLeft||Attack==EM14State::SweepRight)
    {SweepCooldownLeft=SweepCooldown;CooldownLeft=AttackClip(Attack)->GetPlayLength()+.4f;}
    else CooldownLeft=BiteCooldown;
    SetState(Attack);
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
void ASpiralPillarM14::BiteContact()
{
    if(bConsumed||!HasAuthority()||State!=EM14State::Bite)return;bConsumed=true;
    APawn* Victim=AttackTarget.Get();if(!IsValid(Victim))return;
    if(IceWallCombat::ApplyMelee(this,Victim,BiteTriggerRange,PhysicalAttack))return;
    const FVector From=Mouth(),Delta=Victim->GetActorLocation()-From;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M14MawThrustWall),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Block;
    if(GetWorld()->LineTraceSingleByChannel(Block,GetMesh()->GetSocketLocation(TEXT("spine_01")),From,ECC_Visibility,Query))return;
    float Radius=0.f,HalfHeight=0.f;Victim->GetSimpleCollisionCylinder(Radius,HalfHeight);
    if(Delta.Size2D()-Radius>MouthReach||FMath::Abs(Delta.Z)>HalfHeight+30.f||
        FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())<.25f||!CanSee(Victim))return;
    FHitResult Hit;Hit.Location=Hit.ImpactPoint=From+Delta.GetSafeNormal()*FMath::Max(0.f,Delta.Size()-Radius);
    Hit.ImpactNormal=-GetActorForwardVector();
    UGameplayStatics::ApplyPointDamage(Victim,PhysicalAttack,GetActorForwardVector(),Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
}
void ASpiralPillarM14::Tick(float Dt)
{
    Super::Tick(Dt);StateSeconds+=Dt;
    if((State==EM14State::Dying||State==EM14State::Corpse)&&SoftBodyDeath->IsActive())
    {
        if(SoftBodyDeath->Advance(Dt))
        {
            if(HasAuthority()&&State!=EM14State::Corpse)SetState(EM14State::Corpse);
            SetActorTickEnabled(false);
        }
        return;
    }
    const float CloseFacing=TrunkSlamClip&&SlamCooldownLeft<=0.f?FMath::Max(BiteTriggerRange,SlamTriggerRange)+35.f:BiteTriggerRange+35.f;
    const float FacingRange=SpitClip&&SpitCooldownLeft<=0.f?FMath::Max(CloseFacing,SpitMaxRange):CloseFacing;
    if(HasAuthority()&&!Busy()&&State!=EM14State::Returning&&Target.IsValid()&&
        FVector::DistSquared2D(GetActorLocation(),Target->GetActorLocation())<FMath::Square(FacingRange))
    {
        const float Desired=(Target->GetActorLocation()-GetActorLocation()).Rotation().Yaw;
        const float Delta=FMath::Clamp(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,Desired),-25.f*Dt,25.f*Dt);
        SetActorRotation(FRotator(0,GetActorRotation().Yaw+Delta,0));
    }
    const float Yaw=GetActorRotation().Yaw;
    const float Turn=FMath::FindDeltaAngleDegrees(PreviousYaw,Yaw)/FMath::Max(Dt,.001f);PreviousYaw=Yaw;
    if(HasAuthority())
    {
        CooldownLeft=FMath::Max(0.f,CooldownLeft-Dt);
        SpitCooldownLeft=FMath::Max(0.f,SpitCooldownLeft-Dt);
        SweepCooldownLeft=FMath::Max(0.f,SweepCooldownLeft-Dt);
        SlamCooldownLeft=FMath::Max(0.f,SlamCooldownLeft-Dt);
        WhirlwindCooldownLeft=FMath::Max(0.f,WhirlwindCooldownLeft-Dt);
    }
    if(State==EM14State::Crawl||State==EM14State::Returning||State==EM14State::Idle)
    {
        if(auto* Anim=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
        {
            UAnimSequence* Next=FMath::Abs(Turn)>8.f?(Turn<0?TurnLeftClip.Get():TurnRightClip.Get()):State==EM14State::Idle?IdleClip.Get():MoveClip.Get();
            if(Next&&Anim->ActiveClip!=Next)Play(Next,true,false,.25f);
            // Keep the source stride speed at 28: 56 cm/s needs 2x the original cycle.
            Anim->SetLocomotionRate(Next==IdleClip?1.f:FMath::Max(GetVelocity().Size2D()/FMath::Max(1.f,AnimationWalkSpeed),FMath::Abs(Turn)/25.f));
        }
    }
    if(IsAttacking())TickAttack(Dt);
    else if(State==EM14State::Stagger&&HasAuthority()&&StateSeconds>=ReactionSeconds)Combat->FinishReaction();
    else if(State==EM14State::Dying)
    {
        const float Duration=DeathClip?DeathClip->GetPlayLength():3.f;
        // The compound corpse must not take over before the tissue has settled.
        const float Settled=SoftDeathMorphTimes.IsEmpty()?0.f:SoftDeathMorphTimes.Last();
        const float Handoff=FMath::Max(Settled,Duration*FMath::Clamp(DeathPhysicsFraction,0.f,1.f));
        const float PoseTime=FMath::Min(StateSeconds,HasAuthority()&&!CorpseRagdoll->WasAttempted()?Handoff:Duration);
        Sample(PoseTime);ApplySoftDeath(PoseTime);
        if(!HasAuthority())return;
        CorpseRagdoll->RecordDeathPose(GetMesh(),Dt);
        if(!CorpseRagdoll->WasAttempted()&&StateSeconds>=Handoff&&StartCorpsePhysics())
        {SetState(EM14State::Corpse);SetActorTickEnabled(false);}
        else if(CorpseRagdoll->WasAttempted()&&StateSeconds>=Duration)
        {Sample(Duration);CorpseRagdoll->FreezeAnimatedPose(GetMesh());SetState(EM14State::Corpse);SetActorTickEnabled(false);}
    }
}
void ASpiralPillarM14::InterruptAttack(float Seconds)
{
    if(!HasAuthority()||Dead())return;bConsumed=true;ReactionSeconds=FMath::Max(.1f,Seconds);
    SetState(EM14State::Stagger);Combat->BeginReaction(ReactionSeconds);
}
void ASpiralPillarM14::StartHitPresentation(){if(!Dead())Play(Combat->HitClip,false,true,.08f);}
void ASpiralPillarM14::SetHitPresentationTime(float Elapsed,float Remaining)
{
    if(Dead()||!Combat->HitClip)return;const float Length=Combat->HitClip->GetPlayLength();
    Sample(FMath::Clamp(Elapsed<.12f?Elapsed:Remaining>.4f?.12f:Length-FMath::Max(0.f,Remaining),0.f,Length));
}
void ASpiralPillarM14::FinishHitReaction(){if(State==EM14State::Stagger&&!Dead())SetState(EM14State::Idle);}
float ASpiralPillarM14::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||Dead()||Damage<=0.f)return 0.f;
    const float Reduced=CombatFormulaRuntime::MitigateMonster(this,Damage,Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr,Causer);
    const float Applied=UDevelopmentTuningSubsystem::ShouldOneHitKill(this,EventInstigator,Causer)?Health:FMath::Min(Health,Reduced);
    if(Applied<=0.f)return 0.f;
    Health-=Applied;Super::TakeDamage(Applied,Event,EventInstigator,Causer);
    if(Health<=0.f)
    {
        bConsumed=true;Target.Reset();AttackTarget.Reset();CancelProjectile();SweepVictims.Reset();WhirlwindVictims.Reset();
        const bool Soft=SoftBodyDeathData&&SoftBodyDeath->Start(GetMesh(),SoftBodyDeathData,GetVelocity());
        if(!Soft)
        {
            if(CorpsePhysicsAsset&&SoftDeathMorphTargets.IsEmpty())GetMesh()->SetPhysicsAsset(CorpsePhysicsAsset);
            CorpseRagdoll->PrepareDeath(GetMesh());
        }
        SetState(EM14State::Dying);SetLifeSpan(CorpseSeconds);
        if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
        ColdSteelSkills::NotifyKillByOwner(GetGameInstance(),EventInstigator,this);
        if(auto* PC=Cast<APlayerController>(EventInstigator);PC&&PC->IsLocalController()&&GetGameInstance())
            GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);
    }
    else Combat->ReceiveHit(Applied,EventInstigator?EventInstigator->GetPawn().Get():Cast<APawn>(Causer),MonsterToughness::FormOf(Event.DamageTypeClass));
    return Applied;
}
