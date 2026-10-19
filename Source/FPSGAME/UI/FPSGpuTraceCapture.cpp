#include "FPSGpuTraceCapture.h"

#include "Async/Async.h"
#include "Containers/Queue.h"
#include "Containers/StringConv.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "HAL/Event.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/PlatformProcess.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeLock.h"
#include "ProfilingDebugging/MiscTrace.h"
#include "ProfilingDebugging/TraceAuxiliary.h"
#include "RHIResources.h"
#include "Serialization/JsonSerializer.h"

#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#include "Windows/AllowWindowsPlatformTypes.h"
#include <evntrace.h>
#include <evntprov.h>
#include "Windows/HideWindowsPlatformTypes.h"
#include "ID3D12DynamicRHI.h"
#endif

namespace FPSGpuTrace
{
FCriticalSection OwnerLock;
TSharedPtr<FFPSGpuTraceCapture, ESPMode::ThreadSafe> Owner;
constexpr double MaxSeconds = 180.;
constexpr int64 MaxUeBytes = 1024ll * 1024 * 1024;
constexpr int32 MaxQueuedIdentities = 1024;
FString Hex(uint64 Value) { return FString::Printf(TEXT("0x%016llx"), Value); }
FString Json(const TSharedRef<FJsonObject>& Value)
{
    FString Result;
    FJsonSerializer::Serialize(Value, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Result));
    return Result;
}
#if PLATFORM_WINDOWS
struct FProcessPermissions
{
    ULONG Error = ERROR_SUCCESS;
    bool bElevated = false;
};
const FProcessPermissions& ProcessPermissions()
{
    // Cache this process-token read; refreshing the F6 label must stay cheap.
    static const FProcessPermissions Result = []
    {
        FProcessPermissions Value;
        HANDLE Token = nullptr;
        if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &Token))
        { Value.Error = GetLastError(); return Value; }
        TOKEN_ELEVATION Elevation{};
        DWORD ReturnedBytes = 0;
        if (GetTokenInformation(Token, TokenElevation, &Elevation, sizeof(Elevation), &ReturnedBytes))
            Value.bElevated = Elevation.TokenIsElevated != 0;
        else Value.Error = GetLastError();
        CloseHandle(Token);
        return Value;
    }();
    return Result;
}

// Windows SDK GPUView providers. Intentionally omit ForceVsync, StablePower,
// DefaultOverride and Cdd; capturing must not alter graphics/power policy.
const GUID DxgKrnl = {0x802ec45a,0x1e99,0x4b83,{0x99,0x20,0x87,0xc9,0x82,0x77,0xba,0x9d}};
const GUID D3D12 = {0x5d8087dd,0x3a9b,0x4f56,{0x90,0xdf,0x49,0x19,0x6c,0xdc,0x4f,0x11}};
const GUID Umd = {0xa688ee40,0xd8d9,0x4736,{0xb6,0xf9,0x6b,0x74,0x93,0x5b,0xa3,0xb1}};
const GUID Identity = {0x9c613968,0xe475,0x4f37,{0xa1,0x6d,0x0e,0xc7,0x53,0xf8,0x49,0x25}};
constexpr uint64 DxgKeywords = 0x043084c7ull; // Base,Profiler,References,Resource,Memory,DriverEvents,GPUScheduler,GPUVA,VidMm,HWS.
struct FEtwProperties
{
    EVENT_TRACE_PROPERTIES Value{};
    WCHAR Session[128]{};
    WCHAR File[1024]{};
};
#endif
}

FString FFPSGpuTraceCapture::ReadyStatusText()
{
#if PLATFORM_WINDOWS
    const auto& Permissions = FPSGpuTrace::ProcessPermissions();
    if (Permissions.Error != ERROR_SUCCESS)
        return FString::Printf(TEXT("GPU 深采未开始；进程权限状态读取失败（%lu）。开始后确认 WDDM 状态；错误 5 的启动说明见项目根目录 Launch-F6-WddmCapture.cmd。"), Permissions.Error);
    if (!Permissions.bElevated)
        return TEXT("当前 UE 进程未提权。WDDM 若报错误 5：先保存并退出 UE，再双击项目根目录 Launch-F6-WddmCapture.cmd，确认 Windows 权限提示；随后从 F6 开始采集。");
    return TEXT("当前进程已提权。复现前点“GPU 驻留/调度：开始”，等待显示“WDDM + UE 正在记录”；卡顿后导出整份 gpu- 文件夹，最多 180 秒。");
#else
    return TEXT("WDDM 驻留/调度采集仅支持 Windows。");
#endif
}

struct FFPSGpuTraceCapture::FState : TSharedFromThis<FFPSGpuTraceCapture::FState, ESPMode::ThreadSafe>
{
    FCriticalSection Lock;
    FString Directory, TracePath, SessionName, MetricsSession, CaptureId, Status = TEXT("正在启动 GPU 驻留/调度记录…"), StopReason;
    uint64 Generation = 0;
    TWeakObjectPtr<UGameInstance> OwningGameInstance;
    FString OriginGameInstance;
    TAtomic<bool> StopRequested{false}, Finished{false}, Collecting{false}, BundleComplete{false};
    TAtomic<bool> TraceStopNeeded{false}, TraceStopAccepted{false}, TraceInterrupted{false};
    FEvent* Wake = FPlatformProcess::GetSynchEventFromPool(false);
    FEvent* Done = FPlatformProcess::GetSynchEventFromPool(true);
    FEvent* TraceClosed = FPlatformProcess::GetSynchEventFromPool(true);
    FEvent* TraceStopHandled = FPlatformProcess::GetSynchEventFromPool(true);
    FDelegateHandle TraceClosedHandle;
    FTSTicker::FDelegateHandle TraceControlTicker;
    TQueue<FString, EQueueMode::Mpsc> PendingIdentities;
    TAtomic<int32> QueuedIdentities{0}, DroppedIdentities{0};
    TAtomic<int32> IdentityEtwWriteFailures{0};
    uint64 IdentityRows = 0;
    TSharedRef<FJsonObject> Manifest = MakeShared<FJsonObject>();
    TUniquePtr<IFileHandle> IdentityFile;
    TArray<FString> AddedChannels;
    // Initialized on the game thread before Run is launched, then immutable.
    bool bOwnsTrace = false, bDirectoryReady = false;
    // Game-thread-only trace control state; the worker only consumes the events/atomics.
    double TraceStopDeadline = 0.;
    bool bTraceControlCleaned = false;
#if PLATFORM_WINDOWS
    TRACEHANDLE Etw = 0;
    REGHANDLE IdentityProvider = 0;
    FPSGpuTrace::FEtwProperties Properties;
#endif
    ~FState()
    {
        FPlatformProcess::ReturnSynchEventToPool(Wake);
        FPlatformProcess::ReturnSynchEventToPool(Done);
        FPlatformProcess::ReturnSynchEventToPool(TraceClosed);
        FPlatformProcess::ReturnSynchEventToPool(TraceStopHandled);
    }
    void SetStatus(const FString& Text) { FScopeLock Guard(&Lock); Status = Text; }
    void Stop(const FString& Reason)
    {
        { FScopeLock Guard(&Lock); if (StopReason.IsEmpty()) StopReason = Reason; }
        StopRequested.Store(true); Wake->Trigger();
    }
    void Drain()
    {
        FString Batch, Line;
        while (PendingIdentities.Dequeue(Line))
        {
            --QueuedIdentities; Batch += Line; Batch += TEXT("\n"); ++IdentityRows;
            if (Batch.Len() >= 128 * 1024) break;
        }
        if (!Batch.IsEmpty() && IdentityFile)
        {
            const FTCHARToUTF8 Bytes(*Batch);
            if (!IdentityFile->Write(reinterpret_cast<const uint8*>(Bytes.Get()), Bytes.Length()))
            { Manifest->SetBoolField(TEXT("identity_write_failed"), true); Stop(TEXT("identity_write_failed")); }
        }
    }
    void ClockAnchor(const TCHAR* Label)
    {
        auto Row = MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("kind"), TEXT("clock_anchor"));
        Row->SetStringField(TEXT("label"), Label);
        Row->SetStringField(TEXT("capture_id"), CaptureId);
        Row->SetNumberField(TEXT("platform_seconds"), FPlatformTime::Seconds());
        Row->SetStringField(TEXT("utc"), FDateTime::UtcNow().ToIso8601());
#if PLATFORM_WINDOWS
        LARGE_INTEGER Qpc, Frequency; QueryPerformanceCounter(&Qpc); QueryPerformanceFrequency(&Frequency);
        Row->SetStringField(TEXT("qpc"), LexToString(Qpc.QuadPart));
        Row->SetStringField(TEXT("qpc_frequency"), LexToString(Frequency.QuadPart));
#endif
        const FString Text = FPSGpuTrace::Json(Row);
        TRACE_BOOKMARK(TEXT("FPS.GpuTrace.Clock %s"), *Text);
#if PLATFORM_WINDOWS
        if (IdentityProvider && EventWriteString(IdentityProvider, TRACE_LEVEL_INFORMATION, 1, *Text) != ERROR_SUCCESS)
            ++IdentityEtwWriteFailures;
#endif
        ++QueuedIdentities; PendingIdentities.Enqueue(Text);
        Manifest->SetObjectField(Label, Row);
    }
#if PLATFORM_WINDOWS
    void RecordWddmFailure(const TCHAR* Stage, ULONG Error, const FString& Details)
    {
        Manifest->SetStringField(TEXT("wddm_error_stage"), Stage);
        Manifest->SetNumberField(TEXT("wddm_error_code"), Error);
        FString Guidance;
        if (Error == ERROR_ACCESS_DENIED)
        {
            const auto& Permissions = FPSGpuTrace::ProcessPermissions();
            if (Permissions.Error == ERROR_SUCCESS && Permissions.bElevated)
            {
                Guidance = TEXT("当前进程已提权，但 Windows 仍拒绝 ETW 权限；请导出整份失败记录，保留权限及提供程序错误详情。");
                Manifest->SetStringField(TEXT("wddm_failure_action"), TEXT("export_elevated_access_denied_details"));
            }
            else
            {
                Guidance = TEXT("请先保存并退出 UE，再双击项目根目录 Launch-F6-WddmCapture.cmd，确认 Windows 权限提示后重新从 F6 开始；在当前进程内重试不会完成 UAC 提权。");
                Manifest->SetStringField(TEXT("wddm_failure_action"), TEXT("save_exit_launch_elevated_and_capture_again"));
            }
        }
        else
        {
            Guidance = TEXT("请导出整份失败记录，保留该阶段错误详情。");
            Manifest->SetStringField(TEXT("wddm_failure_action"), TEXT("export_provider_or_session_failure_details"));
        }
        SetStatus(FString::Printf(TEXT("WDDM 未就绪：%s；Windows 错误 %lu。%s"), *Details, Error, *Guidance));
    }
    ULONG Enable(const GUID& Provider, uint64 Keywords, bool bProcessOnly)
    {
        ULONG Pid = GetCurrentProcessId();
        EVENT_FILTER_DESCRIPTOR Filter{};
        Filter.Ptr = reinterpret_cast<ULONGLONG>(&Pid); Filter.Size = sizeof(Pid); Filter.Type = EVENT_FILTER_TYPE_PID;
        ENABLE_TRACE_PARAMETERS Params{}; Params.Version = ENABLE_TRACE_PARAMETERS_VERSION_2;
        if (bProcessOnly) { Params.EnableFilterDesc = &Filter; Params.FilterDescCount = 1; }
        return EnableTraceEx2(Etw, &Provider, EVENT_CONTROL_CODE_ENABLE_PROVIDER, TRACE_LEVEL_VERBOSE,
            Keywords, 0, 3000, &Params);
    }
    void CaptureState(const TCHAR* Phase)
    {
        auto Row = MakeShared<FJsonObject>();
        Row->SetNumberField(TEXT("dxgkrnl_error"), EnableTraceEx2(Etw, &FPSGpuTrace::DxgKrnl,
            EVENT_CONTROL_CODE_CAPTURE_STATE, TRACE_LEVEL_VERBOSE, FPSGpuTrace::DxgKeywords, 0, 3000, nullptr));
        Row->SetNumberField(TEXT("d3d12_error"), EnableTraceEx2(Etw, &FPSGpuTrace::D3D12,
            EVENT_CONTROL_CODE_CAPTURE_STATE, TRACE_LEVEL_VERBOSE, MAX_uint64, 0, 3000, nullptr));
        Row->SetStringField(TEXT("contract"), TEXT("Rundown requested; successful API return does not guarantee all pre-existing allocations were emitted."));
        Manifest->SetObjectField(Phase, Row);
    }
    bool StartEtw()
    {
        auto& P = Properties.Value;
        P.Wnode.BufferSize = sizeof(Properties); P.Wnode.Flags = WNODE_FLAG_TRACED_GUID;
        P.Wnode.ClientContext = 1; // QPC clock, matched by our in-stream anchors.
        P.LogFileMode = EVENT_TRACE_FILE_MODE_CIRCULAR; P.MaximumFileSize = 512;
        P.BufferSize = 256; P.MinimumBuffers = 64; P.MaximumBuffers = 128; P.FlushTimer = 1;
        P.LoggerNameOffset = offsetof(FPSGpuTrace::FEtwProperties, Session);
        P.LogFileNameOffset = offsetof(FPSGpuTrace::FEtwProperties, File);
        FCString::Strncpy(Properties.Session, *SessionName, UE_ARRAY_COUNT(Properties.Session));
        FCString::Strncpy(Properties.File, *(Directory / TEXT("wddm.etl")), UE_ARRAY_COUNT(Properties.File));
        const ULONG Error = StartTraceW(&Etw, *SessionName, &P);
        Manifest->SetNumberField(TEXT("etw_start_error"), Error);
        if (Error != ERROR_SUCCESS)
        {
            Etw = 0;
            RecordWddmFailure(TEXT("StartTraceW"), Error, TEXT("创建 ETW 会话失败"));
            return false;
        }
        const ULONG Dxg = Enable(FPSGpuTrace::DxgKrnl, FPSGpuTrace::DxgKeywords, false);
        const ULONG D3d = Enable(FPSGpuTrace::D3D12, MAX_uint64, true);
        const ULONG Umd = Enable(FPSGpuTrace::Umd, 1, true);
        Manifest->SetNumberField(TEXT("dxgkrnl_enable_error"), Dxg);
        Manifest->SetNumberField(TEXT("d3d12_enable_error"), D3d);
        Manifest->SetNumberField(TEXT("umd_mapping_enable_error"), Umd);
        const ULONG Register = EventRegister(&FPSGpuTrace::Identity, nullptr, nullptr, &IdentityProvider);
        Manifest->SetNumberField(TEXT("identity_provider_register_error"), Register);
        const ULONG IdentityEnable = Register == ERROR_SUCCESS ? Enable(FPSGpuTrace::Identity, 1, true) : Register;
        Manifest->SetNumberField(TEXT("identity_provider_enable_error"), IdentityEnable);
        // Mapping and identity events are necessary for the advertised joined
        // residency bundle too. A partial provider set must never be green.
        if (Dxg != ERROR_SUCCESS || D3d != ERROR_SUCCESS || Umd != ERROR_SUCCESS || IdentityEnable != ERROR_SUCCESS)
        {
            const TCHAR* Stage = Dxg != ERROR_SUCCESS ? TEXT("EnableTraceEx2.DxgKrnl")
                : D3d != ERROR_SUCCESS ? TEXT("EnableTraceEx2.D3D12")
                : Umd != ERROR_SUCCESS ? TEXT("EnableTraceEx2.UMD")
                : Register != ERROR_SUCCESS ? TEXT("EventRegister.Identity") : TEXT("EnableTraceEx2.Identity");
            const ULONG ProviderError = Dxg != ERROR_SUCCESS ? Dxg : D3d != ERROR_SUCCESS ? D3d
                : Umd != ERROR_SUCCESS ? Umd : IdentityEnable;
            RecordWddmFailure(Stage, ProviderError, FString::Printf(
                TEXT("提供程序未全部开启（DxgKrnl=%lu，D3D12=%lu，UMD=%lu，身份记录=%lu）"), Dxg, D3d, Umd, IdentityEnable));
            return false;
        }
        CaptureState(TEXT("rundown_at_start"));
        return true;
    }
#endif
    bool StartUeTrace()
    {
        check(IsInGameThread());
        // Start synchronously broadcasts OnTraceStarted. AudioInsights listeners
        // enumerate in-memory assets and must run on the game thread.
        if (FTraceAuxiliary::IsConnected() || !FTraceAuxiliary::GetTraceDestinationString().IsEmpty())
        {
            Manifest->SetStringField(TEXT("ue_trace_status"), TEXT("another_trace_active"));
            SetStatus(TEXT("已有 UE Trace 正在记录；未接管它。停止该记录后再开始 GPU 驻留/调度。"));
            return false;
        }
        TStringBuilder<512> Previous;
        FTraceAuxiliary::GetActiveChannelsString(Previous);
        TArray<FString> Enabled; FString(Previous.ToString()).ParseIntoArray(Enabled, TEXT(","), true);
        for (FString& Name : Enabled) Name.TrimStartAndEndInline();
        for (const TCHAR* Name : {TEXT("cpu"), TEXT("frame"), TEXT("gpu"), TEXT("counters"), TEXT("bookmark")})
            if (!Enabled.ContainsByPredicate([Name](const FString& Item){return Item.Equals(Name, ESearchCase::IgnoreCase);})) AddedChannels.Add(Name);
        FTraceAuxiliary::FOptions Options; Options.bExcludeTail = true;
        const TWeakPtr<FState, ESPMode::ThreadSafe> WeakState = AsShared();
        TraceClosedHandle = FTraceAuxiliary::OnClosed.AddLambda([WeakState]
        {
            if (auto Pinned = WeakState.Pin()) Pinned->TraceClosed->Trigger();
        });
        bOwnsTrace = FTraceAuxiliary::Start(FTraceAuxiliary::EConnectionType::File, *TracePath,
            TEXT("cpu,frame,gpu,counters,bookmark"), &Options)
            && FPaths::IsSamePath(FTraceAuxiliary::GetTraceDestinationString(), TracePath);
        Manifest->SetStringField(TEXT("ue_trace_status"), bOwnsTrace ? TEXT("recording") : TEXT("start_failed"));
        if (!bOwnsTrace)
        {
            if (!FTraceAuxiliary::IsConnected() && FTraceAuxiliary::GetTraceDestinationString().IsEmpty())
                for (const FString& Channel : AddedChannels) FTraceAuxiliary::DisableChannels(*Channel);
            SetStatus(TEXT("UE GPU Trace 启动失败；可导出失败详情。"));
        }
        return bOwnsTrace;
    }
    void CleanupTraceControl()
    {
        check(IsInGameThread());
        if (bTraceControlCleaned) return;
        bTraceControlCleaned = true;
        if (TraceClosedHandle.IsValid())
        {
            FTraceAuxiliary::OnClosed.Remove(TraceClosedHandle);
            TraceClosedHandle.Reset();
        }
        if (bOwnsTrace && FTraceAuxiliary::GetTraceDestinationString().IsEmpty())
            for (const FString& Channel : AddedChannels) FTraceAuxiliary::DisableChannels(*Channel);
    }
    bool TickTraceControl()
    {
        check(IsInGameThread());
        if (Finished.Load()) { TraceStopHandled->Trigger(); CleanupTraceControl(); return false; }
        if (!bOwnsTrace) { TraceStopHandled->Trigger(); CleanupTraceControl(); return true; }
        if (!TraceStopHandled->Wait(0))
        {
            // Never stop a trace opened by a different owner after ours ended.
            if (!FPaths::IsSamePath(FTraceAuxiliary::GetTraceDestinationString(), TracePath))
            {
                TraceInterrupted.Store(true);
                Stop(TEXT("ue_trace_interrupted"));
                TraceStopHandled->Trigger();
            }
            else if (TraceStopNeeded.Load())
            {
                // Stop also broadcasts listeners synchronously. Retry a pending
                // writer connection on later ticks; never wait here during play.
                const double Now = FPlatformTime::Seconds();
                if (TraceStopDeadline == 0.) TraceStopDeadline = Now + 3.;
                const bool bAccepted = FTraceAuxiliary::Stop();
                if (bAccepted || TraceClosed->Wait(0) || Now >= TraceStopDeadline)
                {
                    TraceStopAccepted.Store(bAccepted);
                    TraceStopHandled->Trigger();
                }
            }
        }
        if (TraceStopHandled->Wait(0) && TraceClosed->Wait(0)) CleanupTraceControl();
        return true;
    }
    void FinishAtEngineExit()
    {
        check(IsInGameThread());
        Stop(TEXT("engine_exit"));
        // The normal ticker will no longer advance while OnEnginePreExit waits.
        // Service our own stop control before joining the I/O worker; no queued
        // game-thread task is required for that worker to finish.
        while (!TraceStopHandled->Wait(0))
        {
            TickTraceControl();
            TraceStopHandled->Wait(10);
        }
        Done->Wait();
        CleanupTraceControl();
        FTSTicker::RemoveTicker(TraceControlTicker);
    }
    void Run()
    {
        Manifest->SetNumberField(TEXT("version"), 5);
#if PLATFORM_WINDOWS
        const auto& Permissions = FPSGpuTrace::ProcessPermissions();
        Manifest->SetNumberField(TEXT("windows_token_query_error"), Permissions.Error);
        if (Permissions.Error == ERROR_SUCCESS) Manifest->SetBoolField(TEXT("process_elevated"), Permissions.bElevated);
        else Manifest->SetField(TEXT("process_elevated"), MakeShared<FJsonValueNull>());
        Manifest->SetStringField(TEXT("elevated_launch_entry"), FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Launch-F6-WddmCapture.cmd")));
        Manifest->SetStringField(TEXT("permission_contract"), TEXT("Read-only process-token query. ETW API return codes determine access; a non-elevated process may have explicit ETW permissions. This recorder never elevates, relaunches, changes group membership or provider/session ACLs."));
#endif
        Manifest->SetStringField(TEXT("trace_control_thread"), TEXT("game_thread"));
        Manifest->SetStringField(TEXT("origin_game_instance"), OriginGameInstance);
        Manifest->SetStringField(TEXT("lifetime_contract"), TEXT("Explicit process-wide trace retained by its initiating GameInstance across World travel and frame-sample resets. metrics_session_id/generation identify the origin World, not every later exported snapshot. Match snapshot and buffer times to the capture interval; component paths identify their World. Ends on explicit stop/export, limits, initiating GameInstance teardown or engine exit."));
        Manifest->SetStringField(TEXT("capture_id"), CaptureId);
        Manifest->SetStringField(TEXT("etw_session_name"), SessionName);
        Manifest->SetStringField(TEXT("metrics_session_id"), MetricsSession);
        Manifest->SetStringField(TEXT("metrics_generation"), LexToString(Generation));
        Manifest->SetNumberField(TEXT("process_id"), FPlatformProcess::GetCurrentProcessId());
        Manifest->SetStringField(TEXT("rhi"), GDynamicRHI ? GDynamicRHI->GetName() : TEXT("unavailable"));
        Manifest->SetStringField(TEXT("directory"), Directory);
        Manifest->SetStringField(TEXT("contract"), TEXT("Explicit bounded diagnostic capture. ETL is system-wide GPU metadata; D3D12/UMD/identity providers filtered to this PID. ETW events must be joined by PID, adapter, GPU VA/resource lifetime and QPC; no physical residency is inferred from UE's resident flag. Capture has overhead. A successful provider enable is not proof of complete event coverage. Circular ETL can overwrite its beginning without counting that as lost events. F6's displayed snapshot can be older than this capture; compare timestamps and generation."));
        Manifest->SetNumberField(TEXT("etw_circular_limit_mb"), 512);
        Manifest->SetNumberField(TEXT("maximum_seconds"), FPSGpuTrace::MaxSeconds);
        Manifest->SetNumberField(TEXT("ue_trace_limit_bytes"), double(FPSGpuTrace::MaxUeBytes));
        Manifest->SetStringField(TEXT("dxgkrnl_keywords"), FPSGpuTrace::Hex(0x043084c7));
        bool bStarted = bDirectoryReady;
        if (bStarted) IdentityFile.Reset(FPlatformFileManager::Get().GetPlatformFile().OpenWrite(*(Directory / TEXT("buffers.jsonl"))));
        bStarted &= IdentityFile.IsValid();
        if (!bStarted) SetStatus(TEXT("无法创建 GPU 记录目录或 buffers.jsonl；请检查保存路径。"));
        bStarted &= bOwnsTrace;
        bool bWddmReady = false, bEtwSessionStarted = false;
        FString WddmFailure;
#if PLATFORM_WINDOWS && !UE_BUILD_SHIPPING
        if (bStarted && !StopRequested.Load())
        {
            bWddmReady = StartEtw();
            bEtwSessionStarted = Etw != 0;
            if (!bWddmReady)
            {
                FScopeLock Guard(&Lock);
                WddmFailure = Status;
                Manifest->SetStringField(TEXT("wddm_status_text"), WddmFailure);
            }
        }
        // UE tracing was started on the game thread before this worker. ETW
        // failure must still preserve its timeline and buffer identities.
#else
        bStarted = false; SetStatus(TEXT("此构建不支持 Windows GPU 驻留/调度记录。"));
#endif
        Manifest->SetBoolField(TEXT("wddm_providers_ready"), bWddmReady);
        Manifest->SetStringField(TEXT("capture_mode"), !bStarted ? TEXT("start_failed")
            : bWddmReady ? TEXT("wddm_and_ue_trace") : TEXT("ue_trace_only"));
        ClockAnchor(TEXT("capture_start"));
        const double StartSeconds = FPlatformTime::Seconds();
        if (bStarted && !StopRequested.Load())
        {
            Collecting.Store(true);
            SetStatus(bWddmReady
                ? TEXT("WDDM + UE 正在记录（含缓冲身份，最多 180 秒）；复现卡顿后直接导出记录。")
                : FString::Printf(TEXT("仅 UE GPU 时间线/缓冲身份记录中（最多 180 秒，缺少 WDDM）。%s"), *WddmFailure));
            double NextSizeCheck = 0.;
            while (!StopRequested.Load())
            {
                Drain();
                const double Now = FPlatformTime::Seconds();
                if (Now - StartSeconds >= FPSGpuTrace::MaxSeconds) { Stop(TEXT("duration_limit")); break; }
                if (Now >= NextSizeCheck)
                {
                    NextSizeCheck = Now + 1.;
                    if (IFileManager::Get().FileSize(*TracePath) >= FPSGpuTrace::MaxUeBytes) { Stop(TEXT("ue_file_size_limit")); break; }
                }
                Wake->Wait(250);
            }
        }
        { FScopeLock Guard(&Lock); Collecting.Store(false); }
        ClockAnchor(TEXT("capture_stop"));
        TraceStopNeeded.Store(true);
        bool bTraceSealed = false, bEtwSealed = false;
        if (bOwnsTrace)
        {
            TraceStopHandled->Wait();
            if (!TraceInterrupted.Load())
            {
                Manifest->SetBoolField(TEXT("ue_trace_stop_ok"), TraceStopAccepted.Load());
                bTraceSealed = TraceClosed->Wait(10000);
                Manifest->SetBoolField(TEXT("ue_trace_file_closed"), bTraceSealed);
                Manifest->SetStringField(TEXT("ue_trace_status"), bTraceSealed ? TEXT("closed") : TEXT("close_not_confirmed"));
            }
            else Manifest->SetStringField(TEXT("ue_trace_status"), TEXT("interrupted_by_external_trace_change"));
        }
#if PLATFORM_WINDOWS
        if (Etw)
        {
            CaptureState(TEXT("rundown_at_stop"));
            ULONG Error = ControlTraceW(Etw, nullptr, &Properties.Value, EVENT_TRACE_CONTROL_STOP);
            if (Error != ERROR_SUCCESS && Error != ERROR_WMI_INSTANCE_NOT_FOUND)
            {
                Manifest->SetNumberField(TEXT("etw_first_stop_error"), Error);
                Error = ControlTraceW(0, *SessionName, &Properties.Value, EVENT_TRACE_CONTROL_STOP);
            }
            Manifest->SetNumberField(TEXT("etw_stop_error"), Error);
            Manifest->SetBoolField(TEXT("etw_stop_statistics_valid"), Error == ERROR_SUCCESS);
            Manifest->SetNumberField(TEXT("events_lost"), Properties.Value.EventsLost);
            Manifest->SetNumberField(TEXT("log_buffers_lost"), Properties.Value.LogBuffersLost);
            Manifest->SetNumberField(TEXT("real_time_buffers_lost"), Properties.Value.RealTimeBuffersLost);
            Manifest->SetNumberField(TEXT("buffers_written"), Properties.Value.BuffersWritten);
            bEtwSealed = Error == ERROR_SUCCESS;
            Etw = 0;
        }
        { FScopeLock Guard(&Lock); if (IdentityProvider) EventUnregister(IdentityProvider); IdentityProvider = 0; }
#endif
        while (QueuedIdentities.Load() > 0) Drain();
        bool bIdentityFlushed = false;
        if (IdentityFile) { bIdentityFlushed = IdentityFile->Flush(); IdentityFile.Reset(); }
        { FScopeLock Guard(&Lock); Manifest->SetStringField(TEXT("stop_reason"), StopReason.IsEmpty() ? TEXT("start_failed") : StopReason); }
        Manifest->SetNumberField(TEXT("identity_rows"), double(IdentityRows));
        Manifest->SetNumberField(TEXT("identity_rows_dropped"), DroppedIdentities.Load());
        Manifest->SetNumberField(TEXT("identity_etw_write_failures"), IdentityEtwWriteFailures.Load());
        Manifest->SetBoolField(TEXT("identity_file_flushed"), bIdentityFlushed);
        bool bIdentityWriteFailed = false;
        Manifest->TryGetBoolField(TEXT("identity_write_failed"), bIdentityWriteFailed);
        const bool bAvailableFilesSealed = bStarted && bTraceSealed
            && (!bEtwSessionStarted || bEtwSealed) && bIdentityFlushed && !bIdentityWriteFailed;
        const bool bFilesSealed = bAvailableFilesSealed && bWddmReady && bEtwSealed;
        Manifest->SetBoolField(TEXT("available_files_finalized"), bAvailableFilesSealed);
        Manifest->SetBoolField(TEXT("files_finalized"), bFilesSealed);
        auto Files = MakeShared<FJsonObject>();
        for (const TCHAR* Name : {TEXT("wddm.etl"), TEXT("engine.utrace"), TEXT("buffers.jsonl")})
        {
            auto File = MakeShared<FJsonObject>();
            File->SetStringField(TEXT("relative_path"), Name);
            File->SetNumberField(TEXT("bytes"), double(IFileManager::Get().FileSize(*(Directory / Name))));
            Files->SetObjectField(Name, File);
        }
        Manifest->SetObjectField(TEXT("files"), Files);
        bool bLost = DroppedIdentities.Load() != 0 || IdentityEtwWriteFailures.Load() != 0;
        double Lost = 0;
        for (const TCHAR* Name : {TEXT("events_lost"), TEXT("log_buffers_lost"), TEXT("real_time_buffers_lost")})
            if (Manifest->TryGetNumberField(Name, Lost) && Lost > 0) bLost = true;
        if (bStarted)
        {
            SetStatus(!bAvailableFilesSealed ? TEXT("GPU 记录收尾不完整；请保留整份文件夹中的失败详情。")
                : !bWddmReady ? FString::Printf(TEXT("已保存 UE GPU 时间线/缓冲身份，缺少完整 WDDM%s。%s"),
                    bLost ? TEXT("，且存在丢失事件") : TEXT(""), *WddmFailure)
                : bLost ? TEXT("GPU 记录已停止，存在丢失事件；请导出整份文件夹。")
                : TEXT("GPU 驻留/调度记录已停止；导出时请保留整份文件夹。"));
        }
        { FScopeLock Guard(&Lock); Manifest->SetStringField(TEXT("status_text"), Status); }
        const bool bManifestSaved = FFileHelper::SaveStringToFile(FPSGpuTrace::Json(Manifest), *(Directory / TEXT("manifest.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        if (!bManifestSaved)
        {
            Manifest->SetBoolField(TEXT("manifest_write_failed"), true);
            SetStatus(TEXT("GPU 记录清单写入失败；F6 导出 JSON 会附带详情。"));
            Manifest->SetStringField(TEXT("status_text"), Status);
        }
        BundleComplete.Store(bManifestSaved && bFilesSealed && !bLost);
        Finished.Store(true); Done->Trigger();
    }
};

FFPSGpuTraceCapture::FFPSGpuTraceCapture() : State(MakeShared<FState, ESPMode::ThreadSafe>()) {}
FFPSGpuTraceCapture::~FFPSGpuTraceCapture() { State->Stop(TEXT("owner_released")); }

TSharedRef<FFPSGpuTraceCapture, ESPMode::ThreadSafe> FFPSGpuTraceCapture::Start(const FString& Session, uint64 Generation, UGameInstance* GameInstance)
{
    check(IsInGameThread());
    TSharedPtr<FFPSGpuTraceCapture, ESPMode::ThreadSafe> Previous;
    {
        FScopeLock Guard(&FPSGpuTrace::OwnerLock);
        if (FPSGpuTrace::Owner && FPSGpuTrace::Owner->IsRunning()) return FPSGpuTrace::Owner.ToSharedRef();
        Previous = FPSGpuTrace::Owner;
    }
    if (Previous)
    {
        Previous->State->CleanupTraceControl();
        FTSTicker::RemoveTicker(Previous->State->TraceControlTicker);
    }
    TSharedPtr<FFPSGpuTraceCapture, ESPMode::ThreadSafe> Capture = MakeShareable(new FFPSGpuTraceCapture());
    auto S = Capture->State;
    S->OwningGameInstance = GameInstance;
    S->OriginGameInstance = GetPathNameSafe(GameInstance);
    S->MetricsSession = Session; S->Generation = Generation;
    S->CaptureId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
    S->SessionName = FString::Printf(TEXT("FPSGAME-GPU-%u-%s"), FPlatformProcess::GetCurrentProcessId(), *S->CaptureId);
    S->Directory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("PerformanceReports") / (TEXT("gpu-") + S->CaptureId));
    S->TracePath = S->Directory / TEXT("engine.utrace");
    { FScopeLock Guard(&FPSGpuTrace::OwnerLock); FPSGpuTrace::Owner = Capture; }
    static const FDelegateHandle ExitHandle = FCoreDelegates::OnEnginePreExit.AddLambda([]
    {
        TSharedPtr<FFPSGpuTraceCapture, ESPMode::ThreadSafe> Active;
        { FScopeLock Lock(&FPSGpuTrace::OwnerLock); Active = FPSGpuTrace::Owner; }
        if (Active) Active->State->FinishAtEngineExit();
    });
    S->bDirectoryReady = IFileManager::Get().MakeDirectory(*S->Directory, true);
#if PLATFORM_WINDOWS && !UE_BUILD_SHIPPING
    if (S->bDirectoryReady) S->StartUeTrace();
#endif
    const TWeakPtr<FState, ESPMode::ThreadSafe> WeakState = S;
    S->TraceControlTicker = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([WeakState](float)
    {
        if (auto Pinned = WeakState.Pin()) return Pinned->TickTraceControl();
        return false;
    }), .05f);
    // The game thread owns trace control and listener notifications. One worker
    // owns ETW, file I/O, close waits and the bounded identity queue.
    Async(EAsyncExecution::Thread, [S] { S->Run(); });
    return Capture.ToSharedRef();
}

void FFPSGpuTraceCapture::RequestStop(const FString& Reason) { State->Stop(Reason); }
bool FFPSGpuTraceCapture::IsRunning() const { return !State->Finished.Load(); }
bool FFPSGpuTraceCapture::IsCollectingBuffers() const { return State->Collecting.Load(); }
bool FFPSGpuTraceCapture::HasCompleteBundle() const { return State->Finished.Load() && State->BundleComplete.Load(); }
bool FFPSGpuTraceCapture::IsOwnedBy(const UGameInstance* GameInstance) const
{
    check(IsInGameThread());
    return GameInstance && State->OwningGameInstance.Get() == GameInstance;
}
FString FFPSGpuTraceCapture::StatusText() const { FScopeLock Guard(&State->Lock); return State->Status; }
FString FFPSGpuTraceCapture::GetDirectory() const { return State->Directory; }
TSharedPtr<FJsonObject> FFPSGpuTraceCapture::FinishForExport()
{
    State->Stop(TEXT("F6_export")); State->Done->Wait();
    return MakeShared<FJsonObject>(*State->Manifest);
}

TSharedRef<FJsonObject> FFPSGpuTraceCapture::ObserveBuffer(FRHIBuffer* Buffer, const FString& Component,
    const FString& Asset, const TCHAR* Role, uint64 GameFrame, uint64 RenderFrame)
{
    auto Row = MakeShared<FJsonObject>();
    Row->SetStringField(TEXT("kind"), TEXT("buffer_observation"));
    Row->SetStringField(TEXT("capture_id"), State->CaptureId);
    Row->SetStringField(TEXT("component"), Component); Row->SetStringField(TEXT("asset"), Asset);
    Row->SetStringField(TEXT("role"), Role);
    Row->SetStringField(TEXT("game_frame"), LexToString(GameFrame)); Row->SetStringField(TEXT("render_frame"), LexToString(RenderFrame));
    Row->SetNumberField(TEXT("platform_seconds"), FPlatformTime::Seconds());
    Row->SetBoolField(TEXT("buffer_present"), Buffer != nullptr);
    if (Buffer)
    {
        Row->SetStringField(TEXT("rhi_identity"), FPSGpuTrace::Hex(reinterpret_cast<UPTRINT>(Buffer)));
        Row->SetNumberField(TEXT("logical_buffer_bytes"), double(Buffer->GetSize()));
#if RHI_ENABLE_RESOURCE_INFO
        FRHIResourceInfo Info;
        if (Buffer->GetResourceInfo(Info)) Row->SetBoolField(TEXT("ue_resident_flag_not_physical_segment"), Info.bResident);
#endif
    }
#if PLATFORM_WINDOWS
    LARGE_INTEGER Qpc; QueryPerformanceCounter(&Qpc);
    Row->SetStringField(TEXT("qpc"), LexToString(Qpc.QuadPart));
    if (Buffer && IsRHID3D12())
    {
        auto* Rhi = GetID3D12DynamicRHI();
        ID3D12Resource* Native = Rhi->RHIGetResource(Buffer);
        const uint32 DeviceIndex = Rhi->RHIGetResourceDeviceIndex(Buffer);
        const LUID Adapter = Rhi->RHIGetDevice(DeviceIndex)->GetAdapterLuid();
        Row->SetStringField(TEXT("adapter_luid"), FPSGpuTrace::Hex((uint64(uint32(Adapter.HighPart)) << 32) | Adapter.LowPart));
        Row->SetNumberField(TEXT("device_index"), DeviceIndex);
        Row->SetBoolField(TEXT("placed_resource"), Rhi->RHIIsResourcePlaced(Buffer));
        Row->SetStringField(TEXT("native_resource_identity"), FPSGpuTrace::Hex(reinterpret_cast<UPTRINT>(Native)));
        if (Native)
        {
            const auto Desc = Native->GetDesc();
            Row->SetStringField(TEXT("native_resource_base_gpu_va"), FPSGpuTrace::Hex(Native->GetGPUVirtualAddress()));
            Row->SetNumberField(TEXT("native_resource_width"), double(Desc.Width));
            // Shared read-only RHI buffers can be suballocated within this native
            // resource. The public RHI API does not expose their byte offset.
            Row->SetBoolField(TEXT("logical_range_matches_native_resource"), Desc.Width == Buffer->GetSize());
            D3D12_HEAP_PROPERTIES Props{}; D3D12_HEAP_FLAGS Flags{};
            const HRESULT Result = Native->GetHeapProperties(&Props, &Flags);
            Row->SetStringField(TEXT("heap_properties_hresult"), FPSGpuTrace::Hex(uint32(Result)));
            if (SUCCEEDED(Result))
            {
                Row->SetNumberField(TEXT("heap_type"), uint32(Props.Type));
                Row->SetNumberField(TEXT("heap_memory_pool_preference"), uint32(Props.MemoryPoolPreference));
                Row->SetStringField(TEXT("heap_flags"), FPSGpuTrace::Hex(uint32(Flags)));
            }
        }
    }
#endif
    Row->SetField(TEXT("physical_segment"), MakeShared<FJsonValueNull>());
    const FString Text = FPSGpuTrace::Json(Row);
    FScopeLock Guard(&State->Lock);
    if (State->Collecting.Load())
    {
        TRACE_BOOKMARK(TEXT("FPS.GpuTrace.Buffer %s"), *Text);
#if PLATFORM_WINDOWS
        if (State->IdentityProvider && EventWriteString(State->IdentityProvider, TRACE_LEVEL_INFORMATION, 1, *Text) != ERROR_SUCCESS)
            ++State->IdentityEtwWriteFailures;
#endif
        if (State->QueuedIdentities.Load() < FPSGpuTrace::MaxQueuedIdentities)
        { ++State->QueuedIdentities; State->PendingIdentities.Enqueue(Text); }
        else ++State->DroppedIdentities;
    }
    return Row;
}
