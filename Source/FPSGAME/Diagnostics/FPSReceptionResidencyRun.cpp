// Explicit standalone reproduction for the requested dungeon GPU investigation.
// No startup hook: invoked only by fps.Perf.ReceptionRun <Saved case.json>.
#include "../UI/FPSPerformanceMetrics.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Dungeons/AuthoredDungeonGenerator.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformProcess.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

#if !UE_BUILD_SHIPPING
namespace FPSReceptionResidency
{
struct FRun
{
    TSharedPtr<FJsonObject> Config, State = MakeShared<FJsonObject>();
    FString Directory, Phase = TEXT("loading_dungeon");
    double Started = FPlatformTime::Seconds(), ReadyAt = 0, CaptureAt = 0, FirstStaff = 0, PhaseAt = 0;
    TArray<TSharedPtr<FJsonValue>> Observations;

    void Save()
    {
        State->SetStringField(TEXT("phase"), Phase);
        State->SetStringField(TEXT("updated_utc"), FDateTime::UtcNow().ToIso8601());
        State->SetArrayField(TEXT("observations"), Observations);
        FString Json;
        FJsonSerializer::Serialize(State.ToSharedRef(), TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json, *(Directory / TEXT("state.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    }
    void Command(UWorld* World, const FString& Text) { GEngine->Exec(World, *Text); }
    void Inventory(UWorld* World, const TCHAR* Label)
    {
        const FDateTime Before = FDateTime::UtcNow();
        Command(World, TEXT("rhi.DumpResourceMemory all Transient=no -csvfile"));
        TArray<FString> Files;
        IFileManager::Get().FindFiles(Files, *(FPaths::ProfilingDir() / TEXT("rhiDumpResourceMemory-*.csv")), true, false);
        TArray<TSharedPtr<FJsonValue>> Paths;
        for (const FString& File : Files)
        {
            const FString Source = FPaths::ProfilingDir() / File;
            if (IFileManager::Get().GetTimeStamp(*Source) < Before - FTimespan::FromSeconds(1)) continue;
            const FString Destination = Directory / (FString(Label) + TEXT("-") + File);
            if (IFileManager::Get().Copy(*Destination, *Source) == COPY_OK)
                Paths.Add(MakeShared<FJsonValueString>(Destination));
        }
        State->SetArrayField(FString(Label) + TEXT("_inventory"), Paths);
    }
    bool Tick(float)
    {
        const double Now = FPlatformTime::Seconds();
        UWorld* World = nullptr;
        for (const FWorldContext& Context : GEngine->GetWorldContexts())
            if (Context.WorldType == EWorldType::Game) { World = Context.World(); break; }
        if (!World) return Now - Started < 300;
        if (Now - Started > 300)
        {
            Command(World, TEXT("fps.Perf.GpuCapture stop"));
            Command(World, TEXT("fps.Perf.MonsterCapture end"));
            Phase = TEXT("failed"); State->SetStringField(TEXT("error"), TEXT("Reproduction timed out")); Save();
            FPlatformMisc::RequestExit(false); return false;
        }
        APlayerController* PC = World->GetFirstPlayerController();
        APawn* Pawn = PC ? PC->GetPawn() : nullptr;
        if (Phase == TEXT("loading_dungeon"))
        {
            auto* Loading = World->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
            AAuthoredDungeonGenerator* Generator = nullptr;
            for (TActorIterator<AAuthoredDungeonGenerator> It(World); It; ++It) { Generator = *It; break; }
            if (!Pawn || !Loading || Loading->IsHoldingGameplayInput() || !Generator ||
                Generator->GeneratedSeed != Config->GetIntegerField(TEXT("seed")) || Generator->LayoutManifestJson.Len() < 1000)
            { ReadyAt = 0; return true; }
            if (ReadyAt == 0) ReadyAt = Now;
            if (Now - ReadyAt < 5) return true;
            FFileHelper::SaveStringToFile(Generator->LayoutManifestJson, *(Directory / TEXT("layout.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
            auto CVars = MakeShared<FJsonObject>();
            for (const TCHAR* Name : {TEXT("fps.body.AsyncPreloadCandidates"), TEXT("r.RayTracing"), TEXT("r.Lumen.HardwareRayTracing"),
                TEXT("r.DynamicGlobalIlluminationMethod"), TEXT("r.ReflectionMethod"), TEXT("r.Shadow.Virtual.Enable"),
                TEXT("r.Streaming.PoolSize"), TEXT("r.ScreenPercentage"), TEXT("t.MaxFPS")})
                if (auto* Var = IConsoleManager::Get().FindConsoleVariable(Name)) CVars->SetNumberField(Name, Var->GetFloat());
            State->SetObjectField(TEXT("cvars"), CVars);
            Inventory(World, TEXT("pre"));
            Command(World, TEXT("fps.Perf.MonsterCapture begin"));
            Command(World, TEXT("fps.Perf.GpuCapture begin"));
            CaptureAt = FPlatformTime::Seconds(); Phase = TEXT("baseline"); Save(); return true;
        }
        if (Phase == TEXT("exporting"))
        {
            FString Json; TSharedPtr<FJsonObject> Receipt;
            if (FFileHelper::LoadFileToString(Json, *(Directory / TEXT("export.json"))) &&
                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Receipt))
            {
                State->SetObjectField(TEXT("export"), Receipt);
                Command(World, TEXT("fps.Perf.MonsterCapture end"));
                Inventory(World, TEXT("post"));
                Phase = TEXT("complete"); PhaseAt = Now; Save();
            }
            return true;
        }
        if (Phase == TEXT("complete"))
        {
            if (Now - PhaseAt < 2) return true;
            FPlatformMisc::RequestExit(false); return false;
        }
        if (!Pawn) return true;
        int32 Staff = 0;
        for (TActorIterator<ACharacter> It(World); It; ++It)
            if (It->GetName().StartsWith(TEXT("BP_Faceless")) && It->GetController()) ++Staff;
        auto Observation = MakeShared<FJsonObject>();
        Observation->SetNumberField(TEXT("elapsed"), Now - CaptureAt);
        Observation->SetNumberField(TEXT("staff"), Staff);
        Observation->SetStringField(TEXT("position"), Pawn->GetActorLocation().ToString());
        Observation->SetBoolField(TEXT("paused"), World->IsPaused());
        Observations.Add(MakeShared<FJsonValueObject>(Observation));
        if (Phase == TEXT("baseline") && Now - CaptureAt >= 5)
        {
            const auto& Position = Config->GetArrayField(TEXT("position"));
            Pawn->SetActorLocation(FVector(Position[0]->AsNumber(), Position[1]->AsNumber(), Position[2]->AsNumber()), false, nullptr, ETeleportType::TeleportPhysics);
            PC->SetControlRotation(FRotator(Config->GetNumberField(TEXT("pitch")), Config->GetNumberField(TEXT("yaw")), 0));
            Phase = TEXT("combat");
        }
        if (Phase == TEXT("combat") && Staff > 0 && FirstStaff == 0)
        { FirstStaff = Now; State->SetNumberField(TEXT("first_staff"), Now - CaptureAt); }
        if ((FirstStaff > 0 && Now - FirstStaff >= 35) || Now - CaptureAt >= 75)
        {
            Command(World, FString::Printf(TEXT("fps.Perf.GpuCapture export \"%s\""), *(Directory / TEXT("export.json"))));
            Phase = TEXT("exporting");
        }
        Save(); return true;
    }
};
TWeakPtr<FRun> ActiveRun;
FAutoConsoleCommand Begin(TEXT("fps.Perf.ReceptionRun"), TEXT("Explicit standalone GPU reproduction: <Saved case.json>. Exits this game process after export."),
    FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
    {
        if (GIsEditor || ActiveRun.IsValid() || Args.Num() != 1) return;
        FString Path = FPaths::ConvertRelativePathToFull(Args[0]);
        FPaths::NormalizeFilename(Path); FPaths::CollapseRelativeDirectories(Path);
        if (!FPaths::IsUnderDirectory(Path, FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()))) return;
        auto Run = MakeShared<FRun>(); FString Json;
        if (!FFileHelper::LoadFileToString(Json, *Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Run->Config)) return;
        Run->Directory = FPaths::GetPath(Path);
        Run->Config->SetNumberField(TEXT("pid"), FPlatformProcess::GetCurrentProcessId());
        Run->State->SetNumberField(TEXT("pid"), FPlatformProcess::GetCurrentProcessId());
        Run->State->SetObjectField(TEXT("config"), Run->Config);
        Run->State->SetStringField(TEXT("mode"), TEXT("standalone_game"));
        Run->Save(); ActiveRun = Run;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run](float Delta) { return Run->Tick(Delta); }), .5f);
    }));
}
#endif
