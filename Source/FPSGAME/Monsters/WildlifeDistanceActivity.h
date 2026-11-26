#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WildlifeDistanceActivity.generated.h"

class AAIController;
class UAIPerceptionComponent;
class UAISense;
class UMonsterCombatComponent;

/** Server-selected activity for one hills animal, also applied to its simulated proxies. */
UCLASS()
class FPSGAME_API UWildlifeDistanceActivity : public UActorComponent
{
    GENERATED_BODY()
public:
    UWildlifeDistanceActivity();
    void SetDistancePaused(bool bPause);
    bool IsDistancePaused() const { return bApplied; }
    void LeaveForDeath();

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

private:
    UPROPERTY(ReplicatedUsing=OnRep_Paused) bool bDistancePaused = false;
    UFUNCTION() void OnRep_Paused();
    void ApplyPause(bool bPause);
    void PauseAI();
    void ResumeAI();

    bool bApplied = false;
    bool bLeftForDeath = false;
    bool bRestoreActorTick = false;
    bool bRestoreMovementTick = false;
    TWeakObjectPtr<UMonsterCombatComponent> PausedCombatTick;
    bool bRestoreAnimation = false;
    bool bRestoreControllerTick = false;
    bool bResumeBrain = false;
    TWeakObjectPtr<AAIController> PausedController;
    TWeakObjectPtr<UAIPerceptionComponent> Listener;
    TArray<TSubclassOf<UAISense>, TInlineAllocator<3>> PausedSenses;
};
