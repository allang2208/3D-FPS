#include "FPSGpuTraceSessionSubsystem.h"
#include "FPSGpuTraceCapture.h"

TSharedRef<FFPSGpuTraceCapture, ESPMode::ThreadSafe> UFPSGpuTraceSessionSubsystem::StartCapture(
    const FString& MetricsSession, uint64 Generation)
{
    Capture = FFPSGpuTraceCapture::Start(MetricsSession, Generation, GetGameInstance());
    return Capture.ToSharedRef();
}

void UFPSGpuTraceSessionSubsystem::Deinitialize()
{
    // A process-wide trace can be explicitly shared by several PIE instances.
    // Only its initiating instance owns automatic shutdown; another client's
    // teardown must not end the initiator's capture.
    if (Capture && Capture->IsOwnedBy(GetGameInstance()))
        Capture->RequestStop(TEXT("game_instance_deinitialize"));
    Capture.Reset();
    Super::Deinitialize();
}
