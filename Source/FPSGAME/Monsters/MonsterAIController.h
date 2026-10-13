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
 virtual ETeamAttitude::Type GetTeamAttitudeTowards(const AActor& Other) const override;
 virtual void OnPossess(APawn* Pawn) override;
 virtual void OnUnPossess() override;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI") TObjectPtr<UBehaviorTree> Behavior;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI") float MemorySeconds=12.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI|Alert",meta=(ClampMin="0",Units="cm")) float GroupAlertRadius=1200.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI|Alert",meta=(ClampMin="1",Units="s")) float GroupAlertCooldown=5.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI|Alert",meta=(ClampMin="0",Units="s")) float PassiveDiscoveryDelayMin=1.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI|Alert",meta=(ClampMin="0",Units="s")) float PassiveDiscoveryDelayMax=2.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="MonsterAI") FString ActiveAction;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="MonsterAI") int32 NavigationRequests=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="MonsterAI") bool bNavigationFailed=false;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="MonsterAI") bool bDecisionEnabled=true;
 void UpdateKnowledge();
 void RememberDamage(APawn* Attacker);
 /** The encounter owns this lock and destroys/releases it on exit, death or completion. */
 void SetEncounterTarget(APawn* Player);
 /** Shared area membership permits local warnings; it does not reveal a player. */
 void SetEncounterArea(AActor* Area) { EncounterArea=Area; }
 void NavigateTo(FVector Destination,float Acceptance);
 /** Idle is a persistent BT task; never rebuild a wander path on each tick. */
 void TickWander();
 void StopWander();
 float IdleMovementScale() const { return bWanderActive ? .5f : 1.f; }
 bool IsWandering() const { return bWanderActive; }
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="MonsterAI|Wander",meta=(ClampMin="100",Units="cm")) float WanderRadius=800.f;
 /** Mutant / opt-in canine pursuit, with attack positions and bounded blocked-path retries. */
 bool NavigateFeralTo(FVector Destination,float Acceptance,APawn* VisibleTarget);
 UMonsterCombatComponent* Combat() const;
 UFUNCTION(BlueprintCallable,Category="MonsterAI") void SetDecisionEnabled(bool Enabled);
 UFUNCTION(BlueprintCallable,Category="MonsterAI|Editor") static bool BuildTree(UBehaviorTree* Tree);
 UFUNCTION(BlueprintCallable,Category="MonsterAI|Editor",meta=(WorldContext="Context")) static bool BuildNavigationBounds(UObject* Context,FVector Center,FVector Extent);
private:
 UPROPERTY() TObjectPtr<UAIPerceptionComponent> Senses;
 UFUNCTION() void Perceived(AActor* Actor,FAIStimulus Stimulus);
 TWeakObjectPtr<APawn> KnownTarget;
 TWeakObjectPtr<APawn> EncounterTarget;
 TWeakObjectPtr<AActor> EncounterArea;
 bool CanSeePlayer(APawn* Player,bool RequireFacing) const;
 void DiscoverPlayer(APawn* Player,bool Broadcast);
 void BroadcastGroupAlert();
 void ConsumePassiveDiscovery();
 TWeakObjectPtr<APawn> PendingDamageTarget;
 float NextBroadcast=0.f,EvidenceLifetime=12.f,PassiveDiscoveryAt=-1.f;
 bool bConfirmedTarget=false,bPendingGroupAlert=false;
 FVector LastKnown=FVector::ZeroVector,LastDestination=FVector::ZeroVector;
 float LastEvidence=-100.f,LastMove=-100.f;
 bool bReturning=false;
 void PauseWander(float Now,bool Failed);
 bool ChooseWanderDestination();
 FRandomStream WanderRandom;
 FVector WanderGoal=FVector::ZeroVector,WanderProgressPosition=FVector::ZeroVector;
 float NextWanderUpdate=0.f,NextWanderMove=0.f,WanderProgressTime=0.f,WanderDeadline=0.f;
 uint8 WanderFailures=0;
 bool bWanderActive=false,bWanderMoving=false;
};
