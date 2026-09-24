#pragma once
#include "CoreMinimal.h"

namespace ProductionHarvestAssets
{
    bool IsMaterial(const FString& Definition);
    FSoftObjectPath PickupMesh(const FString& Definition,int32 Variant=0);
    /** 2026-09-24 冶炼材料建模：矿石=强化石网格×分矿种色调材质、锭=铸锭网格×金属色材质；
     *  返回该定义的材质覆写路径（无覆写＝用网格自带材质）。 */
    FSoftObjectPath PickupMaterial(const FString& Definition);
    int32 TreeVariant(const FSoftObjectPath& Tree);
    FSoftObjectPath Stump(int32 Variant=0);
    FSoftObjectPath FallingMesh(int32 Variant);
    FSoftObjectPath CutProfile(int32 Variant);
    FSoftObjectPath FallingMaterial(int32 Slot);
    FSoftObjectPath TreeSound(bool Landing);
    FSoftObjectPath Destruction(bool Wood);
    FSoftObjectPath Leaves();
    FSoftObjectPath Debris();
    TArray<FSoftObjectPath> LoadSet(bool Wood);
}
