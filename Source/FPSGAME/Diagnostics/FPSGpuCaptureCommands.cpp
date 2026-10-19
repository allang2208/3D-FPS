// Explicit automation entry for the same recorder used by F6. No startup hook.
#include "../UI/FPSPerformanceMetrics.h"
#include "../UI/FPSGpuTraceCapture.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

#if !UE_BUILD_SHIPPING
namespace
{
FAutoConsoleCommandWithWorldAndArgs GpuCaptureCommand(TEXT("fps.Perf.GpuCapture"),
    TEXT("Explicit F6 capture: begin | stop | status <Saved receipt> | export <Saved receipt>. Does not change gameplay or quality."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        auto* Metrics = World ? World->GetSubsystem<UFPSPerformanceMetricsSubsystem>() : nullptr;
        if (!Metrics || Args.IsEmpty()) return;
        if (Args[0] == TEXT("begin"))
        { if (!Metrics->IsGpuTraceRunning()) Metrics->ToggleGpuTraceCapture(); return; }
        if (Args[0] == TEXT("stop"))
        { if (Metrics->IsGpuTraceRunning()) Metrics->ToggleGpuTraceCapture(); return; }
        if (Args.Num() != 2 || (Args[0] != TEXT("status") && Args[0] != TEXT("export"))) return;
        FString Receipt = FPaths::ConvertRelativePathToFull(Args[1]);
        FPaths::NormalizeFilename(Receipt); FPaths::CollapseRelativeDirectories(Receipt);
        if (!FPaths::IsUnderDirectory(Receipt, FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()))) return;
        if (Args[0] == TEXT("status"))
        {
            auto Row = MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("status"), Metrics->GpuTraceStatusText());
            Row->SetBoolField(TEXT("running"), Metrics->IsGpuTraceRunning());
            Row->SetStringField(TEXT("world"), World->GetPathName());
            FString Json; FJsonSerializer::Serialize(Row, TJsonWriterFactory<>::Create(&Json));
            FFileHelper::SaveStringToFile(Json, *Receipt, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
            return;
        }
        auto Snapshot = Metrics->BuildSnapshot(10, World->GetFirstPlayerController());
        Metrics->AttachGpuTraceCapture(Snapshot);
        UFPSPerformanceMetricsSubsystem::ExportSnapshotAsync(Snapshot,
            [Receipt, Capture=Snapshot.GpuTraceCapture](bool bSaved, const FString& Path, double ElapsedMs)
            {
                auto Row = MakeShared<FJsonObject>();
                Row->SetBoolField(TEXT("saved"), bSaved);
                Row->SetStringField(TEXT("report_path"), Path);
                Row->SetNumberField(TEXT("export_ms"), ElapsedMs);
                Row->SetBoolField(TEXT("complete_gpu_bundle"), Capture && Capture->HasCompleteBundle());
                if (Capture) Row->SetStringField(TEXT("gpu_status"), Capture->StatusText());
                FString Json; FJsonSerializer::Serialize(Row, TJsonWriterFactory<>::Create(&Json));
                FFileHelper::SaveStringToFile(Json, *Receipt, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
            });
    }));
}
#endif
