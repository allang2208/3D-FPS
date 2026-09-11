#pragma once
#include "CoreMinimal.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BehaviorTree/BTService.h"
#include "BehaviorTree/Decorators/BTDecorator_Blackboard.h"
#include "MonsterBTNodes.generated.h"
UENUM()
enum class EMonsterAction:uint8 { Hold,Return,Attack,Pursue,Idle };
UCLASS()
class FPSGAME_API UBTTask_MonsterAction : public UBTTaskNode
{
 GENERATED_BODY()
public:
 UBTTask_MonsterAction();
 UPROPERTY(EditAnywhere,Category="Action") EMonsterAction Action=EMonsterAction::Idle;
 virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& Owner,uint8* Memory) override;
 virtual void TickTask(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt) override;
 virtual EBTNodeResult::Type AbortTask(UBehaviorTreeComponent& Owner,uint8* Memory) override;
private: float Elapsed=0;
};
UCLASS()
class FPSGAME_API UBTService_MonsterKnowledge : public UBTService
{
 GENERATED_BODY()
public: UBTService_MonsterKnowledge();
 virtual void TickNode(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt) override;
};
UCLASS()
class FPSGAME_API UBTDecorator_MonsterFlag : public UBTDecorator_Blackboard
{
 GENERATED_BODY()
public: void Configure(FName Key);
};
