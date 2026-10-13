#pragma once

#include "CoreMinimal.h"
#include "AI/Navigation/NavigationTypes.h"
#include "Subsystems/WorldSubsystem.h"
#include "MonsterNavigationCache.generated.h"

class UNavigationSystemV1;
class ANavigationData;

/** Reuses identical goal projections within one frame, never paths or decisions. */
UCLASS()
class FPSGAME_API UMonsterNavigationCache : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    bool Project(UNavigationSystemV1* Nav, const ANavigationData* Data,
        const FVector& Position, const FVector& Extent, FNavLocation& Result);
private:
    struct FProjection
    {
        TWeakObjectPtr<const ANavigationData> Data;
        FVector Position, Extent;
        FNavLocation Result;
        bool bFound=false;
    };
    TArray<FProjection,TInlineAllocator<16>> Projections;
    uint64 Frame=MAX_uint64;
};
