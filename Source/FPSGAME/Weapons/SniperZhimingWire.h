#pragma once
#include "CoreMinimal.h"

namespace SniperZhimingWire
{
bool Enabled();
const TCHAR* Definition(int32 Phase);
void EnsureTarget(UWorld* World);
}
