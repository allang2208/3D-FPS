#pragma once
#include "CoreMinimal.h"

class AChapelNun;
class ATemperateHillsWorld;

namespace TemperateHillsChapel
{
    AChapelNun* FindNun(ATemperateHillsWorld* Hills);
    bool IsChapelWorld(const UWorld* World);
    void AddMeshPaths(TArray<FSoftObjectPath>& Paths);
}

