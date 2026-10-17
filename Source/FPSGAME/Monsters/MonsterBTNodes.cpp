#include "MonsterBTNodes.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "NightWardenMonster.h"
#include "HeQueMonster.h"
#include "MantisM27Monster.h"
#include "Mutant3.h"
#include "WolfMonster.h"
#include "BellowSacLobber.h"
#include "M10Mawcrawler.h"
#include "HangingBellM09.h"
#include "LurkerM08Monster.h"
#include "VortexCofferM25.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
UBTTask_MonsterAction::UBTTask_MonsterAction(){bCreateNodeInstance=true;bNotifyTick=true;}
EBTNodeResult::Type UBTTask_MonsterAction::ExecuteTask(UBehaviorTreeComponent& Owner,uint8* Memory)
{
 TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_TaskExecute);
 Elapsed=0;auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner());if(!AI||!AI->Combat())return EBTNodeResult::Failed;
 AI->ActiveAction=NodeName;
 if(Action!=EMonsterAction::Idle)AI->StopWander();
 if(Action==EMonsterAction::Hold)if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))M09->StopCeiling();
 if(Action==EMonsterAction::Hold||Action==EMonsterAction::Attack)
  if(auto* M08=Cast<ALurkerM08Monster>(AI->GetPawn()))M08->StopSurfaceNavigation();
 if(Action==EMonsterAction::Attack)
 {
  // M27 rechecks a moving target at execution time. Its accepted attack owns
  // stopping movement; a stale CanAttack fact must not brake a failed swing.
  if(!Cast<AMantisM27Monster>(AI->GetPawn()))AI->StopMovement();
  return AI->Combat()->TryAttack(Cast<APawn>(Owner.GetBlackboardComponent()->GetValueAsObject(TEXT("Target"))))?EBTNodeResult::Succeeded:EBTNodeResult::Failed;
 }
 if(Action==EMonsterAction::Hold)AI->StopMovement();
 if(Action==EMonsterAction::Idle)AI->TickWander();
 return EBTNodeResult::InProgress;
}
void UBTTask_MonsterAction::TickTask(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt)
{
 TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_TaskTick);
 auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner());if(!AI||!AI->Combat()){FinishLatentTask(Owner,EBTNodeResult::Failed);return;}
 Elapsed+=Dt;auto* C=AI->Combat();auto* B=Owner.GetBlackboardComponent();
 if(Action==EMonsterAction::Idle)
 {
  AI->TickWander();
  // Blackboard decorators abort this persistent task on detection/control.
  // Retain the destination and animation phase across the entire stroll.
  return;
 }
 if(Action==EMonsterAction::Pursue||Action==EMonsterAction::Return)
 {
  if(C->IsBusy()||!AI->bDecisionEnabled||!AI->GetPawn()->IsActorTickEnabled()){AI->StopMovement();FinishLatentTask(Owner,EBTNodeResult::Aborted);return;}
  const bool Returning=Action==EMonsterAction::Return;FVector Dest=B->GetValueAsVector(Returning?TEXT("Home"):TEXT("LastKnown"));
  if(auto* Lobber=Cast<ABellowSacLobber>(AI->GetPawn());Lobber&&!Returning)
  {
   APawn* Visible=B->GetValueAsBool(TEXT("Visible"))?Cast<APawn>(B->GetValueAsObject(TEXT("Target"))):nullptr;
   Lobber->NavigateCombat(AI,Visible,Dest);
   if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
   return;
  }
  if(auto* M27=Cast<AMantisM27Monster>(AI->GetPawn());M27&&M27->bCloaked&&!M27->IsCloakRecoveryReady()&&!Returning)
  {
   AI->ActiveAction=TEXT("Cloak: retreat / orbit / regenerate");
   M27->NavigateWhileCloaked(AI,Dest);
   if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
   return;
  }
  if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))
  {
   M09->NavigateCeiling(Dest,Returning);
   if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
   return;
  }
  if(auto* M08=Cast<ALurkerM08Monster>(AI->GetPawn()))
  {
   APawn* Victim=!Returning&&B->GetValueAsBool(TEXT("Visible"))?Cast<APawn>(B->GetValueAsObject(TEXT("Target"))):nullptr;
   M08->NavigateSurface(Dest,Returning,Victim);
   if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
   return;
  }
  const FVector Feet=AI->GetPawn()->GetNavAgentLocation();
  const bool SameLevel=FMath::Abs(Dest.Z-Feet.Z)<=50.f;
  const float Stop=Returning?55.f:(B->GetValueAsBool(TEXT("Visible"))&&SameLevel?C->StopRange():40.f);
  if(auto* HeQue=Cast<AHeQueMonster>(AI->GetPawn());HeQue&&!Returning&&B->GetValueAsBool(TEXT("Visible")))
  {
   APawn* Victim=HeQue->PreferredCombatTarget(Cast<APawn>(B->GetValueAsObject(TEXT("Target"))));
   if(IsValid(Victim))
   {
    // A wide-agent NavMesh projection can be far from the actual player.
    // Use the live target for melee entry/holding; the projected path only
    // supplies travel, with a small end tolerance instead of the melee radius.
    if(C->TryAttack(Victim))
    {AI->ActiveAction=HeQue->IsJumpSlamming()?TEXT("HeQue: jump slam"):HeQue->IsPsychic()?TEXT("HeQue: psychic lament"):HeQue->IsRifting()?TEXT("HeQue: rift pressure"):HeQue->IsClamping()?TEXT("HeQue: heavy clamp"):TEXT("HeQue: kick");FinishLatentTask(Owner,EBTNodeResult::Succeeded);return;}
    if(FMath::Abs(Victim->GetNavAgentLocation().Z-Feet.Z)<=50.f&&HeQue->GetHorizontalDistanceTo(Victim)<=HeQue->StoppingDistance)
    {AI->StopMovement();C->SetLocomotion(false);}
    else {C->SetLocomotion(true);AI->NavigateTo(Victim->GetNavAgentLocation(),40.f);}
    if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
    return;
   }
  }
  auto* M10=Cast<AM10Mawcrawler>(AI->GetPawn());
  auto* M10Victim=Cast<APawn>(B->GetValueAsObject(TEXT("Target")));
  if(M10&&!Returning&&B->GetValueAsBool(TEXT("Visible"))&&M10->PrefersRearAttack(M10Victim))
  {
   // Hold a rear target only inside gas range, including during cooldown.
   // Beyond that range, normal navigation turns the M10 and resumes pursuit.
   AI->StopMovement();C->SetLocomotion(false);
  }
  else if(auto* M27=Cast<AMantisM27Monster>(AI->GetPawn()))
  {
   // A moving target can enter melee between knowledge-service updates. Use
   // the live contact query and common attack entry while sight is confirmed;
   // walls, cloak, control and cooldown still pass through CanAttack. A noise
   // investigation must not turn into a melee attack through its Target key.
   APawn* Known=!Returning?Cast<APawn>(B->GetValueAsObject(TEXT("Target"))):nullptr;
   const bool InMelee=B->GetValueAsBool(TEXT("Visible"))&&IsValid(Known)&&M27->CanMeleeFrom(Known,M27->GetActorLocation(),M27->MeleeStartDistance(Known));
   if(InMelee&&C->TryAttack(Known))
   {
    AI->StopMovement();AI->ActiveAction=TEXT("M27: close melee");
    FinishLatentTask(Owner,EBTNodeResult::Succeeded);return;
   }
   APawn* Victim=InMelee||B->GetValueAsBool(TEXT("Visible"))?Known:nullptr;
   // During cooldown keep closing on a moving target. Stopping as soon as
   // InMelee becomes true let that target leave again before the next swing.
   const float MeleeStop=Victim?FMath::Max(M27->GetSimpleCollisionRadius()+Victim->GetSimpleCollisionRadius()+15.f,
    M27->MeleeStartDistance(Victim)-65.f-FMath::Min(100.f,float(Victim->GetVelocity().Size2D())*.20f)):Stop;
   const bool Reached=Victim
    ? M27->GetCharacterMovement()->IsMovingOnGround()&&InMelee&&M27->GetHorizontalDistanceTo(Victim)<=MeleeStop
    : SameLevel&&FVector::Dist2D(Dest,Feet)<=Stop;
   AI->ActiveAction=M27->bCloaked?TEXT("Cloak: committed ambush approach"):TEXT("M27: melee / pounce approach");
   if(Reached){AI->StopMovement();C->SetLocomotion(false);}
   else C->SetLocomotion(AI->NavigateFeralTo(Dest,MeleeStop,Victim),Returning);
  }
  else if(auto* Mutant=Cast<AMutant3>(AI->GetPawn()))
  {
   APawn* Victim=!Returning&&B->GetValueAsBool(TEXT("Visible"))?Cast<APawn>(B->GetValueAsObject(TEXT("Target"))):nullptr;
   const float FeralStop=Victim?FMath::Max(25.f,Mutant->GetClawStartDistance()-15.f):Stop;
   const bool Reached=Victim
    ? Mutant->GetCharacterMovement()->IsMovingOnGround()&&Mutant->CanClawFrom(Victim,Mutant->GetActorLocation(),FeralStop)
    : SameLevel&&FVector::Dist2D(Dest,Feet)<=Stop;
   if(Reached){AI->StopMovement();C->SetLocomotion(false);}
   else C->SetLocomotion(AI->NavigateFeralTo(Dest,FeralStop,Victim),Returning);
  }
  else if(auto* Canine=Cast<AWolfMonster>(AI->GetPawn());Canine&&Canine->bUsePredictiveHunting)
  {
   APawn* Victim=!Returning&&B->GetValueAsBool(TEXT("Visible"))?Cast<APawn>(B->GetValueAsObject(TEXT("Target"))):nullptr;
   const bool Reached=Victim
    ? Canine->GetCharacterMovement()->IsMovingOnGround()&&Canine->CanBiteFrom(Victim,Canine->GetActorLocation(),Stop)
    : SameLevel&&FVector::Dist2D(Dest,Feet)<=Stop;
   if(Reached){AI->StopMovement();C->SetLocomotion(false);}
   else C->SetLocomotion(AI->NavigateFeralTo(Dest,Stop,Victim),Returning);
  }
  else if(SameLevel&&FVector::Dist2D(Dest,Feet)<=Stop)
  {
   AI->StopMovement();C->SetLocomotion(false);
   if(!Returning&&B->GetValueAsBool(TEXT("Visible")))
   {
    if(auto* M25=Cast<AVortexCofferM25>(AI->GetPawn()))M25->FaceNearbyTarget(M10Victim,Dt);
    if(auto* Warden=Cast<ANightWardenMonster>(AI->GetPawn()))Warden->FaceMeleeTarget(Cast<APawn>(B->GetValueAsObject(TEXT("Target"))),Dt);
   }
  }
  else{C->SetLocomotion(true,Returning);AI->NavigateTo(Dest,Stop);}
 }
 if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
}
EBTNodeResult::Type UBTTask_MonsterAction::AbortTask(UBehaviorTreeComponent& Owner,uint8* Memory)
{
 if(auto* AI=Owner.GetAIOwner())
 {
  if(auto* MonsterAI=Cast<AMonsterAIController>(AI))MonsterAI->StopWander();
  const auto* B=Owner.GetBlackboardComponent();
  const bool MantisAttackHandoff=Action==EMonsterAction::Pursue&&Cast<AMantisM27Monster>(AI->GetPawn())&&B&&
   B->GetValueAsBool(TEXT("CanAttack"))&&!B->GetValueAsBool(TEXT("Hold"))&&!B->GetValueAsBool(TEXT("Returning"));
  // Keep the path only across this pursuit -> attack handoff. Successful
  // melee/pounce stops it itself; control, return and other aborts still stop.
  if(!MantisAttackHandoff)AI->StopMovement();
  if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))M09->StopCeiling();
  if(auto* M08=Cast<ALurkerM08Monster>(AI->GetPawn()))M08->StopSurfaceNavigation();
 }
 return EBTNodeResult::Aborted;
}
UBTService_MonsterKnowledge::UBTService_MonsterKnowledge(){NodeName=TEXT("Update perception and combat facts");Interval=.1f;RandomDeviation=0;bCallTickOnSearchStart=true;}
void UBTService_MonsterKnowledge::ScheduleNextTick(UBehaviorTreeComponent& Owner,uint8* Memory)
{
 // Keep search-start/urgent updates immediate and the existing frequency.
 // Fixed per-owner phase spreads regular services without storing mutable
 // state on a BT template shared by all monsters or delaying combat ticks.
 const auto* AI=Owner.GetAIOwner();
 if(!AI||!Owner.GetWorld()||RandomDeviation>0.f){Super::ScheduleNextTick(Owner,Memory);return;}
 const double Period=FMath::Max(.001f,Interval);
 const uint32 PhaseKey=AI->GetUniqueID()*2654435761u;
 const double Phase=double(PhaseKey&65535u)/65536.*Period;
 const double Now=Owner.GetWorld()->GetTimeSeconds();
 const double Remainder=FMath::Fmod(Now+Phase,Period);
 SetNextTickTime(Memory,float(FMath::Max(.00001,Period-Remainder)));
}
void UBTService_MonsterKnowledge::TickNode(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt)
{
 TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_KnowledgeService);
 Super::TickNode(Owner,Memory,Dt);
 if(auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner()))AI->UpdateKnowledge();
}
void UBTDecorator_MonsterFlag::Configure(FName Key){BlackboardKey.SelectedKeyName=Key;OperationType=uint8(EBasicKeyOperation::Set);FlowAbortMode=EBTFlowAbortMode::Both;NotifyObserver=EBTBlackboardRestart::ResultChange;NodeName=Key.ToString();}
