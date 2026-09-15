#pragma once
#include "CoreMinimal.h"

namespace TacticalSuppressorAssets
{
inline FString MeshPath(const TCHAR* Family)
{
    return FString::Printf(TEXT("/Game/Weapons/TacticalSuppressor20260913/%s/SM_TacticalSuppressor"), Family);
}
}
