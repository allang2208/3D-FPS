#pragma once

#include "TemperateHillsWorld.h"

namespace TemperateQuarryFixedDressing
{
struct FBlocker
{
    FBox Bounds;
    FTemperatePlacement Item;
};

struct FLayout
{
    TMap<FSoftObjectPath, TArray<FTransform>> Groups;
    TArray<FBlocker> Blockers;
};

using FLayoutPtr = TSharedPtr<FLayout, ESPMode::ThreadSafe>;
FLayoutPtr Load(uint32 TerrainLayout);
#if WITH_EDITOR
bool Write(uint32 TerrainLayout, FLayout& Layout);
#endif
}
