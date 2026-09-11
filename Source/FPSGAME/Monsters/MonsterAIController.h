#pragma once
#include "CoreMinimal.h"
#include "AIController.h"
#include "Perception/AIPerceptionTypes.h"
#include "MonsterAIController.generated.h"
class UBehaviorTree;
class UAIPerceptionComponent;
class UMonsterCombatComponent;
UCLASS()
class FPSGAME_API AMonsterAIController : public AAIController
{
 GENERATED_BODY()
public:
 AMonsterAIController();
 virtual void OnPossess(APawn* Pawn) override;
 virtual void OnUnPossess() override;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI") TObjectPtr<UBehaviorTree> Behavior;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI") float MemorySeconds=12.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="MonsterAI") FString ActiveAction;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="MonsterAI") int32 NavigationRequests=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="MonsterAI") bool bNavigationFailed=false;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="MonsterAI") bool bDecisionEnabled=true;
 void UpdateKnowledge();
 void RememberDamage(APawn* Attacker);
 void NavigateTo(FVector Destination,float Acceptance);
 UMonsterCombatComponent* Combat() const;
 UFUNCTION(BlueprintCallable,Category="MonsterAI") void SetDecisionEnabled(bool Enabled);
 UFUNCTION(BlueprintCallable,Category="MonsterAI|Editor") static bool BuildTree(UBehaviorTree* Tree);
 UFUNCTION(BlueprintCallable,Category="MonsterAI|Editor",meta=(WorldContext="Context")) static bool BuildNavigationBounds(UObject* Context,FVector Center,FVector Extent);
private:
 UPROPERTY() TObjectPtr<UAIPerceptionComponent> Senses;
 UFUNCTION() void Perceived(AActor* Actor,FAIStimulus Stimulus);
 TWeakObjectPtr<APawn> KnownTarget;
 FVector LastKnown=FVector::ZeroVector,LastDestination=FVector::ZeroVector;
 float LastEvidence=-100.f,LastMove=-100.f;
 bool bReturning=false;
};
