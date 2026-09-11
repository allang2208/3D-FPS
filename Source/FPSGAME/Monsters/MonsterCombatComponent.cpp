#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "NurseZombie.h"
#include "HandBrainMonster.h"
#include "PoisonMaggotMonster.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#endif
UMonsterCombatComponent::UMonsterCombatComponent(){PrimaryComponentTick.bCanEverTick=true;}
bool UMonsterCombatComponent::IsDead() const
{
 if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->State==ENurseState::Dead;
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->Dead();
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->Dead();
 return true;
}
bool UMonsterCombatComponent::IsControlled() const
{
 if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->State==ENurseState::Stagger;
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->State==EHandBrainState::Stagger;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->State==EPoisonMaggotState::Stagger;
 return false;
}
bool UMonsterCombatComponent::IsBusy() const
{
 if(IsDead()||IsControlled())return true;
 if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->State==ENurseState::Attack;
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->State==EHandBrainState::Slam||H->State==EHandBrainState::Howl;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->State==EPoisonMaggotState::Spitting;
 return false;
}
void UMonsterCombatComponent::SetTarget(APawn* P)
{
 if(auto* N=Cast<ANurseZombie>(GetOwner()))N->Target=P;
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))H->Target=P;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->SetTarget(P);
}
bool UMonsterCombatComponent::CanAttack(APawn* P) const
{
 if(!IsValid(P)||IsBusy())return false;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->CanSpit(P);
 const float D=FVector::Dist2D(P->GetActorLocation(),GetOwner()->GetActorLocation());
 if(auto* N=Cast<ANurseZombie>(GetOwner()))return D<=N->AttackRange-15&&N->Cooldown<=0&&N->CanSee(P)&&FMath::Abs(P->GetActorLocation().Z-N->GetActorLocation().Z)<90;
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->CanSee(P,H->GetActorLocation()+FVector(0,0,30))&&((D<=H->SlamTriggerRange&&H->SlamLeft<=0)||(D<=H->HowlRadius&&H->HowlLeft<=0));
 return false;
}
bool UMonsterCombatComponent::TryAttack(APawn* P)
{
 if(!GetOwner()->HasAuthority()||!CanAttack(P))return false;SetTarget(P);
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->StartSpit(P);
 if(auto* N=Cast<ANurseZombie>(GetOwner())){N->SetActorRotation(FRotator(0,(P->GetActorLocation()-N->GetActorLocation()).Rotation().Yaw,0));N->SetState(ENurseState::Attack);return true;}
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->StartAttack(!(FVector::Dist2D(P->GetActorLocation(),H->GetActorLocation())<=H->SlamTriggerRange&&H->SlamLeft<=0));
 return false;
}
void UMonsterCombatComponent::SetLocomotion(bool Moving,bool Returning)
{
 if(IsBusy())return;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner())){auto S=Moving?(Returning?EPoisonMaggotState::Returning:EPoisonMaggotState::Chase):EPoisonMaggotState::Idle;if(M->State!=S)M->SetState(S);}
 if(auto* N=Cast<ANurseZombie>(GetOwner())){auto S=Moving?ENurseState::Chase:ENurseState::Idle;if(N->State!=S)N->SetState(S);}
 if(auto* H=Cast<AHandBrainMonster>(GetOwner())){auto S=Moving?(Returning?EHandBrainState::Returning:EHandBrainState::Chase):EHandBrainState::Idle;if(H->State!=S)H->SetState(S);}
}
float UMonsterCombatComponent::AggroRange() const{if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->AggroRadius;if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->AggroRadius;if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->AggroRadius;return 0;}
float UMonsterCombatComponent::LeashRange() const{if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->LeashRadius;if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->LeashRadius;return 2400;}
float UMonsterCombatComponent::StopRange() const{if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->AttackRange*.72f;if(auto* N=Cast<ANurseZombie>(GetOwner()))return FMath::Max(40.f,N->AttackRange-30);if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->SlamTriggerRange*.65f;return 100;}
FVector UMonsterCombatComponent::Home() const{if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->Home;if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->SpawnPosition;if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->Home;return GetOwner()->GetActorLocation();}
void UMonsterCombatComponent::ReachedHome(){if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->Health=M->MaxHealth;if(auto* H=Cast<AHandBrainMonster>(GetOwner()))H->Health=H->MaxHealth;SetLocomotion(false);}
void UMonsterCombatComponent::ReceiveHit(float Damage,APawn* Attacker)
{
 if(!GetOwner()->HasAuthority()||IsDead())return;
 if(auto* Pawn=Cast<APawn>(GetOwner()))if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController()))AI->RememberDamage(Attacker);
 Poise+=Damage;SinceHit=0;const bool TriggerStun=Poise>=PoiseThreshold;
 const float Remaining=IsControlled()?FMath::Max(0.f,ReactionDuration-ReactionTime):0.f;
 bStunned=TriggerStun||(bStunned&&Remaining>0);
 if(TriggerStun)Poise=0;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->InterruptAttack(FMath::Max(Remaining,TriggerStun?StunDuration:StaggerDuration));
 if(auto* N=Cast<ANurseZombie>(GetOwner()))N->InterruptAttack(FMath::Max(Remaining,TriggerStun?StunDuration:StaggerDuration));
 else if(auto* H=Cast<AHandBrainMonster>(GetOwner())){if(TriggerStun)H->InterruptAttack(FMath::Max(Remaining,StunDuration));}
}
void UMonsterCombatComponent::BeginReaction(float Duration)
{
 ++HitReactions;ReactionTime=0;ReactionDuration=Duration;
 if(auto* C=Cast<ACharacter>(GetOwner()))
 {
  if(auto* AI=Cast<AMonsterAIController>(C->GetController())){AI->StopMovement();AI->UpdateKnowledge();}
  if(HitClip){C->GetMesh()->PlayAnimation(HitClip,false);C->GetMesh()->SetPlayRate(0);C->GetMesh()->SetPosition(0,false);}
  else {C->GetMesh()->SetPlayRate(0);UE_LOG(LogTemp,Warning,TEXT("MONSTER_HIT_CLIP_MISSING %s"),*GetOwner()->GetName());}
 }
 UE_LOG(LogTemp,Display,TEXT("MONSTER_REACTION %s duration=%.3f stun=%d"),*GetOwner()->GetName(),Duration,bStunned);
}
void UMonsterCombatComponent::FinishReaction()
{
 bStunned=false;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))if(M->State==EPoisonMaggotState::Stagger)M->SetState(EPoisonMaggotState::Recovery);
 if(auto* N=Cast<ANurseZombie>(GetOwner())){if(N->State==ENurseState::Stagger){N->State=ENurseState::Recovery;N->StateTime=0;}}
 if(auto* H=Cast<AHandBrainMonster>(GetOwner())){if(H->State==EHandBrainState::Stagger){H->State=EHandBrainState::Recovery;H->StateSeconds=0;}}
 if(auto* P=Cast<APawn>(GetOwner()))if(auto* AI=Cast<AMonsterAIController>(P->GetController()))AI->UpdateKnowledge();
}
void UMonsterCombatComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick)
{
 Super::TickComponent(Dt,Type,Tick);if(!GetOwner()->HasAuthority()||IsDead())return;
 SinceHit+=Dt;if(SinceHit>PoiseResetSeconds)Poise=0;
 if(IsControlled())
 {
  ReactionTime+=Dt;
  // Fast recoil, a held recoil pose during long stun, then recovery.
  if(HitClip)if(auto* C=Cast<ACharacter>(GetOwner()))
  {
   const float Remaining=ReactionDuration-ReactionTime;
   const float T=ReactionTime<.15f?ReactionTime:(Remaining>.4f?.15f:HitClip->GetPlayLength()-FMath::Max(0.f,Remaining));
   C->GetMesh()->SetPosition(FMath::Clamp(T,0.f,HitClip->GetPlayLength()),false);
  }
 }
}
bool UMonsterCombatComponent::AuthorHitClip(UAnimSequence* Clip,bool bHandBrain)
{
#if WITH_EDITOR
 if(!Clip||!Clip->GetPathName().StartsWith(TEXT("/Game/Monsters/AI/")))return false;
 auto* Model=Clip->GetDataModel();TArray<FName> Names;Model->GetBoneTrackNames(Names);TMap<FName,FTransform> Rest;
 for(auto Name:Names){TArray<FTransform> Keys;Model->GetBoneTrackTransforms(Name,Keys);if(Keys.Num())Rest.Add(Name,Keys[0]);}
 const auto& Skeleton=Clip->GetSkeleton()->GetReferenceSkeleton();TArray<FQuat> ComponentRotations;
 for(int32 I=0;I<Skeleton.GetNum();++I){const FTransform* Local=Rest.Find(Skeleton.GetBoneName(I));FQuat Q=Local?Local->GetRotation():Skeleton.GetRefBonePose()[I].GetRotation();const int32 Parent=Skeleton.GetParentIndex(I);ComponentRotations.Add(Parent>=0?ComponentRotations[Parent]*Q:Q);}
 auto& Ctrl=Clip->GetController();Ctrl.OpenBracket(FText::FromString(TEXT("Author directional hit recoil")),false);Ctrl.SetFrameRate(FFrameRate(30,1),false);Ctrl.SetNumberOfFrames(FFrameNumber(18),false);
 bool Changed=false;
 for(auto& Pair:Rest)
 {
  TArray<FVector> P,S;TArray<FQuat> R;
  for(int32 I=0;I<=18;++I)
  {
   float T=I/30.f;float Strength=T<.10f?T/.10f:FMath::Pow(FMath::Clamp((.6f-T)/.5f,0.f,1.f),1.5f);
   FTransform Key=Pair.Value;
   bool Joint=bHandBrain?(Pair.Key==TEXT("cranium")||Pair.Key==TEXT("neck")):(Pair.Key==TEXT("spine_01")||Pair.Key==TEXT("spine_03"));
   if(Joint){const int32 Index=Skeleton.FindBoneIndex(Pair.Key);const FVector MeshAxis=bHandBrain?FVector::RightVector:FVector::ForwardVector;const FVector LocalAxis=ComponentRotations[Index].Inverse().RotateVector(MeshAxis);Key.SetRotation(Key.GetRotation()*FQuat(LocalAxis,FMath::DegreesToRadians((bHandBrain?-7.f:12.f)*Strength)));Changed=true;}
   P.Add(Key.GetTranslation());R.Add(Key.GetRotation());S.Add(Key.GetScale3D());
  }
  Ctrl.SetBoneTrackKeys(Pair.Key,P,R,S,false);
 }
 Ctrl.CloseBracket(false);Clip->bEnableRootMotion=false;return Changed;
#else
 return false;
#endif
}
