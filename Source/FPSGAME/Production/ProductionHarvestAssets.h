#pragma once
#include "CoreMinimal.h"

namespace ProductionHarvestAssets
{
    bool IsMaterial(const FString& Definition);
    FSoftObjectPath PickupMesh(const FString& Definition,int32 Variant=0);
    int32 TreeVariant(const FSoftObjectPath& Tree);
    FSoftObjectPath Stump(int32 Variant=0);
    FSoftObjectPath CutCap(int32 Variant=INDEX_NONE);
    FSoftObjectPath FallingMaterial(int32 Slot);
    FSoftObjectPath TreeSound(bool Landing);
    FSoftObjectPath Destruction(bool Wood);
    FSoftObjectPath Leaves();
    FSoftObjectPath Debris();
    TArray<FSoftObjectPath> LoadSet(bool Wood);
}
