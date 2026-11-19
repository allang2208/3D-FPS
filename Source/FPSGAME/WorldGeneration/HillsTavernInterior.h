#pragma once
#include "CoreMinimal.h"
#include "UObject/SoftObjectPath.h"

class AActor;
class USceneComponent;

struct FHillsTavernInterior
{
    static void AddBlockingMeshPaths(TArray<FSoftObjectPath>& Paths);
    static bool AreBlockingMeshesLoaded();
    // Room space is centred on the finished floor, with the street on the -Y side.
    static void Populate(AActor& Host, USceneComponent& RoomRoot, bool bRepaired);
};
