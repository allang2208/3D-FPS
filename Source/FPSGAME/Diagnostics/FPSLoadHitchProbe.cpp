// Sync-load hitch probe implementation. See FPSLoadHitchProbe.h for context.
//
// UObjectGlobals broadcasts FCoreDelegates::OnSyncLoadPackage on entry only, so
// this probe pairs the entry with the next game-thread tick: the load is by then
// either finished or still blocking, and both cases are worth reporting. Nested
// loads keep the outermost duration, so the number matches what CsvProfiler
// shows as FileIO/GameThread/AsyncLoadingTime.

#include "FPSLoadHitchProbe.h"

#include "HAL/IConsoleManager.h"
#include "HAL/PlatformStackWalk.h"
#include "HAL/PlatformTime.h"
#include "Misc/CoreDelegates.h"
#include "Misc/CommandLine.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

namespace FPSLoadHitchProbePrivate
{
    int32 GEnabled = 0;
    float GThresholdMs = 25.0f;
    int32 GStackDepth = 16;
    int32 GMaxEvents = 20000;

    FAutoConsoleVariableRef CVarEnabled(
        TEXT("fps.diag.LoadHitch"),
        GEnabled,
        TEXT("1 = record game-thread synchronous package loads and their caller stacks.\n")
        TEXT("Evidence goes to Saved/Profiling/LoadHitch/. Off by default."),
        ECVF_Default);

    FAutoConsoleVariableRef CVarThreshold(
        TEXT("fps.diag.LoadHitchThresholdMs"),
        GThresholdMs,
        TEXT("Only loads at or above this duration (in ms) are written to the evidence file."),
        ECVF_Default);

    FAutoConsoleVariableRef CVarStackDepth(
        TEXT("fps.diag.LoadHitchStackDepth"),
        GStackDepth,
        TEXT("Callstack depth captured for a load above the threshold; 0 disables stack capture."),
        ECVF_Default);

    /** Set by the fpssyncload console command; see EnableFromCommand(). */
    bool GLogEveryEntry = false;

    enum { MaxCapturedFrames = 24 };
    using FFrameArray = TArray<uint64, TInlineAllocator<MaxCapturedFrames>>;


    struct FPendingLoad
    {
        FString Package;
        double StartSeconds = 0.0;
        FFrameArray Frames;
    };

    /** Last recorded load; closed by the next tick so its duration is known. */
    FPendingLoad Pending;

    TArray<FString> PendingLines;
    FString EvidencePath;
    bool bBound = false;
    int32 GEntryCount = 0;
    int32 GWrittenCount = 0;

    FString ResolveEvidencePath()
    {
        // Capture runs pass -ColdSteelProfile=<name>; reuse it so evidence lands
        // with that run's CSV instead of overwriting the previous run's file.
        FString Profile;
        if (!FParse::Value(FCommandLine::Get(), TEXT("ColdSteelProfile="), Profile) || Profile.IsEmpty())
        {
            Profile = FString::Printf(TEXT("Runtime-%s"), *FDateTime::Now().ToString(TEXT("%Y%m%d-%H%M%S")));
        }
        return FPaths::ProjectSavedDir() / TEXT("Profiling/LoadHitch") / (Profile + TEXT(".log"));
    }

    void FlushEvidence()
    {
        if (PendingLines.Num() == 0)
        {
            return;
        }
        if (EvidencePath.IsEmpty())
        {
            EvidencePath = ResolveEvidencePath();
        }
        FFileHelper::SaveStringArrayToFile(PendingLines, *EvidencePath,
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,
            &IFileManager::Get(), FILEWRITE_Append);
        GWrittenCount += PendingLines.Num();
        PendingLines.Reset();
    }

    /** Module name -> loaded image base, so addresses can be reported as offsets
     *  that resolve against this build's PDBs (ASLR makes raw PCs useless). */
    TMap<FString, uint64> ModuleBases;

    void BuildModuleMap()
    {
        ModuleBases.Reset();
        // GetProcessModuleSignatures reports image base + size without resolving
        // symbols, which is exactly what offsets against this build's PDBs need.
        const int32 ModuleCount = FPlatformStackWalk::GetProcessModuleCount();
        TArray<FStackWalkModuleInfo> Modules;
        Modules.SetNumZeroed(FMath::Max(ModuleCount, 1));
        const int32 Valid = FPlatformStackWalk::GetProcessModuleSignatures(Modules.GetData(), Modules.Num());
        Modules.SetNum(FMath::Clamp(Valid, 0, Modules.Num()));
        for (const FStackWalkModuleInfo& Module : Modules)
        {
            const FString Image(Module.ImageName);
            if (Module.BaseOfImage != 0 && !Image.IsEmpty())
            {
                ModuleBases.Add(FPaths::GetCleanFilename(Image), Module.BaseOfImage);
            }
        }
    }

    void CaptureCallerStack(FFrameArray& OutFrames)
    {
        const int32 RequestedDepth = FMath::Clamp(GStackDepth, 1, MaxCapturedFrames);
        OutFrames.SetNumZeroed(RequestedDepth);
        const uint32 NumFrames = FPlatformStackWalk::CaptureStackBackTrace(OutFrames.GetData(), RequestedDepth);
        OutFrames.SetNum(NumFrames);
    }

    void FormatStack(const FFrameArray& Frames, FString& OutText)
    {
        for (int32 Index = 0; Index < Frames.Num(); ++Index)
        {
            FProgramCounterSymbolInfo Info;
            FPlatformStackWalk::ProgramCounterToSymbolInfo(Frames[Index], Info);
            const FString ModuleName = FPaths::GetCleanFilename(ANSI_TO_TCHAR(Info.ModuleName));
            const uint64* Base = ModuleBases.Find(ModuleName);
            OutText += FString::Printf(TEXT("\n      [%02d] %s +0x%llx"),
                Index, *ModuleName, Base ? (Frames[Index] - *Base) : Info.OffsetInModule);
        }
    }

    void RecordLoad(const FPendingLoad& Load, double ElapsedMs, const FFrameArray& Frames)
    {
        if (GEnabled == 0 || PendingLines.Num() >= GMaxEvents)
        {
            return;
        }
        FString Line = FString::Printf(TEXT("[%.3f] load %8.1f ms  %s"),
            Load.StartSeconds, ElapsedMs, *Load.Package);
        FormatStack(Load.Frames, Line);
        PendingLines.Add(MoveTemp(Line));
        ++GWrittenCount;
    }

    /**
     * UObjectGlobals broadcasts OnSyncLoadPackage on entry only, so a load's own
     * duration is not known here. Every entry therefore stores its caller stack
     * cheaply; the tick then closes the interval and reports it with the stack
     * captured at the moment the load started, which is where the culprit lives.
     */
    void OnSyncLoadPackage(const FString& PackageName)
    {
        ++GEntryCount;
        if (GEnabled == 0 || GMaxEvents <= 0)
        {
            return;
        }
        const double Now = FPlatformTime::Seconds();
        if (!Pending.Package.IsEmpty() && Pending.StartSeconds > 0.0)
        {
            const double GapMs = (Now - Pending.StartSeconds) * 1000.0;
            if (GLogEveryEntry || GapMs >= GThresholdMs)
            {
                RecordLoad(Pending, GapMs, Pending.Frames);
            }
        }

        Pending.Package = PackageName;
        Pending.StartSeconds = Now;
        CaptureCallerStack(Pending.Frames);
    }

    void OnBeginFrame()
    {
        FlushEvidence();
    }

    void OnLoadHitchCVarChanged(IConsoleVariable* Variable)
    {
        // Confirms from the log that the diagnostic was actually switched on for
        // this run, instead of silently recording nothing.
        UE_LOG(LogTemp, Display, TEXT("LoadHitchProbe cvar fps.diag.LoadHitch = %s (entries seen so far: %d)"),
            *Variable->GetString(), GEntryCount);
    }

    void EnableFromCommand(const TArray<FString>& Args)
    {
        const float Threshold = Args.Num() > 0 ? FCString::Atof(*Args[0]) : GThresholdMs;
        GThresholdMs = Threshold > 0.0f ? Threshold : GThresholdMs;
        GLogEveryEntry = Args.Num() > 1 && FCString::Atoi(*Args[1]) != 0;
        GEnabled = 1;
        UE_LOG(LogTemp, Display,
            TEXT("LoadHitchProbe ENABLED: threshold %.1f ms, everyEntry=%d, stack %d, %d entries seen since start"),
            GThresholdMs, GLogEveryEntry ? 1 : 0, GStackDepth, GEntryCount);
    }

    FAutoConsoleCommand EnableCommand(
        TEXT("fpssyncload"),
        TEXT("fpssyncload [thresholdMs] [everyEntry] - record game-thread sync loads to Saved/Profiling/LoadHitch/."),
        FConsoleCommandWithArgsDelegate::CreateStatic(&EnableFromCommand));
}

void FFPSLoadHitchProbe::Startup()
{
    using namespace FPSLoadHitchProbePrivate;
    if (bBound)
    {
        return;
    }
    FCoreDelegates::OnSyncLoadPackage.AddStatic(&OnSyncLoadPackage);
    FCoreDelegates::OnBeginFrame.AddStatic(&OnBeginFrame);
    bBound = true;
    BuildModuleMap();
    if (IConsoleVariable* EnabledVar = IConsoleManager::Get().FindConsoleVariable(TEXT("fps.diag.LoadHitch")))
    {
        EnabledVar->SetOnChangedCallback(FConsoleVariableDelegate::CreateStatic(&OnLoadHitchCVarChanged));
    }
    UE_LOG(LogTemp, Display,
        TEXT("LoadHitchProbe ready: 'fpssyncload [thresholdMs]' enables it (%d modules mapped); evidence in Saved/Profiling/LoadHitch/"),
        ModuleBases.Num());
}

void FFPSLoadHitchProbe::Shutdown()
{
    using namespace FPSLoadHitchProbePrivate;
    if (!bBound)
    {
        return;
    }
    // This module is the only binder of these two delegates (see Startup), so
// clearing them on shutdown is exact; RemoveAll(this) is unavailable because the
// handlers are free functions.
    FCoreDelegates::OnSyncLoadPackage.Clear();
    FCoreDelegates::OnBeginFrame.Clear();
    bBound = false;
    FlushEvidence();
    const TCHAR* EvidenceName = EvidencePath.IsEmpty() ? TEXT("(nothing)") : *EvidencePath;
    UE_LOG(LogTemp, Display,
        TEXT("LoadHitchProbe summary: %d sync-load entries seen, %d recorded to %s"),
        GEntryCount, GWrittenCount, EvidenceName);
}

void FFPSLoadHitchProbe::Tick()
{
    using namespace FPSLoadHitchProbePrivate;
    if (Pending.Package.IsEmpty())
    {
        return;
    }
    // The load that started before this tick has finished by now, so its total
    // duration is known. A load that is still blocking is reported by the next
    // tick, with the longer interval, and carries its own captured stack.
    const double ElapsedMs = (FPlatformTime::Seconds() - Pending.StartSeconds) * 1000.0;
    if (ElapsedMs >= GThresholdMs)
    {
        RecordLoad(Pending, ElapsedMs, Pending.Frames);
    }
    Pending = FPendingLoad();
}