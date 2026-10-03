#include "FleshHandKnockdownComponent.h"
#include "FleshHandMonster.h"
#include "MonsterCorpseRagdollComponent.h"
#include "FatZombieAnimInstance.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "../Combat/CombatStatusFormula.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

UFleshHandKnockdownComponent::UFleshHandKnockdownComponent()
{
 PrimaryComponentTick.bCanEverTick=true;
 PrimaryComponentTick.bStartWithTickEnabled=false;
 PrimaryComponentTick.TickGroup=TG_PrePhysics;
}
AFleshHandMonster* UFleshHandKnockdownComponent::Hand() const {return Cast<AFleshHandMonster>(GetOwner());}
void UFleshHandKnockdownComponent::BeginPlay()
{
 Super::BeginPlay();
 if(auto* H=Hand())
 {
  AddTickPrerequisiteComponent(H->GetCharacterMovement());
  H->GetMesh()->AddTickPrerequisiteComponent(this);
 }
}
bool UFleshHandKnockdownComponent::CapsuleFits(float Radius,float HalfHeight,const FVector& Center) const
{
 const auto* H=Hand();const auto* C=H->GetCapsuleComponent();const float Scale=C->GetShapeScale();
 FCollisionQueryParams Q(SCENE_QUERY_STAT(FleshHandRecoverySpace),false,H);
 FCollisionResponseParams Responses(C->GetCollisionResponseToChannels());
 // The movement capsule owns pawn blocking separately; recovery clearance is world geometry.
 Responses.CollisionResponse.SetResponse(ECC_Pawn,ECR_Ignore);
 return !GetWorld()->OverlapBlockingTestByChannel(Center+FVector(0,0,1),H->GetActorQuat(),C->GetCollisionObjectType(),
  FCollisionShape::MakeCapsule(FMath::Max(1.f,Radius*Scale-.5f),FMath::Max(1.f,HalfHeight*Scale-.5f)),Q,Responses);
}
bool UFleshHandKnockdownComponent::Launch(APawn* Attacker,FVector Velocity,float DownSeconds)
{
 auto* H=Hand();
 if(!H||!H->HasAuthority()||H->Dead()||!bEnabled||Velocity.ContainsNaN()||Velocity.Z<=0||
    H->ActorHasTag(TEXT("KnockdownImmune"))||H->ActorHasTag(TEXT("KnockbackImmune")))return false;
 if(IsControlling())
 {
  ExtendControl(DownSeconds);
  // A fresh heavy launch can knock an emerging hand back down, but repeated
  // hits while airborne/down never restart an endless launch animation.
  if(Phase==EFleshHandKnockdownPhase::GettingUp)
  {
   if(!bPalmDown&&PhaseTime>PlayingClip->GetPlayLength()*.5f)bPalmDown=true;
   DownHold=FMath::Max(GroundHoldSeconds,FMath::Max(0.f,DownSeconds));
   PlayPhase(EFleshHandKnockdownPhase::Landing,bPalmDown?LandPalmClip:LandBackClip);
  }
  return true;
 }
 if(!LaunchPalmClip||!LaunchBackClip||!AirPalmClip||!AirBackClip||!LandPalmClip||!LandBackClip||
    !DownPalmClip||!DownBackClip||!GetUpPalmClip||!GetUpBackClip)return false;
 auto* C=H->GetCapsuleComponent();auto* M=H->GetCharacterMovement();
 StandingRadius=C->GetUnscaledCapsuleRadius();StandingHalfHeight=C->GetUnscaledCapsuleHalfHeight();
 const float Radius=FMath::Max(StandingRadius,FallCollisionRadius);
 const float HalfHeight=FMath::Max(StandingHalfHeight,Radius);
 AddedHalfHeight=HalfHeight-StandingHalfHeight;
 const FVector At=H->GetActorLocation()+FVector(0,0,AddedHalfHeight*C->GetShapeScale());
 // A wider single capsule contains the flat hand. Tight spaces retain the caller's push fallback.
 if(!CapsuleFits(Radius,HalfHeight,At))return false;
 StandingRotation=H->GetMesh()->GetRelativeRotation().Quaternion();GroundRotation=StandingRotation;
 StandingAirControl=M->AirControl;bAutoOrient=M->bOrientRotationToMovement;
 StandingPawnResponse=C->GetCollisionResponseToChannel(ECC_Pawn);
 bUpdateNavAgent=M->ShouldUpdateNavAgentWithOwnersCollision();
 DownHold=FMath::Max(GroundHoldSeconds,FMath::Max(0.f,DownSeconds));
 ControlUntil=GetWorld()->GetTimeSeconds()+H->Combat->StunSecondsRemaining();
 bPalmDown=FVector::DotProduct(Velocity.GetSafeNormal2D(),H->GetActorForwardVector())>=0;
 bCorpse=false;
 H->bConsumed=true;H->LockedTarget.Reset();H->SetState(EFleshHandState::KnockedDown);
 M->SetUpdateNavAgentWithOwnersCollisions(false);M->AirControl=0;M->bOrientRotationToMovement=false;
 C->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
 C->SetCapsuleSize(Radius,HalfHeight,false);
 H->SetActorLocation(At,false,nullptr,ETeleportType::TeleportPhysics);
 H->GetMesh()->SetRelativeLocation(H->GetMesh()->GetRelativeLocation()-FVector(0,0,AddedHalfHeight));
 if(auto* AI=Cast<AMonsterAIController>(H->GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
 PlayPhase(EFleshHandKnockdownPhase::Launch,bPalmDown?LaunchPalmClip:LaunchBackClip);
 Velocity*=FMath::Clamp(LaunchScale,.1f,1.5f);
 const FVector Horizontal=FVector(Velocity.X,Velocity.Y,0).GetClampedToMaxSize(800);
 H->LaunchCharacter(Horizontal+FVector(0,0,FMath::Clamp(Velocity.Z,120.,600.)),true,true);
 SetComponentTickEnabled(true);
 if(auto* AI=Cast<AMonsterAIController>(H->GetController()))AI->UpdateKnowledge();
 return true;
}
void UFleshHandKnockdownComponent::PlayPhase(EFleshHandKnockdownPhase Next,UAnimSequence* Clip,bool Loop)
{
 Phase=Next;PhaseTime=BlendTime=0;PlayingClip=Clip;
 if(auto* A=Cast<UFatZombieAnimInstance>(Hand()->GetMesh()->GetAnimInstance()))
 {
  FMonsterClipTransition Settings;Settings.StartTime=0;
  A->TransitionTo(Clip,Loop,true,Next==EFleshHandKnockdownPhase::Landing?.08f:.10f,Settings);
 }
}
void UFleshHandKnockdownComponent::ExtendControl(float Seconds)
{
 if(IsControlling())ControlUntil=FMath::Max(ControlUntil,double(GetWorld()->GetTimeSeconds())+FMath::Max(0.f,Seconds));
}
void UFleshHandKnockdownComponent::Landed(const FHitResult& Hit)
{
 if(Phase!=EFleshHandKnockdownPhase::Launch&&Phase!=EFleshHandKnockdownPhase::Airborne)return;
 auto* H=Hand();H->GetCharacterMovement()->StopMovementImmediately();
 // The CMC capsule bottom, not its center, is the authored mesh's support origin.
 const FVector LocalNormal=H->GetActorQuat().UnrotateVector(Hit.ImpactNormal).GetSafeNormal();
 const FQuat Slope=FQuat::FindBetweenNormals(FVector::UpVector,LocalNormal);
 GroundRotation=Slope*StandingRotation;
 PlayPhase(EFleshHandKnockdownPhase::Landing,bPalmDown?LandPalmClip:LandBackClip);
}
bool UFleshHandKnockdownComponent::OnDeath()
{
 if(!IsControlling())return false;
 bCorpse=true;ControlUntil=0;
 auto* H=Hand();auto* Mesh=H->GetMesh();
 Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();
 // Existing capsule motion becomes one connected corpse motion. The shared
 // death component already remembers the other 40% of the launch velocity.
 if(H->CorpseRagdoll->Start(Mesh,H->GetVelocity()*.6f))
 {
  H->GetCharacterMovement()->DisableMovement();
  H->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
  Phase=EFleshHandKnockdownPhase::Corpse;SetComponentTickEnabled(false);
  return true;
 }
 if(Phase==EFleshHandKnockdownPhase::GettingUp)
 {
  if(!bPalmDown&&PhaseTime>PlayingClip->GetPlayLength()*.5f)bPalmDown=true;
  PlayPhase(EFleshHandKnockdownPhase::Landing,bPalmDown?LandPalmClip:LandBackClip);
 }
 return true; // Airborne corpses finish their physical fall before freezing on the ground.
}
void UFleshHandKnockdownComponent::FreezeCorpse()
{
 auto* H=Hand();auto* Mesh=H->GetMesh();
 if(auto* A=Cast<UFatZombieAnimInstance>(Mesh->GetAnimInstance()))
  A->HoldClipAtTime(Phase==EFleshHandKnockdownPhase::Landing?PlayingClip->GetPlayLength():PhaseTime);
 Mesh->TickAnimation(0,false);Mesh->RefreshBoneTransforms();
 H->CorpseRagdoll->FreezeAnimatedPose(Mesh);H->GetCharacterMovement()->DisableMovement();
 H->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 Phase=EFleshHandKnockdownPhase::Corpse;H->State=EFleshHandState::Corpse;H->SetActorTickEnabled(false);
 SetComponentTickEnabled(false);
}
void UFleshHandKnockdownComponent::FinishRecovery()
{
 auto* H=Hand();auto* C=H->GetCapsuleComponent();auto* M=H->GetCharacterMovement();
 const FVector At=H->GetActorLocation()-FVector(0,0,AddedHalfHeight*C->GetShapeScale());
 if(!CapsuleFits(StandingRadius,StandingHalfHeight,At)){ProbeTime=.25f;return;}
 C->SetCapsuleSize(StandingRadius,StandingHalfHeight,false);
 H->SetActorLocation(At,false,nullptr,ETeleportType::TeleportPhysics);
 H->GetMesh()->SetRelativeLocation(H->GetMesh()->GetRelativeLocation()+FVector(0,0,AddedHalfHeight));
 H->GetMesh()->SetRelativeRotation(StandingRotation);
 C->SetCollisionResponseToChannel(ECC_Pawn,StandingPawnResponse);
 M->AirControl=StandingAirControl;M->SetUpdateNavAgentWithOwnersCollisions(bUpdateNavAgent);
 M->bForceNextFloorCheck=true;
 Phase=EFleshHandKnockdownPhase::None;PlayingClip=nullptr;SetComponentTickEnabled(false);
 const float Stun=H->Combat->StunSecondsRemaining();
 H->Combat->FinishReaction();
 if(Stun>0)H->Combat->ReceiveStun(nullptr,Stun,0);
 M->bOrientRotationToMovement=bAutoOrient&&!H->Busy();
}
void UFleshHandKnockdownComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick)
{
 Super::TickComponent(Dt,Type,Tick);
 auto* H=Hand();if(!H||!H->HasAuthority()||!OwnsPresentation()||Phase==EFleshHandKnockdownPhase::Corpse)return;
 auto* M=H->GetCharacterMovement();auto* A=Cast<UFatZombieAnimInstance>(H->GetMesh()->GetAnimInstance());
 const bool Frozen=!bCorpse&&(H->Status->IsFrozen()||H->Status->IsPetrified());
 // Gravity and collision keep running while the pose/control clock is frozen.
 if(!Frozen){PhaseTime+=Dt;BlendTime+=Dt;}
 if(A&&PlayingClip)
 {
  const bool Loop=Phase==EFleshHandKnockdownPhase::Airborne||Phase==EFleshHandKnockdownPhase::Downed;
  A->SetCombatTime(Loop?FMath::Fmod(PhaseTime,PlayingClip->GetPlayLength()):PhaseTime);
  A->SetControlledBlendTime(BlendTime);
 }
 if(Phase==EFleshHandKnockdownPhase::Launch||Phase==EFleshHandKnockdownPhase::Airborne)
 {
  // ACharacter::Landed is authoritative. This also covers a movement base landing.
  if(PhaseTime>.05f&&M->IsMovingOnGround()&&M->CurrentFloor.IsWalkableFloor()){Landed(M->CurrentFloor.HitResult);return;}
  if(!Frozen&&Phase==EFleshHandKnockdownPhase::Launch&&PhaseTime>=PlayingClip->GetPlayLength())
   PlayPhase(EFleshHandKnockdownPhase::Airborne,bPalmDown?AirPalmClip:AirBackClip,true);
  return;
 }
 if(M->IsFalling())
 {
  // A destroyed/moving support may disappear during the grounded sequence.
  // Re-enter the physical fall instead of standing up in mid-air.
  H->GetMesh()->SetRelativeRotation(StandingRotation);GroundRotation=StandingRotation;
  PlayPhase(EFleshHandKnockdownPhase::Airborne,bPalmDown?AirPalmClip:AirBackClip,true);return;
 }
 const float Align=FMath::Clamp(BlendTime/.12f,0.f,1.f);
 if(Phase==EFleshHandKnockdownPhase::Landing)
  H->GetMesh()->SetRelativeRotation(FQuat::Slerp(StandingRotation,GroundRotation,Align));
 if(bCorpse&&Phase==EFleshHandKnockdownPhase::Downed){FreezeCorpse();return;}
 if(Frozen)return;
 if(Phase==EFleshHandKnockdownPhase::Landing&&PhaseTime>=PlayingClip->GetPlayLength())
 {
  if(bCorpse){FreezeCorpse();return;}
  PlayPhase(EFleshHandKnockdownPhase::Downed,bPalmDown?DownPalmClip:DownBackClip,true);
  ControlUntil=FMath::Max(ControlUntil,double(GetWorld()->GetTimeSeconds())+DownHold);ProbeTime=0;
 }
 else if(Phase==EFleshHandKnockdownPhase::Downed)
 {
  ProbeTime-=Dt;
  if(GetWorld()->GetTimeSeconds()<ControlUntil||H->Status->IsStunned()||ProbeTime>0)return;
  ProbeTime=.25f;
  const auto* C=H->GetCapsuleComponent();
  const FVector At=H->GetActorLocation()-FVector(0,0,AddedHalfHeight*C->GetShapeScale());
  if(CapsuleFits(StandingRadius,StandingHalfHeight,At))PlayPhase(EFleshHandKnockdownPhase::GettingUp,bPalmDown?GetUpPalmClip:GetUpBackClip);
 }
 else if(Phase==EFleshHandKnockdownPhase::GettingUp)
 {
  const float Fraction=FMath::Clamp(PhaseTime/PlayingClip->GetPlayLength(),0.f,1.f);
  H->GetMesh()->SetRelativeRotation(FQuat::Slerp(GroundRotation,StandingRotation,Fraction*Fraction*(3-2*Fraction)));
  ProbeTime-=Dt;
  if(Fraction>=1&&ProbeTime<=0)FinishRecovery();
 }
}
