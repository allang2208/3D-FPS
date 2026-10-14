#include "FPSPerformanceMetrics.h"
#include "CoreGlobals.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
TAutoConsoleVariable<int32> MonsterCaptureVersion(TEXT("fps.Perf.MonsterCaptureVersion"), 1,
    TEXT("Version of the opt-in AI and render attribution capture."), ECVF_ReadOnly);
TWeakObjectPtr<UFPSPerformanceMetricsSubsystem> CaptureMetrics;
bool bCaptureActive = false, bPreviousRecording = false;
int32 PreviousSampling = 1, PreviousInventory = 0;

void EndCaptureResources()
{
    if (!bCaptureActive) return;
    if (auto* Metrics = CaptureMetrics.Get()) Metrics->SetRecording(bPreviousRecording);
    if (auto* CVar = IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Perf.RenderResourceSampling")))
        CVar->Set(PreviousSampling, ECVF_SetByConsole);
    if (auto* CVar = IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Perf.GpuResourceInventory")))
        CVar->Set(PreviousInventory, ECVF_SetByConsole);
    // Match the engine's stat namedevents reference-counted enable/disable.
    GCycleStatsShouldEmitNamedEvents = FMath::Max(0, GCycleStatsShouldEmitNamedEvents - 1);
    CaptureMetrics.Reset();
    bCaptureActive = false;
}

FAutoConsoleCommandWithWorldAndArgs MonsterCapture(TEXT("fps.Perf.MonsterCapture"),
    TEXT("Diagnostic only: begin | end | export <receipt.json under Saved>. No gameplay or quality changes."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        if (Args.IsEmpty()) return;
        if (Args[0] == TEXT("end")) { EndCaptureResources(); return; }
        auto* Metrics = World ? World->GetSubsystem<UFPSPerformanceMetricsSubsystem>() : nullptr;
        if (!Metrics) return;
        if (Args[0] == TEXT("begin"))
        {
            if (bCaptureActive) return;
            CaptureMetrics = Metrics;
            bPreviousRecording = Metrics->IsRecording();
            Metrics->SetRecording(true);
            if (auto* CVar = IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Perf.RenderResourceSampling")))
            { PreviousSampling = CVar->GetInt(); CVar->Set(1, ECVF_SetByConsole); }
            // Full RHI allocation enumeration can itself stall allocation.
            // Keep the passive budget/morph observer, omit that costly inventory.
            if (auto* CVar = IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Perf.GpuResourceInventory")))
            { PreviousInventory = CVar->GetInt(); CVar->Set(0, ECVF_SetByConsole); }
            ++GCycleStatsShouldEmitNamedEvents;
            bCaptureActive = true;
            UE_LOG(LogTemp, Display, TEXT("MONSTER_CAPTURE_RESOURCES_BEGIN"));
        }
        else if (Args[0] == TEXT("export") && Args.Num() == 2)
        {
            FString Receipt = FPaths::ConvertRelativePathToFull(Args[1]);
            FPaths::NormalizeFilename(Receipt);
            FPaths::CollapseRelativeDirectories(Receipt);
            const FString Saved = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
            if (!FPaths::IsUnderDirectory(Receipt, Saved)) return;
            // Called only after stopping the trace: the scene scan and JSON
            // serialization must not become part of the measured combat window.
            const auto Snapshot = Metrics->BuildSnapshot(10, World->GetFirstPlayerController());
            UFPSPerformanceMetricsSubsystem::ExportSnapshotAsync(Snapshot,
                [Receipt](bool bSaved, const FString& Path, double ElapsedMs)
                {
                    auto Root = MakeShared<FJsonObject>();
                    Root->SetBoolField(TEXT("saved"), bSaved);
                    Root->SetStringField(TEXT("report_path"), Path);
                    Root->SetNumberField(TEXT("export_ms"), ElapsedMs);
                    Root->SetStringField(TEXT("completed_utc"), FDateTime::UtcNow().ToIso8601());
                    FString Json;
                    FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Json));
                    FFileHelper::SaveStringToFile(Json, *Receipt, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
                    UE_LOG(LogTemp, Display, TEXT("MONSTER_CAPTURE_REPORT saved=%d path=%s"), bSaved, *Path);
                });
        }
    }));
}
