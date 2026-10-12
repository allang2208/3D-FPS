#pragma once

#include "CoreMinimal.h"
#include "RenderCommandFence.h"
#include "Subsystems/WorldSubsystem.h"
#include "FacilityHallSpawnSubsystem.generated.h"

class AFacilityHallEncounter;

/** Shares staff spawn admission across halls without retaining unused monster instances. */
UCLASS()
class FPSGAME_API UFacilityHallSpawnSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    void Request(AFacilityHallEncounter* Hall);
    void Cancel(AFacilityHallEncounter* Hall);
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override;
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;

private:
    TArray<TWeakObjectPtr<AFacilityHallEncounter>> Pending;
    FRenderCommandFence SpawnRenderFence;
    uint64 LastAttemptFrame = MAX_uint64;
    double NextAttemptAt = 0.;
    bool bRenderRegistrationPending = false;
};
