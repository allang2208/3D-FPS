#pragma once

#include "CoreMinimal.h"
#include "RenderCommandFence.h"
#include "Subsystems/WorldSubsystem.h"
#include "FacilityHallSpawnSubsystem.generated.h"

class AFacilityHallEncounter;

/** One admission queue; bounded optional preparation never postpones a due wave. */
UCLASS()
class FPSGAME_API UFacilityHallSpawnSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    void Request(AFacilityHallEncounter* Hall);
    void RequestPreparation(AFacilityHallEncounter* Hall);
    void Cancel(AFacilityHallEncounter* Hall);
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override;
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;
    int32 PreparedCount() const;
    int32 PendingCount() const { return Pending.Num(); }
    FName PreparationLastDecision() const { return PreparationDecision; }

private:
    TArray<TWeakObjectPtr<AFacilityHallEncounter>> Pending;
    TArray<TWeakObjectPtr<AFacilityHallEncounter>> PreparationPending;
    TArray<TWeakObjectPtr<AFacilityHallEncounter>> PreparedHalls;
    double NextPreparationAt = 0.;
    FRenderCommandFence SpawnRenderFence;
    uint64 LastAttemptFrame = MAX_uint64;
    double NextAttemptAt = 0.;
    bool bRenderRegistrationPending = false;
    FName PreparationDecision=TEXT("not_requested");
};
