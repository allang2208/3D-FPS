#pragma once

#include "UObject/SoftObjectPath.h"

namespace VillageMasonry
{
    inline FSoftObjectPath Mesh(const FString& Name)
    {
        return FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/VillageMasonry/ReliefMeshes/") + Name + TEXT(".") + Name);
    }
}
