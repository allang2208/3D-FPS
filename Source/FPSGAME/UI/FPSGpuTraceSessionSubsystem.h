#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "FPSGpuTraceSessionSubsystem.generated.h"

class FFPSGpuTraceCapture;

/** Retains an explicitly started GPU capture through travel within one play session. */
UCLASS()
class FPSGAME_API UFPSGpuTraceSessionSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Deinitialize() override;
    TSharedPtr<FFPSGpuTraceCapture, ESPMode::ThreadSafe> GetCapture() const { return Capture; }
    TSharedRef<FFPSGpuTraceCapture, ESPMode::ThreadSafe> StartCapture(const FString& MetricsSession, uint64 Generation);
private:
    TSharedPtr<FFPSGpuTraceCapture, ESPMode::ThreadSafe> Capture;
};
