#pragma once

#include "CoreMinimal.h"

class FJsonObject;
class FRHIBuffer;
class UGameInstance;

/** Explicit F6 deep capture. Owns only its ETW session and its UE trace connection. */
class FFPSGpuTraceCapture : public TSharedFromThis<FFPSGpuTraceCapture, ESPMode::ThreadSafe>
{
public:
    /** Read-only process permission guidance. Does not launch or elevate anything. */
    static FString ReadyStatusText();
    static TSharedRef<FFPSGpuTraceCapture, ESPMode::ThreadSafe> Start(const FString& MetricsSession, uint64 Generation, UGameInstance* GameInstance);
    ~FFPSGpuTraceCapture();
    void RequestStop(const FString& Reason);
    bool IsRunning() const;
    bool IsCollectingBuffers() const;
    /** True only after the full WDDM/UE bundle is sealed without recorded data loss. */
    bool HasCompleteBundle() const;
    /** Game-thread lifetime ownership; the trace itself remains process-wide. */
    bool IsOwnedBy(const UGameInstance* GameInstance) const;
    FString StatusText() const;
    /** Worker only. Seals sidecars before the report advertises their completion. */
    TSharedPtr<FJsonObject> FinishForExport();
    /** RHI command stream only; metadata reads, no GPU wait or residency mutation. */
    TSharedRef<FJsonObject> ObserveBuffer(FRHIBuffer* Buffer, const FString& Component,
        const FString& Asset, const TCHAR* Role, uint64 GameFrame, uint64 RenderFrame);
    FString GetDirectory() const;
private:
    struct FState;
    TSharedPtr<FState, ESPMode::ThreadSafe> State;
    FFPSGpuTraceCapture();
};
