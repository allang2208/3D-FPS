#pragma once
#include "CoreMinimal.h"

namespace ProductionHarvestAssets
{
    bool IsMaterial(const FString& Definition);
    FSoftObjectPath PickupMesh(const FString& Definition);
    FSoftObjectPath Destruction(bool Wood);
    FSoftObjectPath Leaves();
    FSoftObjectPath Debris();
    TArray<FSoftObjectPath> LoadSet(bool Wood);
}
