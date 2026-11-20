#pragma once

#include "Components/ActorComponent.h"
#include "HillsTavernSite.generated.h"

class ATemperateHillsWorld;
class AVillageTavernKeeper;

/** Streamed House 02. The 1318 x 878 cm deck has its floor at local Z=0.
 * +X runs along the ridge. The street door is at (0,-426), the bar faces it
 * from the +Y wall, and the oak tie beams cross the hall at Z=316. */
UCLASS()
class UHillsTavernSite : public UActorComponent
{
    GENERATED_BODY()
public:
    void Bind(ATemperateHillsWorld& WorldOwner);

protected:
    virtual void EndPlay(EEndPlayReason::Type Reason) override;

private:
    void Refresh();
    void UpdateKeeper(bool bRepaired);
    bool RepairAreaOccupied() const;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<AActor> Furnishings;
    TWeakObjectPtr<AVillageTavernKeeper> Keeper;
    bool bShowingRepaired = false;
};
