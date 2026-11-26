#pragma once

#include "CoreMinimal.h"

class UWorld;
class FFPSGpuTraceCapture;

namespace HillsLiveTrace
{
// Called only by an explicit F6 GPU capture. A manually started trace keeps
// its own lifetime; the F6-owned trace stops with that capture or its World.
#if !UE_BUILD_SHIPPING
void StartForGpuCapture(UWorld* World,const TSharedRef<FFPSGpuTraceCapture,ESPMode::ThreadSafe>& Capture);
#endif
}
