#pragma once
#include "CoreMinimal.h"
#include "AIController.h"
#include "Perception/AIPerceptionTypes.h"
#include "MonsterAIController.generated.h"
class UBehaviorTree;
class UAIPerceptionComponent;
class UMonsterCombatComponent;
class AChapelShrine;
UCLASS()
class FPSGAME_API AMonsterAIController : public AAIController
{
 GENERATED_BODY()
public:
 AMonsterAIController();
 virtual ETeamAttitude::Type GetTeamAttitudeTowards(const AActor& Other) const override;
 virtual void OnPossess(APawn* Pawn) override;
 virtual void OnUnPossess() override;
 virtual void OnMoveCompleted(FAIRequestID RequestID,const FPathFollowingResult& Result) override;
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
 bool CanSeePlayer(APawn* Player,bool RequireFacing) const;
 /** The encounter owns this lock and destroys/releases it on exit, death or completion. */
 void SetEncounterTarget(APawn* Player);
 /** Only raiders opt into a permanent objective; normal perception still discovers players. */
 void SetNightRaidObjective(AChapelShrine* Shrine);
 APawn* GetEncounterTarget() const { return EncounterTarget.Get(); }
 void NotePursuitAttempt();
 /** Shared area membership permits local warnings; it does not reveal a player. */
 void SetEncounterArea(AActor* Area) { EncounterArea=Area; }
 void NavigateTo(FVector Destination,float Acceptance,float RepathInterval=.65f);
 bool ShouldAvoidNavigationGoal(const FVector& Goal,float Radius=75.f) const;
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
 bool CanHuntArtisans() const;
 bool IsCombatOpponent(const APawn* Candidate) const;
 TWeakObjectPtr<APawn> KnownTarget;
 TWeakObjectPtr<AChapelShrine> NightRaidObjective;
 TWeakObjectPtr<class AVillageDefenseSection> RaidBarrier;
 FVector RaidBarrierApproach=FVector::ZeroVector;
 double NextBarrierSearch=0.;
 void PublishNightRaidObjective();
 double NextRaidSearch=0.;
 uint8 RaidSearchStep=0;
 FVector RaidSearchPoint=FVector::ZeroVector;
 TWeakObjectPtr<APawn> EncounterTarget;
 TWeakObjectPtr<AActor> EncounterArea;
 void CheckForStalledPursuit(double Now);
 APawn* FindReplacement(bool Stalled,bool AttackOnly=false);
 void RememberAlternate(APawn* Player);
 TMap<TWeakObjectPtr<APawn>,double> AlternateEvidence, FailedPlayers;
 TWeakObjectPtr<APawn> ProgressTarget;
 FVector ProgressPosition=FVector::ZeroVector;
 double LastAttempt=-100.,LastTravel=0.,LastClosure=0.,BestDistance=0.,NextAlternativeCheck=0.;
 bool bAwaitingReplacement=false;
 bool bEncounterOwnsTarget=false;
 uint32 AlternativeRouteCursor=0;
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
 // Only common pursuit requests own this receipt; wander/feral/cloak paths keep their own recovery.
 FAIRequestID PursuitRequest=FAIRequestID::InvalidRequest;
 FVector PursuitDestination=FVector::ZeroVector,FailedPursuitDestination=FVector::ZeroVector;
 double FailedPursuitUntil=0.;
 float LastPursuitAcceptance=-1.f;
 uint8 ApproachSearchOffset=0;
 bool bHillsPursuitRecovery=false;
 bool bHillsPawnInvoker=false;
 FVector PursuitProgressPosition=FVector::ZeroVector;
 double PursuitProgressTime=0.;
 void RememberNavigationFailure(const FVector& Destination);
};
