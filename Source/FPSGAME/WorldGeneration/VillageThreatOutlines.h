#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "TimerManager.h"
#include "VillageThreatOutlines.generated.h"

class ATemperateHillsWorld;
class UMonsterCombatComponent;

/** Tracks village entrants on the server, independently of raid schedules and spell marks. */
UCLASS()
class FPSGAME_API UVillageThreatOutlines : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void Deinitialize() override;
    void RegisterMonster(UMonsterCombatComponent* Combat);
    void UnregisterMonster(UMonsterCombatComponent* Combat);
private:
    void Update();
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TMap<TWeakObjectPtr<UMonsterCombatComponent>,bool> Monsters;
    FTimerHandle Timer;
};
