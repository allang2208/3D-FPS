#include "MonsterBTNodes.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "Mutant3.h"
#include "WolfMonster.h"
#include "M10Mawcrawler.h"
#include "HangingBellM09.h"
#include "VortexCofferM25.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
UBTTask_MonsterAction::UBTTask_MonsterAction(){bCreateNodeInstance=true;bNotifyTick=true;}
EBTNodeResult::Type UBTTask_MonsterAction::ExecuteTask(UBehaviorTreeComponent& Owner,uint8* Memory)
{
 Elapsed=0;auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner());if(!AI||!AI->Combat())return EBTNodeResult::Failed;
 AI->ActiveAction=NodeName;
 if(Action==EMonsterAction::Hold||Action==EMonsterAction::Idle)if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))M09->StopCeiling();
 if(Action==EMonsterAction::Attack){AI->StopMovement();return AI->Combat()->TryAttack(Cast<APawn>(Owner.GetBlackboardComponent()->GetValueAsObject(TEXT("Target"))))?EBTNodeResult::Succeeded:EBTNodeResult::Failed;}
 const auto* M25=Cast<AVortexCofferM25>(AI->GetPawn());
 const bool Searching=Action==EMonsterAction::Idle&&M25&&M25->bSearchForPlayers&&AI->bDecisionEnabled;
 if(Action==EMonsterAction::Hold||(Action==EMonsterAction::Idle&&!Searching))
 {AI->StopMovement();if(Action==EMonsterAction::Idle)AI->Combat()->SetLocomotion(false);}
 return EBTNodeResult::InProgress;
}
void UBTTask_MonsterAction::TickTask(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt)
{
 auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner());if(!AI||!AI->Combat()){FinishLatentTask(Owner,EBTNodeResult::Failed);return;}
 Elapsed+=Dt;auto* C=AI->Combat();auto* B=Owner.GetBlackboardComponent();
 if(Action==EMonsterAction::Idle)
 {
  if(auto* M25=Cast<AVortexCofferM25>(AI->GetPawn());M25&&M25->bSearchForPlayers)
  {
   if(C->IsBusy()||!AI->bDecisionEnabled||!M25->IsActorTickEnabled())
   {AI->StopMovement();FinishLatentTask(Owner,EBTNodeResult::Aborted);return;}
   FVector SearchGoal;
   if(M25->SearchDestination(SearchGoal))
   {
    AI->ActiveAction=TEXT("Search for player");
    AI->NavigateTo(SearchGoal,65.f);
    if(AI->bNavigationFailed){M25->DeferSearch();AI->StopMovement();}
   }
   else AI->StopMovement();
  }
 }
 if(Action==EMonsterAction::Pursue||Action==EMonsterAction::Return)
 {
  if(C->IsBusy()||!AI->bDecisionEnabled||!AI->GetPawn()->IsActorTickEnabled()){AI->StopMovement();FinishLatentTask(Owner,EBTNodeResult::Aborted);return;}
  const bool Returning=Action==EMonsterAction::Return;FVector Dest=B->GetValueAsVector(Returning?TEXT("Home"):TEXT("LastKnown"));
  if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))
  {
   M09->NavigateCeiling(Dest,Returning);
   if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
   return;
  }
  const FVector Feet=AI->GetPawn()->GetNavAgentLocation();
  const bool SameLevel=FMath::Abs(Dest.Z-Feet.Z)<=50.f;
  const float Stop=Returning?55.f:(B->GetValueAsBool(TEXT("Visible"))&&SameLevel?C->StopRange():40.f);
  auto* M10=Cast<AM10Mawcrawler>(AI->GetPawn());
  auto* M10Victim=Cast<APawn>(B->GetValueAsObject(TEXT("Target")));
  if(M10&&!Returning&&B->GetValueAsBool(TEXT("Visible"))&&M10->PrefersRearAttack(M10Victim))
  {
   // Hold a rear target only inside gas range, including during cooldown.
   // Beyond that range, normal navigation turns the M10 and resumes pursuit.
   AI->StopMovement();C->SetLocomotion(false);
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
    if(auto* M25=Cast<AVortexCofferM25>(AI->GetPawn()))M25->FaceNearbyTarget(M10Victim,Dt);
  }
  else{C->SetLocomotion(true,Returning);AI->NavigateTo(Dest,Stop);}
 }
 if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
}
EBTNodeResult::Type UBTTask_MonsterAction::AbortTask(UBehaviorTreeComponent& Owner,uint8* Memory){if(auto* AI=Owner.GetAIOwner()){AI->StopMovement();if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))M09->StopCeiling();}return EBTNodeResult::Aborted;}
UBTService_MonsterKnowledge::UBTService_MonsterKnowledge(){NodeName=TEXT("Update perception and combat facts");Interval=.1f;RandomDeviation=0;bCallTickOnSearchStart=true;}
void UBTService_MonsterKnowledge::TickNode(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt){Super::TickNode(Owner,Memory,Dt);if(auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner()))AI->UpdateKnowledge();}
void UBTDecorator_MonsterFlag::Configure(FName Key){BlackboardKey.SelectedKeyName=Key;OperationType=uint8(EBasicKeyOperation::Set);FlowAbortMode=EBTFlowAbortMode::Both;NotifyObserver=EBTBlackboardRestart::ResultChange;NodeName=Key.ToString();}
