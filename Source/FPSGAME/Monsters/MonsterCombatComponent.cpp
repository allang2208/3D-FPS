#include "MonsterCombatComponent.h"
#include "M10Mawcrawler.h"
#include "../Combat/CombatStatusFormula.h"
#include "MonsterCombatTuning.h"
#include "../Skills/IceWallCombat.h"
#include "MonsterCoreStats.h"
#include "MonsterAIController.h"
#include "NurseZombie.h"
#include "BlindSupplicantMonster.h"
#include "HumanoidKnockdownComponent.h"
#include "Mutant3.h"
#include "HandBrainMonster.h"
#include "FleshHandMonster.h"
#include "FleshHandKnockdownComponent.h"
#include "PoisonMaggotMonster.h"
#include "HundredEyedSlagMonster.h"
#include "WolfMonster.h"
#include "WitchMonster.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#endif
UMonsterCombatComponent::UMonsterCombatComponent(){PrimaryComponentTick.bCanEverTick=true;}
void UMonsterCombatComponent::BeginPlay()
{
    Super::BeginPlay();
    // 韧性走类别×阶级基准表（MonsterCoreStats，2026-09-29）：晚于地牢导演写入实例
    // Rank（SpawnDeferred 阶段先写 Rank 再 FinishSpawning→BeginPlay），覆盖构造器默认。
    MonsterCoreStats::ApplyToughnessProfile(GetOwner());
    LoadHumanoidStun();
}
bool UMonsterCombatComponent::GetVitals(float& Health,float& MaxHealth,FText& Name) const
{
 if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner())){Health=M10->Health;MaxHealth=M10->MaxHealth;Name=FText::FromString(TEXT("沉匣 M-10"));return true;}
 if(const auto* S=Cast<AHundredEyedSlagMonster>(GetOwner())){Health=S->Health;MaxHealth=S->MaxHealth;Name=FText::FromString(TEXT("百目炉渣"));return true;}
 if(const auto* F=Cast<AFleshHandMonster>(GetOwner())){Health=F->Health;MaxHealth=F->MaxHealth;Name=FText::FromString(F->bMinion?TEXT("小皮肤手"):TEXT("异变巨手"));return true;}
 if(const auto* W=Cast<AWolfMonster>(GetOwner()))
 {Health=W->Health;MaxHealth=W->MaxHealth;Name=W->MonsterDisplayName;return true;}
 if(const auto* M07=Cast<ABlindSupplicantMonster>(GetOwner()))
 {Health=M07->Health;MaxHealth=M07->MaxHealth;Name=M07->MonsterDisplayName;return true;}
 if(const auto* N=Cast<ANurseZombie>(GetOwner()))
 {Health=N->Health;MaxHealth=N->MaxHealth;Name=FText::FromString(N->ActorHasTag(TEXT("SpitterZombie"))?TEXT("毒液僵尸"):N->ActorHasTag(TEXT("Witch"))?TEXT("巫婆"):N->ActorHasTag(TEXT("Mutant3"))?TEXT("突变体-3"):N->ActorHasTag(TEXT("FatZombie"))?TEXT("胖子僵尸"):TEXT("护士僵尸"));return true;}
 if(const auto* H=Cast<AHandBrainMonster>(GetOwner()))
 {Health=H->Health;MaxHealth=H->MaxHealth;Name=FText::FromString(TEXT("手脑"));return true;}
 if(const auto* M=Cast<APoisonMaggotMonster>(GetOwner()))
 {Health=M->Health;MaxHealth=M->MaxHealth;Name=FText::FromString(TEXT("毒蛆"));return true;}
 return false;
}
bool UMonsterCombatComponent::IsDead() const
{
 if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->Dead();
 if(const auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return S->Dead();
 if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->Dead();
 if(auto* W=Cast<AWolfMonster>(GetOwner()))return W->Dead();
 if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->State==ENurseState::Dead;
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->Dead();
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->Dead();
 return true;
}
bool UMonsterCombatComponent::IsControlled() const
{
 if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->State==EM10State::Stagger;
 if(const auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return S->Controlled();
 if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->State==EFleshHandState::Stagger||IsKnockedDown();
 if(auto* W=Cast<AWolfMonster>(GetOwner()))return W->State==EWolfState::Stagger;
 if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->State==ENurseState::Stagger || (N->Knockdown && N->Knockdown->IsControlling());
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->State==EHandBrainState::Stagger;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->State==EPoisonMaggotState::Stagger;
 return false;
}
bool UMonsterCombatComponent::IsKnockedDown() const
{
 if(const auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->Knockdown&&F->Knockdown->IsControlling();
 if(const auto* N=Cast<ANurseZombie>(GetOwner()))return N->Knockdown&&N->Knockdown->IsControlling();
 return false;
}
bool UMonsterCombatComponent::IsBusy() const
{
 if(IsDead()||IsControlled())return true;
 if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->Busy();
 if(const auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return S->Busy();
 if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->Busy();
 if(auto* W=Cast<AWolfMonster>(GetOwner()))return W->Busy();
 if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->State==ENurseState::Attack;
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->State==EHandBrainState::Slam||H->State==EHandBrainState::Howl;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->State==EPoisonMaggotState::Spitting;
 return false;
}
void UMonsterCombatComponent::SetTarget(APawn* P)
{
 if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->SetTarget(P);
 if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))S->SetTarget(P);
 if(auto* F=Cast<AFleshHandMonster>(GetOwner()))F->SetTarget(P);
 if(auto* W=Cast<AWolfMonster>(GetOwner()))W->SetTarget(P);
 if(auto* N=Cast<ANurseZombie>(GetOwner()))N->Target=P;
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))H->Target=P;
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->SetTarget(P);
}
bool UMonsterCombatComponent::CanAttack(APawn* P) const
{
 if(!IsValid(P)||IsBusy())return false;
 if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->CanAttack(P);
 if(const auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return S->CanAttack(P);
 if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->CanAttack(P);
 if(auto* Witch=Cast<AWitchMonster>(GetOwner()))return Witch->CanCast(P);
 if(auto* Mutant=Cast<AMutant3>(GetOwner()))return Mutant->CanStartFeralAttack(P);
 if(auto* W=Cast<AWolfMonster>(GetOwner()))return W->CanAttack(P);
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->CanSpit(P);
 if(const auto* M07=Cast<ABlindSupplicantMonster>(GetOwner()))return M07->CanAttackTarget(P);
 const float D=FVector::Dist2D(P->GetActorLocation(),GetOwner()->GetActorLocation());
 if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->Cooldown<=0&&
  (IceWallCombat::BlockingWall(N,P,MonsterCombatTuning::AttackDistance(N->AttackRange)-15)||
   (D<=MonsterCombatTuning::AttackDistance(N->AttackRange)-15&&N->CanSee(P)&&FMath::Abs(P->GetActorLocation().Z-N->GetActorLocation().Z)<90));
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->CanSlamTarget(P)||H->CanHowlTarget(P);
 return false;
}
bool UMonsterCombatComponent::TryAttack(APawn* P)
{
 if(!GetOwner()->HasAuthority()||!CanAttack(P))return false;SetTarget(P);
 if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->StartAttack(P);
 if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return S->StartAttack(P);
 if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->StartAttack(P);
 if(auto* Mutant=Cast<AMutant3>(GetOwner()))return Mutant->StartFeralAttack(P);
 if(auto* W=Cast<AWolfMonster>(GetOwner()))return W->StartAttack(P);
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->StartSpit(P);
 if(auto* N=Cast<ANurseZombie>(GetOwner()))
 {
  if(auto* M07=Cast<ABlindSupplicantMonster>(N))if(!M07->PrepareAttack(P))return false;
  // The witch aligns before planting; rotating her actor here moves both support feet instantly.
  if(!Cast<AWitchMonster>(N))N->SetActorRotation(FRotator(0,(P->GetActorLocation()-N->GetActorLocation()).Rotation().Yaw,0));
  N->SetState(ENurseState::Attack);
  if(Cast<ABlindSupplicantMonster>(N))if(auto* AI=Cast<AMonsterAIController>(N->GetController()))AI->UpdateKnowledge();
  return true;
 }
 if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->StartAttack(!H->CanSlamTarget(P));
 return false;
}
void UMonsterCombatComponent::SetLocomotion(bool Moving,bool Returning)
{
 if(IsBusy())return;
 if(auto* M10=Cast<AM10Mawcrawler>(GetOwner())){M10->SetLocomotion(Moving,Returning);return;}
 if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner())){S->SetLocomotion(Moving,Returning);return;}
 if(auto* F=Cast<AFleshHandMonster>(GetOwner())){F->SetLocomotion(Moving,Returning);return;}
 if(auto* W=Cast<AWolfMonster>(GetOwner())){W->SetLocomotion(Moving,Returning);return;}
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner())){auto S=Moving?(Returning?EPoisonMaggotState::Returning:EPoisonMaggotState::Chase):EPoisonMaggotState::Idle;if(M->State!=S)M->SetState(S);}
 if(auto* N=Cast<ANurseZombie>(GetOwner())){auto S=Moving?ENurseState::Chase:ENurseState::Idle;if(N->State!=S)N->SetState(S);}
 if(auto* H=Cast<AHandBrainMonster>(GetOwner())){auto S=Moving?(Returning?EHandBrainState::Returning:EHandBrainState::Chase):EHandBrainState::Idle;if(H->State!=S)H->SetState(S);}
}
float UMonsterCombatComponent::AggroRange() const{if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->AggroRadius;if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return S->AggroRadius;if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->AggroRadius;if(auto* W=Cast<AWolfMonster>(GetOwner()))return W->AggroRadius;if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->AggroRadius;if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->AggroRadius;if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->AggroRadius;return 0;}
float UMonsterCombatComponent::LeashRange() const{if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->LeashRadius;if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return S->LeashRadius;if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->LeashRadius;if(auto* W=Cast<AWolfMonster>(GetOwner()))return W->LeashRadius;if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->LeashRadius;if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->LeashRadius;return 2400;}
float UMonsterCombatComponent::StopRange() const{if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->BiteTriggerRange-15.f;if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return FMath::Clamp(S->MeleeRange-35.f,80.f,155.f);if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->bMinion?5.f:F->HammerRange*.8f;if(auto* Witch=Cast<AWitchMonster>(GetOwner()))return FMath::Max(40.f,Witch->SpellRange*.75f);if(auto* W=Cast<AWolfMonster>(GetOwner()))return FMath::Max(55.f,W->BiteTriggerRange-30.f);if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return MonsterCombatTuning::AttackDistance(M->AttackRange)*.72f;if(const auto* M07=Cast<ABlindSupplicantMonster>(GetOwner()))return M07->CombatStoppingRange();if(auto* N=Cast<ANurseZombie>(GetOwner()))return FMath::Max(40.f,MonsterCombatTuning::AttackDistance(N->AttackRange)-30);if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->SlamTriggerRange*.65f;return 100;}
FVector UMonsterCombatComponent::Home() const{if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->Home;if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))return S->Home;if(auto* F=Cast<AFleshHandMonster>(GetOwner()))return F->Home;if(auto* W=Cast<AWolfMonster>(GetOwner()))return W->Home;if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))return M->Home;if(auto* N=Cast<ANurseZombie>(GetOwner()))return N->SpawnPosition;if(auto* H=Cast<AHandBrainMonster>(GetOwner()))return H->Home;return GetOwner()->GetActorLocation();}
void UMonsterCombatComponent::ReachedHome(){if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->Health=M10->MaxHealth;if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))S->Health=S->MaxHealth;if(auto* F=Cast<AFleshHandMonster>(GetOwner()))F->Health=F->MaxHealth;if(auto* W=Cast<AWolfMonster>(GetOwner()))W->ReachedHome();if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->Health=M->MaxHealth;if(auto* H=Cast<AHandBrainMonster>(GetOwner()))H->Health=H->MaxHealth;SetLocomotion(false);}
float UMonsterCombatComponent::ToughnessResistance(EMonsterAttackForm Form) const
{
 switch(Form)
 {
 case EMonsterAttackForm::Blade:return BladeResistance;
 case EMonsterAttackForm::Blunt:return BluntResistance;
 default:return ImpactResistance;
 }
}
float UMonsterCombatComponent::ToughnessDamageFor(float Damage,EMonsterAttackForm Form) const
{
 return MonsterToughness::ToughnessDamage(Damage,Form,ToughnessResistance(Form));
}
float UMonsterCombatComponent::ApplyHitWithReactionScale(float Multiplier,TFunctionRef<float()> ApplyDamage)
{
 TGuardValue<float> Scope(IncomingHitReactionMultiplier,Multiplier);
 return ApplyDamage();
}
float UMonsterCombatComponent::ApplyHitWithToughnessScale(float Multiplier,TFunctionRef<float()> ApplyDamage)
{
 TGuardValue<float> Scope(IncomingToughnessDamageMultiplier,FMath::Max(0.f,Multiplier));
 return ApplyDamage();
}
void UMonsterCombatComponent::ReceiveHit(float Damage,APawn* Attacker,EMonsterAttackForm Form)
{
 if(!GetOwner()->HasAuthority()||IsDead())return;
 if(auto* Pawn=Cast<APawn>(GetOwner()))if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController()))AI->RememberDamage(Attacker);
 // Closed reaction gate (firearms by default): the monster still remembers who
 // shot it, but never flips the state machine, the toughness clock or the hit
 // presentation. Melee and skills keep the existing scaled behaviour.
 if(IncomingHitReactionMultiplier<=0.f)return;
 if(IsKnockedDown())return;
 // 韧性结算：伤害先按命中形式与对应抗性折算成韧性伤害，攒满阈值才破韧。
 // 未破韧的命中只累积韧性，不打断动作、不进入硬直、不播放受击表现。
 // 耐心与装备的受击倍率（hit_reaction_mult）只作用于硬直时长，不改削韧速度。
 const float ToughnessDamage=ToughnessDamageFor(Damage,Form)*IncomingToughnessDamageMultiplier;
 LastToughnessDamage=ToughnessDamage;LastAttackForm=Form;
 Toughness+=ToughnessDamage;SinceHit=0;
 const bool bBreak=ToughnessThreshold<=0.f||Toughness>=ToughnessThreshold;
 const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
 const float Remaining=FMath::Max(IsControlled()?FMath::Max(0.f,ReactionDuration-ReactionTime):0.f,Status?Status->FrozenRemaining():0.f);
 if(bBreak){Toughness=0;SinceHit=0;++Breaks;}
 // 破韧只造成硬直；已有技能眩晕保留自己的到期时间，不被破韧延长。
 bStunned=StunSecondsRemaining()>0.f;
 if(!bBreak&&!bAllowSubthresholdStagger)
 {
  UE_LOG(LogTemp,Verbose,TEXT("MONSTER_TOUGHNESS target=%s form=%s damage=%.2f toughness_damage=%.2f toughness=%.2f/%.2f absorbed"),
   *GetOwner()->GetName(),MonsterToughness::FormName(Form),Damage,ToughnessDamage,Toughness,ToughnessThreshold);
  return;
 }
 // 破韧按破韧时长失能；可选的次阈值硬直沿用原短硬直时长。
 if(!bStunned)bParryReaction=false;
 const float Duration=(bBreak?ToughnessBreakSeconds:StaggerDuration)*IncomingHitReactionMultiplier;
 if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->InterruptAttack(FMath::Max(Remaining,Duration));
 if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))S->InterruptAttack(FMath::Max(Remaining,Duration));
 if(auto* F=Cast<AFleshHandMonster>(GetOwner()))F->InterruptAttack(FMath::Max(Remaining,Duration));
 if(auto* W=Cast<AWolfMonster>(GetOwner()))W->InterruptAttack(FMath::Max(Remaining,Duration));
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->InterruptAttack(FMath::Max(Remaining,Duration));
 if(auto* N=Cast<ANurseZombie>(GetOwner()))N->InterruptAttack(FMath::Max(Remaining,Duration));
 else if(auto* H=Cast<AHandBrainMonster>(GetOwner())){if(bBreak)H->InterruptAttack(FMath::Max(Remaining,Duration));}
 UE_LOG(LogTemp,Log,TEXT("MONSTER_TOUGHNESS_BREAK target=%s form=%s damage=%.2f toughness_damage=%.2f duration=%.2f breaks=%d"),
  *GetOwner()->GetName(),MonsterToughness::FormName(Form),Damage,ToughnessDamage,Duration,Breaks);
}
void UMonsterCombatComponent::BeginReaction(float Duration)
{
 ++HitReactions;ReactionTime=0;ReactionDuration=Duration;
 bStunned=StunSecondsRemaining()>0.f;
 const bool bContinueSway=BeginHumanoidStun(Duration);
 if(auto* C=Cast<ACharacter>(GetOwner()))
 {
  if(auto* AI=Cast<AMonsterAIController>(C->GetController())){AI->StopMovement();AI->UpdateKnowledge();}
  if(auto* M10=Cast<AM10Mawcrawler>(C))M10->StartHitPresentation();
        else if(auto* S=Cast<AHundredEyedSlagMonster>(C))S->StartHitPresentation();
  else if(auto* F=Cast<AFleshHandMonster>(C))F->StartHitPresentation();
  else if(auto* W=Cast<AWolfMonster>(C))W->StartHitPresentation();
  else if(auto* N=Cast<ANurseZombie>(C)){if(!bContinueSway)N->StartHitPresentation(HitClip,Duration);}
  else if(HitClip){C->GetMesh()->PlayAnimation(HitClip,false);C->GetMesh()->SetPlayRate(0);C->GetMesh()->SetPosition(0,false);}
  else {C->GetMesh()->SetPlayRate(0);UE_LOG(LogTemp,Warning,TEXT("MONSTER_HIT_CLIP_MISSING %s"),*GetOwner()->GetName());}
  if(bParryReaction)
  {
   // Resolve the recoil inside the parried damage call, even if the mesh has
   // already ticked. This samples a pose without advancing any combat clock.
   UpdateReactionPresentation();
   C->GetMesh()->TickAnimation(0.f,false);
   C->GetMesh()->RefreshBoneTransforms();
  }
 }
 // Reaction refresh happens once per accepted bullet; keep it out of the
 // default log stream (log LogTemp Verbose) so firing does not spam the output.
 UE_LOG(LogTemp,Verbose,TEXT("MONSTER_REACTION %s duration=%.3f stun=%d"),*GetOwner()->GetName(),Duration,bStunned);
}
void UMonsterCombatComponent::FinishReaction()
{
 if(IsKnockedDown())return;
 ClearHumanoidStun();
 ExplicitStunUntil=0.0;bStunned=false;bParryReaction=false;
 if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->FinishHitReaction();
 if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))S->FinishHitReaction();
 if(auto* F=Cast<AFleshHandMonster>(GetOwner()))F->FinishHitReaction();
 if(auto* W=Cast<AWolfMonster>(GetOwner()))W->FinishHitReaction();
 if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))if(M->State==EPoisonMaggotState::Stagger)M->SetState(EPoisonMaggotState::Recovery);
 // Restore a live idle/locomotion player after either reaction; leaving the
 // sampled hit player at its last frame would keep the body frozen in recovery.
 if(auto* N=Cast<ANurseZombie>(GetOwner());N && N->State==ENurseState::Stagger)N->SetState(ENurseState::Recovery);
 if(auto* H=Cast<AHandBrainMonster>(GetOwner())){if(H->State==EHandBrainState::Stagger){H->State=EHandBrainState::Recovery;H->StateSeconds=0;}}
 if(auto* P=Cast<APawn>(GetOwner()))if(auto* AI=Cast<AMonsterAIController>(P->GetController()))AI->UpdateKnowledge();
}
void UMonsterCombatComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick)
{
 Super::TickComponent(Dt,Type,Tick);if(!GetOwner()->HasAuthority()||IsDead())return;
 bStunned=StunSecondsRemaining()>0.f;
 if(!bStunned)bParryReaction=false;
 if(IsKnockedDown())return;
 TickParryPush(Dt);
 TickMeleePush(Dt);
 // 韧性在持续挨打时保持，脱离接触超过恢复时间后清空。
 SinceHit+=Dt;if(SinceHit>ToughnessRecoverySeconds)Toughness=0;
 if(IsControlled())
 {
  ReactionTime+=Dt;
  if(bPlayingSway){SwayTime+=Dt;SwayBlendTime+=Dt;}
  UpdateReactionPresentation();
 }
}
void UMonsterCombatComponent::UpdateReactionPresentation()
{
 if(UpdateHumanoidStun(ReactionTime,ReactionDuration-ReactionTime))return;
 // Parry starts at the existing recoil's impact pose, not its neutral lead-in.
 // Only presentation is offset; the full control duration remains unchanged.
 const float Elapsed=ReactionTime+(bParryReaction?.1f:0.f);
 const float Remaining=ReactionDuration-ReactionTime;
 if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->SetHitPresentationTime(Elapsed,Remaining);
 else if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))S->SetHitPresentationTime(Elapsed,Remaining);
 else if(auto* F=Cast<AFleshHandMonster>(GetOwner()))F->SetHitPresentationTime(Elapsed,Remaining);
 else if(auto* W=Cast<AWolfMonster>(GetOwner()))W->SetHitPresentationTime(Elapsed,Remaining);
 else if(auto* N=Cast<ANurseZombie>(GetOwner()))N->SetHitPresentationTime(HitClip,Elapsed,Remaining);
 else if(HitClip)if(auto* C=Cast<ACharacter>(GetOwner()))
 {
  const float T=Elapsed<.15f?Elapsed:(Remaining>.4f?.15f:HitClip->GetPlayLength()-FMath::Max(0.f,Remaining));
  C->GetMesh()->SetPosition(FMath::Clamp(T,0.f,HitClip->GetPlayLength()),false);
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
