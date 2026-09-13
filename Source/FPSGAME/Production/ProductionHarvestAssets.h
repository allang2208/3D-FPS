#pragma once
#include "CoreMinimal.h"

namespace ProductionHarvestAssets
{
    bool IsMaterial(const FString& Definition);
    FSoftObjectPath PickupMesh(const FString& Definition,int32 Variant=0);
    FSoftObjectPath Stump();
    FSoftObjectPath CutCap();
    FSoftObjectPath FallingMaterial(int32 Slot);
    FSoftObjectPath TreeSound(bool Landing);
    FSoftObjectPath Destruction(bool Wood);
    FSoftObjectPath Leaves();
    FSoftObjectPath Debris();
    TArray<FSoftObjectPath> LoadSet(bool Wood);
}
