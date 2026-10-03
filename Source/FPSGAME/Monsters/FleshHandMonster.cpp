#include "FleshHandMonster.h"
#include "FleshHandKnockdownComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterCombatTuning.h"
#include "FleshHandChargeFX.h"
#include "MonsterCombatComponent.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterAIController.h"
#include "MonsterReactionTiming.h"
#include "FatZombieAnimInstance.h"
#include "FPSCombatHealthComponent.h"
#include "HandBrainFearComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/IceWallCombat.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/DamageEvents.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/RootMotionSource.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundAttenuation.h"
#include "UObject/ConstructorHelpers.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

namespace
{
 TMap<TWeakObjectPtr<UWorld>,TArray<TWeakObjectPtr<AFleshHandMonster>>> SummonedHands;
 bool Alive(const APawn* P)
 {
  if(!IsValid(P))return false;
  const auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();return !H||!H->IsDead();
 }
 bool Attacking(EFleshHandState S){return S==EFleshHandState::Hammer||S==EFleshHandState::Slam||S==EFleshHandState::GrandSlam;}
 bool Charging(EFleshHandState S){return S==EFleshHandState::ChargeWindup||S==EFleshHandState::ChargeRush||S==EFleshHandState::ChargeRecover;}
}
UFleshHandPushComponent::UFleshHandPushComponent(){PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;}
void UFleshHandPushComponent::Apply(ACharacter* Target,FVector D,float CM)
{
 if(!Target||CM<=0)return;
 auto* C=Target->FindComponentByClass<UFleshHandPushComponent>();
 if(!C){C=NewObject<UFleshHandPushComponent>(Target);Target->AddInstanceComponent(C);C->RegisterComponent();}
 C->Direction=D.GetSafeNormal2D();C->Distance=CM;C->Age=0;C->SetComponentTickEnabled(true);
}
void UFleshHandPushComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick)
{
 Super::TickComponent(Dt,Type,Tick);auto* C=Cast<ACharacter>(GetOwner());
 if(!C||!Alive(C)){SetComponentTickEnabled(false);return;}
 auto* M=C->GetCharacterMovement();const float Before=Age/.16f;Age=FMath::Min(.16f,Age+Dt);
 const float Step=Distance*(FMath::Square(1-Before)-FMath::Square(1-Age/.16f));
 FHitResult Hit;M->SafeMoveUpdatedComponent(Direction*Step,C->GetActorQuat(),true,Hit);M->bForceNextFloorCheck=true;
 if(Hit.bBlockingHit||Age>=.16f)SetComponentTickEnabled(false);
}
AFleshHandMonster::AFleshHandMonster(const FObjectInitializer& I)
 :Super(I.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(ACharacter::CharacterMovementComponentName)
    .SetDefaultSubobjectClass<UMonsterIdleBreathingMeshComponent>(ACharacter::MeshComponentName))
{
 PrimaryActorTick.bCanEverTick=true;
 Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
 Status=CreateDefaultSubobject<UCombatStatusFormula>(TEXT("CombatStatus"));
 Knockdown=CreateDefaultSubobject<UFleshHandKnockdownComponent>(TEXT("HandKnockdown"));
 CorpseRagdoll=CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
 CorpseRagdoll->Rig=EMonsterCorpseRig::FleshHand;
 AIControllerClass=AMonsterAIController::StaticClass();AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
 bUseControllerRotationYaw=false;GetCapsuleComponent()->InitCapsuleSize(62,102);
 GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
 GetMesh()->SetRelativeLocation(FVector(0,0,-102));GetMesh()->SetRelativeRotation(FRotator(0,-90,0));GetMesh()->SetRelativeScale3D(FVector(2));
 GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
 GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
 GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
 GetMesh()->bEnableUpdateRateOptimizations=true;
 auto* M=GetCharacterMovement();M->bOrientRotationToMovement=true;M->RotationRate=FRotator(0,240,0);
 M->bRunPhysicsWithNoController=true;M->MaxStepHeight=40;M->bCanWalkOffLedges=false;
 PalmFist=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PalmFist"));PalmFist->SetupAttachment(GetRootComponent());
 PalmFist->SetCollisionEnabled(ECollisionEnabled::NoCollision);PalmFist->SetVisibility(false);
 PalmFist->SetRelativeLocation(FVector(5,0,-22));PalmFist->SetRelativeRotation(FRotator(0,-90,0));
 WarningRing=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("AttackWarning"));WarningRing->SetupAttachment(GetRootComponent());
 WarningRing->SetCollisionEnabled(ECollisionEnabled::NoCollision);WarningRing->SetCastShadow(false);WarningRing->SetVisibility(false);
 static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
 if(Plane.Succeeded())WarningRing->SetStaticMesh(Plane.Object);
 Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("FleshHand"));
}
AFleshHandMinion::AFleshHandMinion(const FObjectInitializer& I):Super(I)
{
 bMinion=true;MaxHealth=Health=80;PhysicalAttack=20;MagicDefense=55;Level=1;Rank=EMonsterRank::Normal;ExperienceReward=0;
 WalkSpeed=324;AnimationWalkSpeed=270;AggroRadius=945;CorpseSeconds=4;
 Knockdown->LaunchScale=1.f;Knockdown->GroundHoldSeconds=.45f;Knockdown->FallCollisionRadius=47.f;
 GetCapsuleComponent()->InitCapsuleSize(26,38);GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
 GetMesh()->SetRelativeLocation(FVector(0,0,-38));GetMesh()->SetRelativeScale3D(FVector(.65));
 auto* M=GetCharacterMovement();M->SetUpdateNavAgentWithOwnersCollisions(false);
 M->GetNavAgentPropertiesRef().AgentRadius=34;M->GetNavAgentPropertiesRef().AgentHeight=184;
 Tags.Add(TEXT("Summoned"));Tags.Add(TEXT("NoSkillTraining"));Tags.Add(TEXT("NoKillRewards"));
}
void AFleshHandMonster::OnConstruction(const FTransform& T)
{
 Super::OnConstruction(T);if(VisualMesh)GetMesh()->SetSkeletalMeshAsset(VisualMesh);if(PalmFistMesh)PalmFist->SetStaticMesh(PalmFistMesh);
 PalmFist->SetRelativeRotation(GetMesh()->GetRelativeRotation());
}
void AFleshHandMonster::BeginPlay()
{
 Super::BeginPlay();MaxHealth*=MonsterCoreStats::HealthMultiplier();Health=MaxHealth;Home=GetActorLocation();
 if(VisualMesh)GetMesh()->SetSkeletalMeshAsset(VisualMesh);
 GetMesh()->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
 GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;
 if(PalmFistMesh)PalmFist->SetStaticMesh(PalmFistMesh);
 PalmFist->SetRelativeRotation(GetMesh()->GetRelativeRotation());
 if(WarningMaterial){RingMID=UMaterialInstanceDynamic::Create(WarningMaterial,this);WarningRing->SetMaterial(0,RingMID);}
 if(!bMinion&&ChargeWarningMaterial)ChargeRingMID=UMaterialInstanceDynamic::Create(ChargeWarningMaterial,this);
 if(bMinion)
 {
  GetMesh()->SetForcedLOD(3);
  // The dungeon director sets this tag before FinishSpawning / BeginPlay.
  // An encounter member must not expire and silently complete its spawn slot.
  if(ActorHasTag(TEXT("DungeonSpawned")))
  {
   SetLifeSpan(0);
   Tags.Remove(TEXT("Summoned"));Tags.Remove(TEXT("NoSkillTraining"));Tags.Remove(TEXT("NoKillRewards"));
   // Natural dungeon members participate in kill registration and progression.
   // Keep any authored reward override; the summon class otherwise defaults to zero.
   if(ExperienceReward<=0)ExperienceReward=20;
  }
  else SetLifeSpan(90);
 }
 SetState(EFleshHandState::Idle);
}
void AFleshHandMonster::EndPlay(const EEndPlayReason::Type Reason)
{
 if(auto* FX=GetWorld()->GetSubsystem<UFleshHandChargeFX>())FX->Cancel(this);
 StopChargeMotion();
 for(auto& Child:Children)if(Child.IsValid())Child->Destroy();Children.Empty();
 if(auto* Hands=SummonedHands.Find(GetWorld())){Hands->RemoveAll([this](const auto& P){return !P.IsValid()||P.Get()==this;});if(Hands->IsEmpty())SummonedHands.Remove(GetWorld());}
 Super::EndPlay(Reason);
}
void AFleshHandMonster::Play(UAnimSequence* Clip,bool Loop,bool Clock,float Blend)
{if(Clip)if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->TransitionTo(Clip,Loop,Clock,Blend);}
bool AFleshHandMonster::Busy() const {return Dead()||State==EFleshHandState::KnockedDown||State==EFleshHandState::Stagger||State==EFleshHandState::Telegraph||Attacking(State)||Charging(State);}
void AFleshHandMonster::SetState(EFleshHandState Next)
{
 const auto Previous=State;
 if(State==EFleshHandState::ChargeRush&&Next!=State)StopChargeMotion();
 State=Next;StateSeconds=0;PalmFist->SetVisibility(false);WarningRing->SetVisibility(false);
 if(RingMID)WarningRing->SetMaterial(0,RingMID);
 if(auto* FX=GetWorld()->GetSubsystem<UFleshHandChargeFX>())FX->Transition(this,Previous);
 const bool Moving=Next==EFleshHandState::Walk||Next==EFleshHandState::Returning;
 const bool WasMoving=Previous==EFleshHandState::Walk||Previous==EFleshHandState::Returning;
 if(!Moving)GetCharacterMovement()->StopMovementImmediately();
 GetCharacterMovement()->bOrientRotationToMovement=!Busy();
 // Chase/home share one gait. Keep the visible cycle and its speed on that switch.
 if(Moving&&WasMoving)return;
 if(Next==EFleshHandState::Stagger||Next==EFleshHandState::Corpse||Next==EFleshHandState::KnockedDown)return;
 if(Charging(Next))
 {
  Play(Next==EFleshHandState::ChargeWindup?ChargeWindupClip:Next==EFleshHandState::ChargeRush?ChargeRushClip:ChargeRecoverClip,Next==EFleshHandState::ChargeRush,true,.08f);
  if(Next==EFleshHandState::ChargeWindup&&RingMID)
  {
   // A windup indicator under the hand, not an area-damage decal.
   WarningRing->SetRelativeLocation(FVector(0,0,-GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3));
   WarningRing->SetRelativeScale3D(FVector(1.65f,1.65f,1));
   RingMID->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.24f,.015f));
   RingMID->SetScalarParameterValue(TEXT("Opacity"),.8f);WarningRing->SetVisibility(true);
   if(ChargeRingMID){WarningRing->SetMaterial(0,ChargeRingMID);ChargeRingMID->SetScalarParameterValue(TEXT("Progress"),0);}
  }
  return;
 }
 UAnimSequence* Clip=Next==EFleshHandState::Hammer?HammerClip:Next==EFleshHandState::Slam?SlamClip:Next==EFleshHandState::GrandSlam?GrandSlamClip:Next==EFleshHandState::Dying?DeathClip:Moving?MoveClip:IdleClip;
 if(Moving||Next==EFleshHandState::Idle)
 {
  if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
  {
   FMonsterClipTransition Settings;Settings.bContinueOutgoingLoop=WasMoving||Previous==EFleshHandState::Idle;
   Settings.InitialPlayRate=Moving?FMath::Clamp(GetVelocity().Size2D()/FMath::Max(1.f,AnimationWalkSpeed),.15f,1.8f):1.f;
   A->TransitionTo(Clip,true,false,Moving?(bMinion?.14f:.20f):(bMinion?.18f:.24f),Settings);
  }
  return;
 }
 Play(Clip,!Attacking(Next)&&Next!=EFleshHandState::Dying,Attacking(Next)||Next==EFleshHandState::Dying,Attacking(Next)?.04f:.12f);
 if(Next==EFleshHandState::Telegraph&&RingMID)
 {
  const float Radius=Queued==EFleshHandState::Hammer?HammerRange:SlamRadius;
  WarningRing->SetRelativeLocation(FVector(0,0,-GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3));
  WarningRing->SetRelativeScale3D(FVector(Radius*.02f,Radius*.02f,1));
  RingMID->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.08f,.025f));RingMID->SetScalarParameterValue(TEXT("Opacity"),.7f);WarningRing->SetVisibility(true);
 }
}
void AFleshHandMonster::SetLocomotion(bool Moving,bool Returning)
{if(Busy())return;const auto Next=Moving?(Returning?EFleshHandState::Returning:EFleshHandState::Walk):EFleshHandState::Idle;if(State!=Next)SetState(Next);}
bool AFleshHandMonster::CanReach(const APawn* P,float Range) const
{
 if(!Alive(P)||FVector::DistSquared2D(GetActorLocation(),P->GetActorLocation())>FMath::Square(Range))return false;
 const float Feet=GetActorLocation().Z-GetSimpleCollisionHalfHeight();
 if(FMath::Abs(P->GetActorLocation().Z-P->GetSimpleCollisionHalfHeight()-Feet)>75)return false;
 FCollisionQueryParams Q(SCENE_QUERY_STAT(FleshHandSight),false,this);Q.AddIgnoredActor(P);FHitResult Hit;
 return !GetWorld()->LineTraceSingleByChannel(Hit,FVector(GetActorLocation().X,GetActorLocation().Y,Feet+40),FVector(P->GetActorLocation().X,P->GetActorLocation().Y,Feet+40),ECC_Visibility,Q);
}
bool AFleshHandMonster::CanAttack(APawn* P) const
{
 if(bMinion||Busy()||Status->IsFrozen()||Status->IsPetrified()||Status->IsStunned())return false;
 if((GrandLeft<=0||SlamLeft<=0)&&IceWallCombat::BlockingWall(this,P,SlamRadius))return true;
 // Palm-extension Hammer is retired. Only slams and the ranged fist rush can start.
 return ((GrandLeft<=0||SlamLeft<=0)&&CanReach(P,SlamRadius))||CanCharge(P);
}
bool AFleshHandMonster::CanCharge(const APawn* P) const
{
 return ChargeLeft<=0&&ChargeWindupClip&&ChargeRushClip&&ChargeRecoverClip&&!Status->BlocksMovement()&&GetCharacterMovement()->IsMovingOnGround()
  &&Alive(P)&&FVector::DistSquared2D(P->GetActorLocation(),GetActorLocation())>=FMath::Square(ChargeMinRange)&&CanReach(P,ChargeMaxRange);
}
bool AFleshHandMonster::StartAttack(APawn* P)
{
 if(!HasAuthority()||!CanAttack(P))return false;
 const bool AttackWall=IceWallCombat::BlockingWall(this,P,SlamRadius)!=nullptr;
 Queued=GrandLeft<=0&&(AttackWall||CanReach(P,SlamRadius))?EFleshHandState::GrandSlam:
  SlamLeft<=0&&(AttackWall||CanReach(P,SlamRadius))?EFleshHandState::Slam:EFleshHandState::ChargeWindup;
 Target=LockedTarget=P;StrikeDirection=(P->GetActorLocation()-GetActorLocation()).GetSafeNormal2D();
 SetActorRotation(StrikeDirection.Rotation());if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->StopMovement();
 bConsumed=false;
 if(Queued==EFleshHandState::ChargeWindup){ChargeLeft=ChargeCooldown;SetState(Queued);}
 else SetState(EFleshHandState::Telegraph);
 return true;
}
void AFleshHandMonster::StopChargeMotion()
{
 if(ChargeMotionID){GetCharacterMovement()->RemoveRootMotionSourceByID(ChargeMotionID);ChargeMotionID=0;GetCharacterMovement()->StopMovementImmediately();}
}
bool AFleshHandMonster::BuildChargeDirection(const APawn* Victim,FVector& Direction) const
{
 Direction=FVector::ZeroVector;
 if(!CanReach(Victim,ChargeDistance))return false;
 const FVector Start=GetActorLocation(),TargetPosition=Victim->GetActorLocation();
 const auto* Capsule=GetCapsuleComponent();const auto* Move=GetCharacterMovement();
 const float HalfHeight=Capsule->GetScaledCapsuleHalfHeight();
 const auto* TargetCharacter=Cast<ACharacter>(Victim);
 const auto* TargetCapsule=TargetCharacter?TargetCharacter->GetCapsuleComponent():nullptr;
 const double ContactRadius=Capsule->GetScaledCapsuleRadius()+(TargetCapsule?TargetCapsule->GetScaledCapsuleRadius():0.f);
 const double Speed=ChargeSpeed*FMath::Clamp(Status->MovementMultiplier(),0.f,1.f);
 if(Speed<=KINDA_SMALL_NUMBER)return false;
 const double MaxTime=ChargeDistance/FMath::Max(1.f,ChargeSpeed);
 FVector Offset=TargetPosition-Start;Offset.Z=0;
 FVector Velocity=Victim->GetVelocity();Velocity.Z=0;
 Velocity*=FMath::Clamp(ChargeLeadStrength,0.f,1.5f);
 // Mutant3 resamples at takeoff, using only the remaining travel time. Here
 // speed is fixed, so solve |Offset + Velocity*t| = Speed*t + contact radius.
 // The 1.2 s windup has already elapsed and must not be added a second time.
 double Time=FMath::Clamp((Offset.Size()-ContactRadius)/Speed,0.,MaxTime);
 const double A=Velocity.SizeSquared()-Speed*Speed;
 const double B=2.*(FVector::DotProduct(Offset,Velocity)-Speed*ContactRadius);
 const double C=FMath::Max(0.,Offset.SizeSquared()-ContactRadius*ContactRadius);
 if(C>KINDA_SMALL_NUMBER)
 {
  if(FMath::Abs(A)>KINDA_SMALL_NUMBER)
  {
   const double Discriminant=B*B-4.*A*C;
   if(Discriminant>=0.)
   {
    const double Root=FMath::Sqrt(Discriminant),T0=(-B-Root)/(2.*A),T1=(-B+Root)/(2.*A);
    if(T0>0.||T1>0.)Time=FMath::Clamp(T0>0.&&T1>0.?FMath::Min(T0,T1):FMath::Max(T0,T1),0.,MaxTime);
   }
  }
  else if(B<-KINDA_SMALL_NUMBER)Time=FMath::Clamp(-C/B,0.,MaxTime);
 }
 FVector Lead=(Velocity*Time).GetClampedToMaxSize(FMath::Max(0.f,ChargeMaxLeadDistance));
 FCollisionQueryParams Params(SCENE_QUERY_STAT(FleshHandChargeLead),false,this);Params.AddIgnoredActor(Victim);
 // As in Mutant3, stop the player's forecast at a wall their capsule cannot cross.
 if(TargetCapsule&&!Lead.IsNearlyZero(1.f))
 {
  FHitResult Obstacle;
  const FCollisionShape Shape=FCollisionShape::MakeCapsule(TargetCapsule->GetScaledCapsuleRadius(),FMath::Max(TargetCapsule->GetScaledCapsuleRadius(),TargetCapsule->GetScaledCapsuleHalfHeight()-2.f));
  if(GetWorld()->SweepSingleByChannel(Obstacle,TargetPosition,TargetPosition+Lead,FQuat::Identity,TargetCapsule->GetCollisionObjectType(),Shape,Params,FCollisionResponseParams(TargetCapsule->GetCollisionResponseToChannels())))
   Lead*=FMath::Max(0.f,Obstacle.Time-.02f);
 }
 const FCollisionShape Shape=FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),FMath::Max(Capsule->GetScaledCapsuleRadius(),HalfHeight-2.f));
 const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
 const int32 Candidates=Lead.IsNearlyZero(1.f)?1:3;
 for(int32 Candidate=0;Candidate<Candidates;++Candidate)
 {
  const FVector Aim=TargetPosition+Lead*(1.f-.5f*Candidate);
  FVector Planar=Aim-Start;Planar.Z=0;
  if(Planar.IsNearlyZero(1.f)||Planar.Size()-ContactRadius>Speed*MaxTime)continue;
  FHitResult Floor;
  if(!GetWorld()->LineTraceSingleByChannel(Floor,Aim+FVector(0,0,120),Aim-FVector(0,0,350),ECC_Visibility,Params)||!Move->IsWalkable(Floor))continue;
  if(FMath::Abs(Floor.ImpactPoint.Z-(Start.Z-HalfHeight))>75.f)continue;
  // This is a ground rush, not the mutant's parabolic flight. Check the hand's
  // straight capsule corridor once at launch; CharacterMovement owns actual motion.
  const FVector End=Floor.ImpactPoint+FVector(0,0,HalfHeight+2.f);FHitResult Obstacle;
  if(GetWorld()->SweepSingleByChannel(Obstacle,Start,End,FQuat::Identity,Capsule->GetCollisionObjectType(),Shape,Params,Response))continue;
  Direction=Planar.GetSafeNormal();return true;
 }
 return false;
}
void AFleshHandMonster::BeginChargeRush()
{
 FVector Direction;
 if(!BuildChargeDirection(LockedTarget.Get(),Direction)){bConsumed=true;SetState(EFleshHandState::ChargeRecover);return;}
 StrikeDirection=Direction;SetActorRotation(StrikeDirection.Rotation());
 SetState(EFleshHandState::ChargeRush);ChargeStart=ChargePrevious=GetActorLocation();ChargeBlockedSeconds=0;
 // In-place animation owns the fist pose; CharacterMovement owns swept motion,
 // floor following, steps and ledges. AI StopMovement cannot erase this source.
 auto Motion=MakeShared<FRootMotionSource_ConstantForce>();
 Motion->InstanceName=TEXT("FleshHandCharge");Motion->Priority=500;Motion->AccumulateMode=ERootMotionAccumulateMode::Override;
 Motion->Duration=ChargeDistance/FMath::Max(1.f,ChargeSpeed);Motion->bInLocalSpace=false;
 Motion->Force=StrikeDirection*ChargeSpeed*FMath::Min(1.f,Status->MovementMultiplier());
 Motion->Settings.SetFlag(ERootMotionSourceSettingsFlags::IgnoreZAccumulate);
 Motion->FinishVelocityParams.Mode=ERootMotionFinishVelocityMode::ClampVelocity;Motion->FinishVelocityParams.ClampVelocity=0;
 ChargeMotionID=GetCharacterMovement()->ApplyRootMotionSource(Motion);
 if(!ChargeMotionID)SetState(EFleshHandState::ChargeRecover);
}
void AFleshHandMonster::TickCharge(float Dt)
{
 auto* Move=GetCharacterMovement();
 if(State!=EFleshHandState::ChargeRecover&&(!Alive(LockedTarget.Get())||Status->BlocksMovement()||!Move->IsMovingOnGround()))
 {bConsumed=true;SetState(EFleshHandState::ChargeRecover);return;}
 if(State==EFleshHandState::ChargeWindup)
 {
  const float Progress=FMath::Clamp(StateSeconds/FMath::Max(.1f,ChargeWindupSeconds),0.f,1.f);
  const float Pulse=.84f+.16f*FMath::Sin(2.f*PI*(2.f*Progress+2.f*Progress*Progress));
  WarningRing->SetRelativeScale3D(FVector(FMath::Lerp(2.8f,1.8f,Progress),FMath::Lerp(2.8f,1.8f,Progress),1));
  if(ChargeRingMID)ChargeRingMID->SetScalarParameterValue(TEXT("Progress"),Progress);
  else if(RingMID)RingMID->SetScalarParameterValue(TEXT("Opacity"),Pulse);
  // Follow the live target during windup, then commit the predicted intercept
  // heading once at launch, matching Mutant3's windup/takeoff separation.
  const FRotator Facing(0,(LockedTarget->GetActorLocation()-GetActorLocation()).Rotation().Yaw,0);
  SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(),Facing,Dt,540.f));
  if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->SetCombatTime(ChargeWindupClip->GetPlayLength()*FMath::Clamp(StateSeconds/FMath::Max(.1f,ChargeWindupSeconds),0.f,1.f));
  if(StateSeconds>=ChargeWindupSeconds)BeginChargeRush();
  return;
 }
 if(State==EFleshHandState::ChargeRush)
 {
  if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->SetCombatTime(FMath::Fmod(StateSeconds,FMath::Max(.01f,ChargeRushClip->GetPlayLength())));
  if(auto Motion=Move->GetRootMotionSourceByID(ChargeMotionID))
   StaticCastSharedPtr<FRootMotionSource_ConstantForce>(Motion)->Force=StrikeDirection*ChargeSpeed*FMath::Min(1.f,Status->MovementMultiplier());
  const float Progress=FVector::DotProduct(GetActorLocation()-ChargePrevious,StrikeDirection);
  ChargeBlockedSeconds=Progress<FMath::Max(.01f,ChargeSpeed*Dt*.05f)?ChargeBlockedSeconds+Dt:0.f;ChargePrevious=GetActorLocation();
  if(StateSeconds>=ChargeDistance/FMath::Max(1.f,ChargeSpeed)||FVector::DistSquared2D(ChargeStart,GetActorLocation())>=FMath::Square(ChargeDistance)||ChargeBlockedSeconds>=.15f)
  {bConsumed=true;SetState(EFleshHandState::ChargeRecover);}
  return;
 }
 if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->SetCombatTime(ChargeRecoverClip->GetPlayLength()*FMath::Clamp(StateSeconds/FMath::Max(.1f,ChargeRecoverSeconds),0.f,1.f));
 if(StateSeconds>=ChargeRecoverSeconds){LockedTarget.Reset();SetState(EFleshHandState::Idle);}
}
void AFleshHandMonster::MoveBlockedBy(const FHitResult& Hit)
{
 Super::MoveBlockedBy(Hit);
 if(!HasAuthority()||State!=EFleshHandState::ChargeRush||bConsumed||Dead()||GetCharacterMovement()->IsWalkable(Hit))return;
 bConsumed=true; // The swept capsule's first blocking contact consumes this rush.
 bool DamageLanded=false;
 APawn* Victim=Cast<APawn>(Hit.GetActor());
 if(Alive(Victim)&&Victim->IsPlayerControlled()&&!Status->BlocksMovement())
 {
  const float Applied=UGameplayStatics::ApplyDamage(Victim,PhysicalAttack*ChargeDamageMultiplier,GetController(),this,UEnemyMeleeDamage::StaticClass());
  // Parry, stun or death may synchronously interrupt us inside ApplyDamage.
  if(State!=EFleshHandState::ChargeRush||Dead())return;
  DamageLanded=Applied>0;
  if(Applied>0&&Alive(Victim))UCombatStatusFormula::GetOrAdd(Victim)->AddStun(ChargeStunSeconds);
 }
 if(auto* FX=GetWorld()->GetSubsystem<UFleshHandChargeFX>())FX->Impact(this,Hit,DamageLanded);
 if(ImpactSound)
 {
  auto* Attenuation=NewObject<USoundAttenuation>(this);Attenuation->Attenuation.bAttenuate=true;Attenuation->Attenuation.bSpatialize=true;Attenuation->Attenuation.FalloffDistance=1800;
  UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Hit.ImpactPoint,.9f,.85f,0.f,Attenuation);
 }
 SetState(EFleshHandState::ChargeRecover);
}
void AFleshHandMonster::UpdateFist()
{
 const float T=StateSeconds;const float Extension=T<.1875f?FMath::SmoothStep(.085f,.1875f,T):1-FMath::SmoothStep(.92f,1.32f,T);
 const FVector PalmCenter=FMath::Lerp(GetMesh()->GetSocketLocation(TEXT("palm")),GetMesh()->GetSocketLocation(TEXT("middle_01")),.5f);
 PalmFist->SetWorldLocation(PalmCenter+GetActorForwardVector()*2.f);
 PalmFist->SetVisibility(Extension>.015f);PalmFist->SetRelativeScale3D(FVector(.85f,FMath::Max(.01f,Extension)*1.15f,.85f));
}
void AFleshHandMonster::Tick(float Dt)
{
 Super::Tick(Dt);if(!HasAuthority()||State==EFleshHandState::Corpse)return;
 StateSeconds+=Dt;
 if(Knockdown&&Knockdown->OwnsPresentation())
 {
  HammerLeft=FMath::Max(0.f,HammerLeft-Dt);SlamLeft=FMath::Max(0.f,SlamLeft-Dt);GrandLeft=FMath::Max(0.f,GrandLeft-Dt);
  ChargeLeft=FMath::Max(0.f,ChargeLeft-Dt);GetCharacterMovement()->MaxWalkSpeed=0;return;
 }
 if(Dead())
 {
  const float End=DeathClip?DeathClip->GetPlayLength():0.f;
  const float Handoff=End*MonsterCombatTuning::DeathAnimationFraction;
  if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
   A->SetCombatTime(FMath::Min(StateSeconds,CorpseRagdoll->WasAttempted()?End:Handoff));
  CorpseRagdoll->RecordDeathPose(GetMesh(),Dt);
  if(!CorpseRagdoll->WasAttempted()&&StateSeconds>=Handoff&&CorpseRagdoll->Start(GetMesh()))
  {State=EFleshHandState::Corpse;StateSeconds=0;return;}
  if(CorpseRagdoll->WasAttempted()&&StateSeconds>=End)
  {if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->HoldClipAtTime(End);CorpseRagdoll->FreezeAnimatedPose(GetMesh());State=EFleshHandState::Corpse;SetActorTickEnabled(false);}
  return;
 }
 HammerLeft=FMath::Max(0.f,HammerLeft-Dt);SlamLeft=FMath::Max(0.f,SlamLeft-Dt);GrandLeft=FMath::Max(0.f,GrandLeft-Dt);
 ChargeLeft=FMath::Max(0.f,ChargeLeft-Dt);
 GetCharacterMovement()->MaxWalkSpeed=Status->BlocksMovement()?0:WalkSpeed*Status->MovementMultiplier();
 if(State==EFleshHandState::Stagger){if(StateSeconds>=ControlSeconds&&Combat->StunSecondsRemaining()<=0&&!Status->IsFrozen()&&!Status->IsPetrified()&&!Status->IsStunned())Combat->FinishReaction();return;}
 if(const auto* Fear=FindComponentByClass<UHandBrainFearComponent>();Fear&&Fear->Stacks>0){if(Busy())InterruptAttack(Fear->GetRemainingSeconds());return;}
 if(Status->IsFrozen()||Status->IsPetrified()||Status->IsStunned()){if(Busy())InterruptAttack(.1f);return;}
 if(Charging(State)){TickCharge(Dt);return;}
 if(State==EFleshHandState::Telegraph)
 {
  if(!Alive(LockedTarget.Get())){SetState(EFleshHandState::Idle);return;}
  if(StateSeconds>=.5f)
  {
   if(Queued==EFleshHandState::GrandSlam)GrandLeft=20;else if(Queued==EFleshHandState::Slam)SlamLeft=8;else HammerLeft=4;
   SetState(Queued);
  }
  return;
 }
 if(Attacking(State))
 {
  const auto Attack=State;const float HitTime=Attack==EFleshHandState::Hammer?.1875f:Attack==EFleshHandState::Slam?.25f:2.f*5.f/19.f;
  if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->SetCombatTime(StateSeconds);
  if(Attack==EFleshHandState::Hammer)UpdateFist();
  if(!bConsumed&&StateSeconds>=HitTime){bConsumed=true;Impact();}
  if(State!=Attack)return; // Damage can synchronously parry, stun or kill the attacker.
  if(bConsumed&&RingMID&&Attack!=EFleshHandState::Hammer)
  {
   const float Pulse=FMath::Clamp((StateSeconds-HitTime)/(Attack==EFleshHandState::GrandSlam?.42f:.28f),0.f,1.f);
   const float Radius=FMath::Lerp(45.f,SlamRadius,Pulse);
   WarningRing->SetRelativeScale3D(FVector(Radius*.02f,Radius*.02f,1));
   RingMID->SetVectorParameterValue(TEXT("Tint"),FLinearColor(.36f,.6f,.16f));
   RingMID->SetScalarParameterValue(TEXT("Opacity"),(1-Pulse)*.65f);WarningRing->SetVisibility(Pulse<1);
  }
  if(StateSeconds>=(Attack==EFleshHandState::Hammer?1.5f:2.f))SetState(EFleshHandState::Idle);
  return;
 }
 if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
 {
  // Keep the authored reference speed fixed when gameplay movement is increased.
  const bool Moving=State==EFleshHandState::Walk||State==EFleshHandState::Returning;
  A->SetLocomotionRate(Moving?FMath::Clamp(GetVelocity().Size2D()/FMath::Max(1.f,AnimationWalkSpeed),.15f,1.8f):1.f);
 }
 if(bMinion){ContactLeft-=Dt;if(ContactLeft<=0){ContactLeft=.5f;ContactDamage();}}
}
void AFleshHandMonster::Impact()
{
 const auto Attack=State; // Neither slam spawns minions, even when it misses.
 if(ImpactSound)
 {
  auto* Attenuation=NewObject<USoundAttenuation>(this);Attenuation->Attenuation.bAttenuate=true;Attenuation->Attenuation.bSpatialize=true;Attenuation->Attenuation.FalloffDistance=1800;
  UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,GetActorLocation(),1.f,1.f,0.f,Attenuation);
 }
 const float WallMultiplier=Attack==EFleshHandState::Hammer?1.f:Attack==EFleshHandState::Slam?1.5f:2.f;
 if(IceWallCombat::ApplyMelee(this,LockedTarget.Get(),Attack==EFleshHandState::Hammer?HammerRange:SlamRadius,PhysicalAttack*WallMultiplier))return;
 for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
 {
  APawn* P=It->Get()?It->Get()->GetPawn().Get():nullptr;
  if(Attack==EFleshHandState::Hammer&&P!=LockedTarget.Get())continue;
  if(!CanReach(P,Attack==EFleshHandState::Hammer?HammerRange:SlamRadius))continue;
  if(Attack==EFleshHandState::Hammer&&FVector::DotProduct(StrikeDirection,(P->GetActorLocation()-GetActorLocation()).GetSafeNormal2D())<.35f)continue;
  const float Multiplier=Attack==EFleshHandState::Hammer?1.f:Attack==EFleshHandState::Slam?1.5f:2.f;
  const float Applied=UGameplayStatics::ApplyDamage(P,PhysicalAttack*Multiplier,GetController(),this,UEnemyMeleeDamage::StaticClass());
  if(State!=Attack||Dead())return;
  if(Applied<=0||!Alive(P))continue;
  if(Attack==EFleshHandState::Hammer)UFleshHandPushComponent::Apply(Cast<ACharacter>(P),StrikeDirection,101.25f);
  else
  {
   UCombatStatusFormula::GetOrAdd(P)->AddStun(1.f);
   if(Attack==EFleshHandState::Slam)
   {
    FVector Away=(P->GetActorLocation()-GetActorLocation()).GetSafeNormal2D();
    if(Away.IsNearlyZero())Away=StrikeDirection;
    UFleshHandPushComponent::Apply(Cast<ACharacter>(P),Away,SlamKnockbackDistance);
   }
  }
 }
}
void AFleshHandMonster::ContactDamage()
{
 if(IceWallCombat::ApplyMelee(this,Target.Get(),150,PhysicalAttack))return;
 for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
 {
  APawn* P=It->Get()?It->Get()->GetPawn().Get():nullptr;if(!CanReach(P,150))continue;
  const FVector D=GetActorTransform().InverseTransformPosition(P->GetActorLocation());bool Touch=false;
  for(const FVector Zone:{FVector(30,0,40.8),FVector(34.8,-31.2,26.4),FVector(34.8,31.2,26.4)})
   Touch|=FVector2D(D.X-Zone.X*1.35,D.Y-Zone.Y*1.35).SizeSquared()<=FMath::Square(Zone.Z*1.35);
  if(Touch)UGameplayStatics::ApplyDamage(P,PhysicalAttack,GetController(),this,UEnemyMeleeDamage::StaticClass());
  if(Busy())return;
 }
}
void AFleshHandMonster::Summon()
{
 if(!MinionClass)return;
 Children.RemoveAll([](const auto& P){return !P.IsValid()||P->Dead();});
 auto& Global=SummonedHands.FindOrAdd(GetWorld());Global.RemoveAll([](const auto& P){return !P.IsValid()||P->Dead();});
 auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());if(!Nav)return;
 const auto* Defaults=MinionClass->GetDefaultObject<AFleshHandMonster>();const auto& Agent=Defaults->GetCharacterMovement()->GetNavAgentPropertiesRef();
 const auto* NavData=Nav->GetNavDataForProps(Agent,GetActorLocation());if(!NavData)return;
 for(int32 N=0;N<3&&Children.Num()<9&&Global.Num()<36;++N)
 {
  for(int32 Attempt=0;Attempt<12;++Attempt)
  {
   const float Angle=FMath::FRand()*2*PI;const float Radius=Attempt<6?FMath::Sqrt(FMath::FRand())*67.5f:90.f+(Attempt-6)*24;
   FVector Near=GetActorLocation()+FVector(FMath::Cos(Angle)*Radius,FMath::Sin(Angle)*Radius,-GetSimpleCollisionHalfHeight());FNavLocation Floor;
   if(!Nav->ProjectPointToNavigation(Near,Floor,FVector(35,35,90),NavData))continue;
   FCollisionQueryParams Q(SCENE_QUERY_STAT(FleshHandSummon),false,this);FHitResult Wall;
   if(GetWorld()->LineTraceSingleByChannel(Wall,GetActorLocation(),Floor.Location+FVector(0,0,38),ECC_Visibility,Q))continue;
   const FVector At=Floor.Location+FVector(0,0,41);
   FCollisionResponseParams Responses;Responses.CollisionResponse.SetResponse(ECC_Pawn,ECR_Ignore);
   if(GetWorld()->OverlapBlockingTestByChannel(At,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(26,38),Q,Responses))continue;
   FActorSpawnParameters Params;Params.Owner=this;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   if(auto* Child=GetWorld()->SpawnActor<AFleshHandMonster>(MinionClass,At,GetActorRotation(),Params))
   {Children.Add(Child);Global.Add(Child);Child->SetTarget(Target.Get());if(auto* AI=Cast<AMonsterAIController>(Child->GetController()))AI->RememberDamage(Target.Get());}
   break;
  }
 }
}
void AFleshHandMonster::InterruptAttack(float Seconds)
{
 if(Dead())return;
 if(Knockdown&&Knockdown->IsControlling()){Knockdown->ExtendControl(Seconds);return;}
 ControlSeconds=FMath::Max(Seconds,State==EFleshHandState::Stagger?ControlSeconds-StateSeconds:0.f);
 bConsumed=true;LockedTarget.Reset();SetState(EFleshHandState::Stagger);Combat->BeginReaction(ControlSeconds);
}
void AFleshHandMonster::StartHitPresentation()
{
 bDizzyPresentation=Combat->bStunned&&!Combat->IsImmobileReaction();
 Play(bDizzyPresentation?Combat->DizzyClip:Combat->HitClip,bDizzyPresentation,true,.08f);
}
void AFleshHandMonster::SetHitPresentationTime(float Elapsed,float Remaining)
{
 const bool Dizzy=Combat->bStunned&&!Combat->IsImmobileReaction();
 if(Dizzy!=bDizzyPresentation){bDizzyPresentation=Dizzy;Play(Dizzy?Combat->DizzyClip:Combat->HitClip,Dizzy,true,.15f);}
 if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
 {
  const auto* Clip=Dizzy?Combat->DizzyClip.Get():Combat->HitClip.Get();if(!Clip)return;
  const float Time=Combat->IsImmobileReaction()?.12f:Dizzy?FMath::Fmod(Elapsed,Clip->GetPlayLength()):MonsterReactionTiming::StaggerSample(Elapsed,Remaining,Clip->GetPlayLength(),.12f,.12f);
  A->SetCombatTime(Time);A->SetControlledBlendTime(Elapsed);
 }
}
void AFleshHandMonster::FinishHitReaction(){if(!Dead()&&(!Knockdown||!Knockdown->IsControlling()))SetState(EFleshHandState::Idle);}
void AFleshHandMonster::Landed(const FHitResult& Hit)
{
 Super::Landed(Hit);if(Knockdown)Knockdown->Landed(Hit);
}
float AFleshHandMonster::TakeDamage(float Damage,const FDamageEvent& Event,AController* DamageInstigator,AActor* Causer)
{
 if(!HasAuthority()||Dead()||Damage<=0)return 0;
 const auto* Type=Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():GetDefault<UDamageType>();
 auto* Weapon=CombatFormulaRuntime::ActiveWeaponHit;
 // Source classification belongs to the attack receipt; gun-butt and sword hits remain melee.
 const bool Ranged=Weapon&&Weapon->Target==this?!Weapon->bMelee:
  ((Event.IsOfType(FPointDamageEvent::ClassID)||Event.IsOfType(FRadialDamageEvent::ClassID)||CombatFormulaRuntime::IsMagic(Type))&&!Type->IsA<UStatusMagicDamage>()&&!Type->IsA<UCombatDirectDamage>());
 const float Mult=bMinion&&Ranged?.5f:1.f;
 const FWeaponDamageParts Original=Weapon?Weapon->Incoming:FWeaponDamageParts{};
 if(Weapon&&Weapon->Target==this)Weapon->Incoming=Weapon->Incoming.Scaled(Mult);
 float Applied=CombatFormulaRuntime::MitigateMonster(this,Damage*Mult,Type,DamageInstigator?DamageInstigator->GetPawn().Get():Causer);
 if(Weapon)Weapon->Incoming=Original;
 if(UDevelopmentTuningSubsystem::ShouldOneHitKill(this,DamageInstigator,Causer))Applied=Health;
 Applied=FMath::Clamp(Applied,0.f,Health);if(Applied<=0)return 0;Health-=Applied;
 Super::TakeDamage(Applied,Event,DamageInstigator,Causer);
 if(Health<=0)
 {
  bConsumed=true;LockedTarget.Reset();Target.Reset();
  CorpseRagdoll->PrepareDeath(GetMesh());
  const bool FallingCorpse=Knockdown&&Knockdown->OnDeath();
  if(CorpseRagdoll->SimulatedBodyCount()>0)
  {State=EFleshHandState::Corpse;StateSeconds=0;GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);GetCharacterMovement()->DisableMovement();}
  else if(FallingCorpse){State=EFleshHandState::Dying;StateSeconds=0;GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);}
  else {SetState(EFleshHandState::Dying);GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);GetCharacterMovement()->DisableMovement();}
  if(CorpseRagdoll->SimulatedBodyCount()==0)GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
  Combat->SetComponentTickEnabled(false);Status->SetComponentTickEnabled(false);
  if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->SetDecisionEnabled(false);AI->UpdateKnowledge();}
  SetLifeSpan(CorpseSeconds);
  if(!bMinion||ActorHasTag(TEXT("DungeonSpawned")))if(auto* PC=Cast<APlayerController>(DamageInstigator);PC&&PC->IsLocalController()&&GetGameInstance())GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);
 }
 else Combat->ReceiveHit(Applied,DamageInstigator?DamageInstigator->GetPawn().Get():Cast<APawn>(Causer),MonsterToughness::FormOf(Type));
 return Applied;
}
bool AFleshHandMonster::BuildQueryPhysics(USkeletalMesh* Mesh,UPhysicsAsset* Asset)
{
#if WITH_EDITOR
 if(!Mesh||!Asset)return false;
 Asset->Modify();Asset->SkeletalBodySetups.Empty();Asset->ConstraintSetup.Empty();Asset->CollisionDisableTable.Empty();
 const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> CS=Ref.GetRefBonePose();
 for(int32 I=0;I<CS.Num();++I)if(Ref.GetParentIndex(I)>=0)CS[I]=CS[I]*CS[Ref.GetParentIndex(I)];
 TArray<TArray<FVector>> Points;Points.SetNum(CS.Num());
 if(auto* Model=Mesh->GetImportedModel();Model&&Model->LODModels.Num())
 for(const auto& Section:Model->LODModels[0].Sections)for(const auto& Vertex:Section.SoftVertices)
 {
  int32 Best=0;for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(Vertex.InfluenceWeights[J]>Vertex.InfluenceWeights[Best])Best=J;
  const int32 Bone=Section.BoneMap[Vertex.InfluenceBones[Best]];Points[Bone].Add(CS[Bone].InverseTransformPosition(FVector(Vertex.Position)));
 }
 for(int32 I=0;I<Points.Num();++I)if(Points[I].Num()>8)
 {
  auto* Body=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional);Body->BoneName=Ref.GetBoneName(I);
  Body->PhysicsType=PhysType_Kinematic;Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
  FKConvexElem Hull;Hull.VertexData=Points[I];Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(Hull);
  Body->CreatePhysicsMeshes();Asset->SkeletalBodySetups.Add(Body);
 }
 for(int32 I=0;I<Asset->SkeletalBodySetups.Num();++I)for(int32 J=I+1;J<Asset->SkeletalBodySetups.Num();++J)Asset->DisableCollision(I,J);
 for(int32 L=0;L<Mesh->GetLODNum();++L)if(auto* Info=Mesh->GetLODInfo(L)){Info->ScreenSize.Default=L==0?1.f:L==1?.42f:.16f;Info->LODHysteresis=.025f;}
 Asset->UpdateBodySetupIndexMap();Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();Mesh->SetPhysicsAsset(Asset);Mesh->MarkPackageDirty();return true;
#else
 return false;
#endif
}
