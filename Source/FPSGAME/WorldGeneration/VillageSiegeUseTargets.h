#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "VillageSiegeUseTargets.generated.h"

class AVillageSiegeEngine;

// Standing engines have a much larger silhouette than their movement collision.
UCLASS()
class UVillageSiegeUseTargets : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    void Register(AVillageSiegeEngine& Engine);
    void Remove(AVillageSiegeEngine& Engine);
    AVillageSiegeEngine* Trace(const FVector& Player, const FVector& Eye, const FVector& Direction,
        double Reach, double& HitDistance) const;
private:
    TSet<TWeakObjectPtr<AVillageSiegeEngine>> Engines;
};
