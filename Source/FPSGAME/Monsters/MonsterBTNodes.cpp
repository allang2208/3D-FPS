#include "MonsterBTNodes.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
UBTTask_MonsterAction::UBTTask_MonsterAction(){bCreateNodeInstance=true;bNotifyTick=true;}
EBTNodeResult::Type UBTTask_MonsterAction::ExecuteTask(UBehaviorTreeComponent& Owner,uint8* Memory)
{
 Elapsed=0;auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner());if(!AI||!AI->Combat())return EBTNodeResult::Failed;
 AI->ActiveAction=NodeName;
 if(Action==EMonsterAction::Attack){AI->StopMovement();return AI->Combat()->TryAttack(Cast<APawn>(Owner.GetBlackboardComponent()->GetValueAsObject(TEXT("Target"))))?EBTNodeResult::Succeeded:EBTNodeResult::Failed;}
 if(Action==EMonsterAction::Hold||Action==EMonsterAction::Idle){AI->StopMovement();if(Action==EMonsterAction::Idle)AI->Combat()->SetLocomotion(false);}
 return EBTNodeResult::InProgress;
}
void UBTTask_MonsterAction::TickTask(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt)
{
 auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner());if(!AI||!AI->Combat()){FinishLatentTask(Owner,EBTNodeResult::Failed);return;}
 Elapsed+=Dt;auto* C=AI->Combat();auto* B=Owner.GetBlackboardComponent();
 if(Action==EMonsterAction::Pursue||Action==EMonsterAction::Return)
 {
  if(C->IsBusy()||!AI->bDecisionEnabled||!AI->GetPawn()->IsActorTickEnabled()){AI->StopMovement();FinishLatentTask(Owner,EBTNodeResult::Aborted);return;}
  const bool Returning=Action==EMonsterAction::Return;FVector Dest=B->GetValueAsVector(Returning?TEXT("Home"):TEXT("LastKnown"));
  const float Stop=Returning?55.f:(B->GetValueAsBool(TEXT("Visible"))?C->StopRange():40.f);
  if(FVector::Dist2D(Dest,AI->GetPawn()->GetActorLocation())<=Stop){AI->StopMovement();C->SetLocomotion(false);}
  else{C->SetLocomotion(true,Returning);AI->NavigateTo(Dest,Stop);}
 }
 if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);
}
EBTNodeResult::Type UBTTask_MonsterAction::AbortTask(UBehaviorTreeComponent& Owner,uint8* Memory){if(auto* AI=Owner.GetAIOwner())AI->StopMovement();return EBTNodeResult::Aborted;}
UBTService_MonsterKnowledge::UBTService_MonsterKnowledge(){NodeName=TEXT("Update perception and combat facts");Interval=.1f;RandomDeviation=0;bCallTickOnSearchStart=true;}
void UBTService_MonsterKnowledge::TickNode(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt){Super::TickNode(Owner,Memory,Dt);if(auto* AI=Cast<AMonsterAIController>(Owner.GetAIOwner()))AI->UpdateKnowledge();}
void UBTDecorator_MonsterFlag::Configure(FName Key){BlackboardKey.SelectedKeyName=Key;OperationType=uint8(EBasicKeyOperation::Set);FlowAbortMode=EBTFlowAbortMode::Both;NotifyObserver=EBTBlackboardRestart::ResultChange;NodeName=Key.ToString();}
