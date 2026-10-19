#include "NurseZombie.h"
#include "FatZombieAnimInstance.h"
#include "Net/UnrealNetwork.h"
#include "MonsterReactionTiming.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/IceWallCombat.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "HumanoidKnockdownComponent.h"
#include "MonsterCombatTuning.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/Skeleton.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#endif
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
bool UsesFacelessStaffTransitions(const AActor* Actor)
{
    return Actor->ActorHasTag(TEXT("FacelessResearcher")) ||
        Actor->ActorHasTag(TEXT("FacelessReceptionist")) ||
        Actor->ActorHasTag(TEXT("FacelessSecurity"));
}
// M-01 humanoid staff share NurseZombie defaults; role tags bias vitals within
// ?20% so each posting reads differently without a per-variant class.
struct FStaffVitalBias { const TCHAR* Tag; float HealthMul, DamageMul, WalkSpeed; };
static const FStaffVitalBias StaffVitalBiases[] =
{
    {TEXT("FacelessSecurity"),     1.16f, 1.18f, 95.f},
    {TEXT("CargoPorter"),          1.12f, 1.14f, 92.f},
    {TEXT("EcologyGardener"),      1.06f, 1.09f, 95.f},
    {TEXT("NightWarden"),          1.02f, 1.05f, 95.f},
    {TEXT("CargoTechnician"),      0.92f, 0.95f, 92.f},
    {TEXT("FacelessResearcher"),   0.84f, 0.86f, 90.f},
    {TEXT("FacelessReceptionist"), 0.80f, 0.82f, 90.f},
};
}
ANurseZombie::ANurseZombie(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(ACharacter::CharacterMovementComponentName)
        .SetDefaultSubobjectClass<UMonsterIdleBreathingMeshComponent>(ACharacter::MeshComponentName))
{
    PrimaryActorTick.bCanEverTick = true;
    Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    Knockdown=CreateDefaultSubobject<UHumanoidKnockdownComponent>(TEXT("HumanoidKnockdown"));
    AIControllerClass=AMonsterAIController::StaticClass();AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    GetCapsuleComponent()->InitCapsuleSize(34.f, 92.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    GetMesh()->SetRelativeLocation(FVector(0,0,-92.f));
    GetMesh()->SetRelativeRotation(FRotator(0,-90.f,0));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bRunPhysicsWithNoController = true;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0,180,0);
    GetCharacterMovement()->MaxStepHeight = 40.f;
    GetCharacterMovement()->bCanWalkOffLedges = false;
    Tags.Add(TEXT("Enemy"));
    Tags.Add(TEXT("NurseZombie"));
    // Shared humanoid voice: quiet breathing loop on the body plus state-edge
    // one-shots. Missing assets degrade silently for deferred imports.
    BodyVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("BodyVoice"));
    BodyVoice->SetupAttachment(GetMesh());BodyVoice->bAutoActivate=false;
    BodyVoice->bOverrideAttenuation=true;BodyVoice->AttenuationOverrides.bAttenuate=true;
    BodyVoice->AttenuationOverrides.bSpatialize=true;BodyVoice->AttenuationOverrides.FalloffDistance=950.f;
    const struct {const TCHAR* Key;TObjectPtr<USoundBase>* Slot;} AudioMap[]={
        {TEXT("Idle"),&NurseIdleSound},{TEXT("Chase"),&NurseChaseSound},{TEXT("Attack"),&AttackSound},
        {TEXT("HitA"),&HitSoundA},{TEXT("HitB"),&HitSoundB},{TEXT("Death"),&NurseDeathSound},
        {TEXT("StepA"),&StepSoundA},{TEXT("StepB"),&StepSoundB}};
    for(const auto& Entry:AudioMap)
    {
        const FString Path=FString::Printf(TEXT("/Game/Monsters/Shared/HumanoidAudioV1/S_Humanoid_%s.S_Humanoid_%s"),Entry.Key,Entry.Key);
        ConstructorHelpers::FObjectFinder<USoundBase> Found(*Path);
        if(Found.Succeeded())*Entry.Slot=Found.Object;
    }
}

void ANurseZombie::PrepareDeferredAllocation()
{
    TInlineComponentArray<UActorComponent*> Components(this);
    for (auto* Component : Components)
        if (Component->bAutoRegister)
        {
            DeferredRegistration.Add(Component);
            Component->bAutoRegister=false;
        }
}

void ANurseZombie::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    if (VisualMesh) GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    if (!DeferredRegistration.IsEmpty())
    {
        for (const auto& Component : DeferredRegistration)
            if (Component.IsValid()) Component->bAutoRegister=true;
        DeferredRegistration.Reset();
        // ExecuteConstruction has applied the final transform. Register here,
        // before PostInitializeComponents/BeginPlay, never at the holding origin.
        RegisterAllComponents();
    }
}

void ANurseZombie::BeginPlay()
{
    Super::BeginPlay();
    SpawnPosition=GetActorLocation();
    // Living-area employees retain donor tags for animation transitions/grounding,
    // but their Blueprint vitals are already final and must not receive the donor's job bias.
    if (!ActorHasTag(TEXT("StaffLivingEmployee")))
        for (const FStaffVitalBias& Bias : StaffVitalBiases)
            if (ActorHasTag(Bias.Tag)) { MaxHealth*=Bias.HealthMul; AttackDamage*=Bias.DamageMul; WalkSpeed=Bias.WalkSpeed; break; }
    // ?????????MonsterCoreStats::HealthMultiplier??????/???/?????/????????????????    MaxHealth*=static_cast<float>(MonsterCoreStats::HealthMultiplier());
    Health = MaxHealth;
    if (VisualMesh) GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    if(BodyVoice&&NurseIdleSound)BodyVoice->SetSound(NurseIdleSound);
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
    if (!GetMesh()->GetSkeletalMeshAsset() || !IdleClip || !WalkClip || !AttackClip)
    {
        UE_LOG(LogTemp, Error, TEXT("NURSE_ASSET_MISSING %s"), *GetName());
        SetActorTickEnabled(false);
        return;
    }
    SetState(ENurseState::Idle);
    UE_LOG(LogTemp, Display, TEXT("NURSE_READY %s location=%s attack=%.3f health=%.1f/%.1f damage=%.1f"), *GetName(), *GetActorLocation().ToString(), AttackClip->GetPlayLength(), Health, MaxHealth, AttackDamage);
}

void ANurseZombie::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ANurseZombie, State);
}
void ANurseZombie::OnRep_State()
{
    // ????????etState ??????????????????????????????????    if(!HasAuthority())SetState(State);
}
void ANurseZombie::SetState(ENurseState NewState)
{
    State = NewState;
    StateTime = 0.f;
    UAnimSequence* Clip = State == ENurseState::Chase ? WalkClip : State == ENurseState::Attack ? AttackClip : IdleClip;
    if (State != ENurseState::Dead && State != ENurseState::Stagger && Clip)
    {
        StartStateAnimation(Clip,State!=ENurseState::Attack);
    }
    // Replicated state edges carry the one-shots to every endpoint; the loop
    // voice only runs while the zombie is alive (dedi skips audio entirely).
    UpdateVoice();
    if(GetNetMode()!=NM_DedicatedServer)
    {
        const FVector Mouth=GetActorLocation()+FVector(0,0,120);
        if(State==ENurseState::Chase&&NurseChaseSound)
            UGameplayStatics::PlaySoundAtLocation(this,NurseChaseSound,Mouth,.9f,1.f,0.f,OneShotAttenuation(1600.f));
        else if(State==ENurseState::Attack&&AttackSound)
            UGameplayStatics::PlaySoundAtLocation(this,AttackSound,Mouth,1.f,1.f,0.f,OneShotAttenuation(1400.f));
        else if(State==ENurseState::Stagger)
        {
            if(USoundBase* Hit=(bAudioHitAlt=!bAudioHitAlt)?HitSoundA:HitSoundB)
                UGameplayStatics::PlaySoundAtLocation(this,Hit,Mouth,.85f,1.f,0.f,OneShotAttenuation(1200.f));
        }
        else if(State==ENurseState::Dead&&NurseDeathSound)
            UGameplayStatics::PlaySoundAtLocation(this,NurseDeathSound,Mouth,1.f,1.f,0.f,OneShotAttenuation(1800.f));
    }
    if (State != ENurseState::Chase) GetCharacterMovement()->StopMovementImmediately();
    if (State == ENurseState::Attack) bAttackConsumed = false;
}
USoundAttenuation* ANurseZombie::OneShotAttenuation(float Falloff) const
{
    auto* Attenuation=NewObject<USoundAttenuation>(const_cast<ANurseZombie*>(this));
    Attenuation->Attenuation.bAttenuate=true;Attenuation->Attenuation.bSpatialize=true;
    Attenuation->Attenuation.FalloffDistance=Falloff;return Attenuation;
}
void ANurseZombie::UpdateVoice()
{
    if(GetNetMode()==NM_DedicatedServer||!BodyVoice)return;
    if(State!=ENurseState::Dead&&BodyVoice->Sound){if(!BodyVoice->IsPlaying())BodyVoice->Play();}
    else if(BodyVoice->IsPlaying())BodyVoice->Stop();
}

void ANurseZombie::StartStateAnimation(UAnimSequence* Clip,bool bLoop)
{
    if (UsesFacelessStaffTransitions(this))
    {
        if (!Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
            GetMesh()->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
        if (auto* Animation = Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
        {
            FMonsterClipTransition Settings;
            Settings.InitialPlayRate = Clip ? Clip->RateScale : 1.f;
            if (bLoop && Clip == WalkClip)
                Settings.InitialPlayRate *= FMath::Clamp(GetVelocity().Size2D()/26.f,.15f,3.5f);
            Settings.bContinueOutgoingLoop = bLoop;
            Animation->TransitionTo(Clip,bLoop,!bLoop,bLoop?.24f:.10f,Settings);
            PresentedClip = Clip;
            return;
        }
    }
    GetMesh()->PlayAnimation(Clip,bLoop);
    PresentedClip = Clip;
    GetMesh()->SetPlayRate(bLoop?1.f:0.f);
}
void ANurseZombie::SetAttackAnimationTime(float Seconds)
{
    if (UsesFacelessStaffTransitions(this))
        if (auto* Animation = Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
        { Animation->SetCombatTime(Seconds); return; }
    GetMesh()->SetPosition(Seconds,false);
}
float ANurseZombie::GetAttackDuration() const { return AttackClip ? AttackClip->GetPlayLength() : 0.f; }
void ANurseZombie::ProcessAttackContact(float Previous, float Current)
{
    if (Previous <= ContactEnd && Current >= ContactTime) TryMelee();
}
void ANurseZombie::SetWalkAnimationRate(float Rate)
{
    if (UsesFacelessStaffTransitions(this))
        if (auto* Animation = Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
        { Animation->SetLocomotionRate(Rate*(WalkClip?WalkClip->RateScale:1.f)); return; }
    GetMesh()->SetPlayRate(Rate);
}

void ANurseZombie::StartHitPresentation(UAnimSequence* Clip, float Duration)
{
    if (Clip && UsesFacelessStaffTransitions(this))
    {
        if (!Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
            GetMesh()->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
        if (auto* Animation = Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
        {
            // Repeated hits reuse the player but recapture the visible pose;
            // the reset reaction clock must not revive an older snapshot.
            const float BlendSeconds = Animation->ActiveClip == Clip ? .04f : .07f;
            Animation->TransitionTo(Clip,false,true,BlendSeconds);
            Animation->SetControlledBlendTime(0.f);
            Animation->SetCombatTime(0.f);
            PresentedClip = Clip;
            return;
        }
    }
    // Automatic fire re-issues the same reaction every bullet. PlayAnimation
    // rebuilds the single-node player on each call; restarting the sample time
    // produces the identical pose without that per-bullet animation churn.
    if (Clip && Clip == PresentedClip && GetMesh()->GetAnimationMode()==EAnimationMode::AnimationSingleNode)
    {
        GetMesh()->SetPlayRate(0);
        GetMesh()->SetPosition(0, false);
        return;
    }
    if (Clip)
    {
        GetMesh()->PlayAnimation(Clip, false);
        PresentedClip = Clip;
        GetMesh()->SetPlayRate(0);
        GetMesh()->SetPosition(0, false);
    }
    else
    {
        GetMesh()->SetPlayRate(0);
        UE_LOG(LogTemp, Warning, TEXT("MONSTER_HIT_CLIP_MISSING %s"), *GetName());
    }
}

void ANurseZombie::SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining)
{
    if (!Clip) return;
    const float Length=Clip->GetPlayLength();
    const float Time = Combat->IsImmobileReaction() ? FMath::Min(Elapsed,.15f) : !Combat->bStunned ?
        MonsterReactionTiming::StaggerSample(Elapsed,Remaining,Length,.15f,.15f) :
        (Elapsed < .15f ? Elapsed : (Remaining > .4f ? .15f : Length - FMath::Max(0.f, Remaining)));
    if (UsesFacelessStaffTransitions(this))
        if (auto* Animation = Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
        {
            Animation->SetCombatTime(FMath::Clamp(Time,0.f,Length));
            Animation->SetControlledBlendTime(Elapsed);
            return;
        }
    GetMesh()->SetPosition(FMath::Clamp(Time, 0.f, Clip->GetPlayLength()), false);
}

bool ANurseZombie::CanSee(const AActor* Actor) const
{
    if (!IsValid(Actor)) return false;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(NurseSight), false, this);
    Params.AddIgnoredActor(Actor);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation()+FVector(0,0,35), Actor->GetActorLocation(), ECC_Visibility, Params);
}

void ANurseZombie::TryMelee()
{
    if (bAttackConsumed || !Target.IsValid()) return;
    if(IceWallCombat::ApplyMelee(this,Target.Get(),MonsterCombatTuning::AttackDistance(AttackRange),AttackDamage,.55f))
    {bAttackConsumed=true;return;}
    const FVector Offset = Target->GetActorLocation() - GetActorLocation();
    if (Offset.Size2D() > MonsterCombatTuning::AttackDistance(AttackRange) || FMath::Abs(Offset.Z) > 90.f ||
        FVector::DotProduct(GetActorForwardVector(),Offset.GetSafeNormal2D()) < .55f || !CanSee(Target.Get())) return;
    bAttackConsumed = true;
    ApplyMeleeDamage(Target.Get());
    ++SuccessfulHits;
    UE_LOG(LogTemp, Display, TEXT("NURSE_MELEE time=%.3f hit=%d"),StateTime,SuccessfulHits);
}

float ANurseZombie::ApplyMeleeDamage(APawn* Victim)
{
    return UGameplayStatics::ApplyDamage(Victim,AttackDamage,GetController(),this,UEnemyMeleeDamage::StaticClass());
}

void ANurseZombie::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    // Shamble steps: stride-driven on the real velocity, not a chained loop.
    if(GetNetMode()!=NM_DedicatedServer&&State==ENurseState::Chase&&GetVelocity().Size2D()>20.f)
    {
        AudioStepClock+=DeltaSeconds;
        if(AudioStepClock>=FMath::Clamp(55.f/GetVelocity().Size2D(),.22f,.9f))
        {
            AudioStepClock=0.f;
            if(USoundBase* Step=(bAudioStepAlt=!bAudioStepAlt)?StepSoundA:StepSoundB)
                UGameplayStatics::PlaySoundAtLocation(this,Step,GetActorLocation()-FVector(0,0,80),.45f,1.f,0.f,OneShotAttenuation(700.f));
        }
    }
    else AudioStepClock=0.f;
    if (!HasAuthority() || State == ENurseState::Dead || (Knockdown && Knockdown->IsControlling())) return;
    const float Previous = StateTime;
    StateTime += DeltaSeconds;
    Cooldown = FMath::Max(0.f,Cooldown-DeltaSeconds);
    if (State == ENurseState::Stagger)
    {
        if (StateTime >= StaggerSeconds) Combat->FinishReaction();
        return;
    }
    if (State == ENurseState::Attack)
    {
        SetAttackAnimationTime(FMath::Min(StateTime,GetAttackDuration()));
        ProcessAttackContact(Previous, StateTime);
        // ApplyDamage can synchronously parry/kill us. The interrupted attack
        // must not write recovery state after that callback returns.
        if (State != ENurseState::Attack) return;
        if (StateTime >= GetAttackDuration())
        {
            Cooldown = RecoveryTime;
            State=ENurseState::Recovery;StateTime=0;
        }
        return;
    }
    if(State==ENurseState::Chase)SetWalkAnimationRate(FMath::Clamp(GetVelocity().Size2D()/26.f,.15f,3.5f));
}

void ANurseZombie::InterruptAttack(float Seconds)
{
    if (!HasAuthority() || State == ENurseState::Dead) return;
    if (Knockdown && Knockdown->IsControlling()) { Knockdown->ExtendControl(Seconds); return; }
    if (State==ENurseState::Stagger) Seconds=FMath::Max(Seconds,StaggerSeconds-StateTime);
    bAttackConsumed = true;
    StaggerSeconds = FMath::Max(.01f,Seconds);
    Cooldown = FMath::Max(Cooldown,.6f);
    SetState(ENurseState::Stagger);
    Combat->BeginReaction(StaggerSeconds);
}

void ANurseZombie::CancelAttackForLocomotion()
{
    if (!HasAuthority() || (State != ENurseState::Attack && State != ENurseState::Recovery)) return;
    bAttackConsumed = true;
    SetState(ENurseState::Chase);
}

float ANurseZombie::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    if (!HasAuthority() || State == ENurseState::Dead || Damage <= 0.f) return 0.f;
    if (UDevelopmentTuningSubsystem::ShouldOneHitKill(this, EventInstigator, Causer)) Damage = Health;
    else Damage=CombatFormulaRuntime::MitigateMonster(this,Damage,Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr,Causer);
    if(Damage<=0)return 0.f;
    const float Before = Health;
    Health = FMath::Max(0.f, Health - Damage);
    const float Applied = Before - Health;
    Super::TakeDamage(Applied,Event,EventInstigator,Causer);
    if (Health > 0.f) Combat->ReceiveHit(Applied,EventInstigator?EventInstigator->GetPawn().Get():Cast<APawn>(Causer),
        MonsterToughness::FormOf(Event.DamageTypeClass));
    else
    {
        SetState(ENurseState::Dead);
        if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
        bAttackConsumed = true;
        Target.Reset();
        GetCharacterMovement()->DisableMovement();
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if (!Knockdown || !Knockdown->OnDeath()) StartDeathPresentation();
        SetLifeSpan(CorpseSeconds);
        UE_LOG(LogTemp, Display, TEXT("NURSE_KILLED %s"),*GetName());
        ColdSteelSkills::NotifyKillByOwner(GetGameInstance(),EventInstigator,this);
        if(auto* PlayerController=Cast<APlayerController>(EventInstigator))
            if(PlayerController->IsLocalController()&&GetGameInstance())
                GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);
    }
    const FName Bone = Event.IsOfType(FPointDamageEvent::ClassID)
        ? static_cast<const FPointDamageEvent&>(Event).HitInfo.BoneName : NAME_None;
    // Per-bullet damage reporting belongs to Verbose; the default stream stays
    // readable while an automatic rifle is firing.
    UE_LOG(LogTemp, Verbose, TEXT("MONSTER_DAMAGE target=%s requested=%.2f applied=%.2f health=%.2f->%.2f/%.2f dead=%d bone=%s causer=%s"),
        *GetName(), Damage, Applied, Before, Health, MaxHealth, State == ENurseState::Dead, *Bone.ToString(), *GetNameSafe(Causer));
    return Applied;
}

void ANurseZombie::StartDeathPresentation()
{
    if (Knockdown) { Knockdown->StartDeath(); return; }
    GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
    GetMesh()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
    GetMesh()->SetSimulatePhysics(true);
    GetMesh()->WakeAllRigidBodies();
    GetMesh()->AddImpulse(-GetActorForwardVector()*110.f,TEXT("pelvis"),true);
}

bool ANurseZombie::PrepareInPlaceAnimation(UAnimSequence* Clip)
{
#if WITH_EDITOR
    if (!Clip || !Clip->GetPathName().StartsWith(TEXT("/Game/Monsters/NurseZombie/")) || !Clip->GetSkeleton()) return false;
    const FName Root = Clip->GetSkeleton()->GetReferenceSkeleton().GetBoneName(0);
    TArray<FTransform> Keys;
    Clip->GetDataModel()->GetBoneTrackTransforms(Root, Keys);
    if (Keys.Num()<2) return false;
    const FVector Drift = (Keys.Last().GetTranslation()-Keys[0].GetTranslation())*FVector(1,1,0);
    TArray<FVector> Positions,Scales;
    TArray<FQuat> Rotations;
    for (int32 Index=0;Index<Keys.Num();++Index)
    {
        Positions.Add(Keys[Index].GetTranslation()-Drift*(double(Index)/(Keys.Num()-1)));
        Rotations.Add(Keys[Index].GetRotation());
        Scales.Add(Keys[Index].GetScale3D());
    }
    const bool OK=Clip->GetController().SetBoneTrackKeys(Root,Positions,Rotations,Scales,false);
    UE_LOG(LogTemp,Display,TEXT("NURSE_INPLACE root=%s drift=%s frames=%d success=%d"),*Root.ToString(),*Drift.ToString(),Keys.Num(),OK);
    return OK;
#else
    return false;
#endif
}

bool ANurseZombie::FindTestSpawn(UObject* WorldContextObject,FVector Origin,FRotator Facing,float PreferredDistance,float Side,FVector& Location)
{
    UWorld* World=GEngine->GetWorldFromContextObject(WorldContextObject,EGetWorldErrorMode::ReturnNull);
    if (!World) return false;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(NursePlacement),false);
    for (TActorIterator<ANurseZombie> It(World);It;++It) Params.AddIgnoredActor(*It);
    for (float Distance : {PreferredDistance,350.f,250.f,450.f})
        for (float Yaw : {0.f,30.f,-30.f,60.f,-60.f,90.f,-90.f,180.f})
        {
            const FRotator Rotation(0,Facing.Yaw+Yaw,0);
            const FVector Near=Origin+Rotation.Vector()*Distance+FRotationMatrix(Rotation).GetUnitAxis(EAxis::Y)*Side;
            FHitResult Ground,Wall;
            if (!World->LineTraceSingleByChannel(Ground,Near+FVector(0,0,250),Near-FVector(0,0,600),ECC_Pawn,Params) || Ground.ImpactNormal.Z<.72f) continue;
            const FVector Candidate=Ground.ImpactPoint+FVector(0,0,96.f);
            if (FMath::Abs(Candidate.Z-Origin.Z)>75.f) continue;
            if (World->OverlapBlockingTestByChannel(Candidate,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(36.f,92.f),Params)) continue;
            if (World->LineTraceSingleByChannel(Wall,Origin+FVector(0,0,35),Candidate+FVector(0,0,35),ECC_Visibility,Params)) continue;
            // Swept capsule across the clearing avoids placement behind a low wall that sight rays clear.
            if (World->SweepSingleByChannel(Wall,Origin+FVector(0,0,15),Candidate+FVector(0,0,15),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(34.f,75.f),Params)) continue;
            Location=Candidate;
            return true;
        }
    return false;
}
