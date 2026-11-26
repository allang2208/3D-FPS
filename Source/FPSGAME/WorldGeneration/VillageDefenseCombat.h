#pragma once
#include "CoreMinimal.h"
class APawn;
class AActor;
class AVillageDefenseSection;
class UNavigationSystemV1;
class ANavigationData;
namespace VillageDefenseCombat
{
    FVector Aim(const AActor* Target,const FVector& From);
    AVillageDefenseSection* Blocking(const APawn* Monster,const AActor* Target);
    AVillageDefenseSection* Reachable(UWorld* World,const FVector& From,const FVector& Goal,
        UNavigationSystemV1* Nav,const ANavigationData* Data,FVector& Approach);
    bool HasRoute(UWorld* World,const FVector& From,const FVector& Goal,UNavigationSystemV1* Nav,const ANavigationData* Data);
}
