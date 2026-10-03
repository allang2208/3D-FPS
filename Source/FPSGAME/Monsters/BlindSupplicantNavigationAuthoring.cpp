#include "BlindSupplicantNavigationAuthoring.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

#if WITH_EDITOR
#include "Engine/Engine.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#endif

namespace
{
FString M07NavigationReceipt(const TSharedRef<FJsonObject>& Data)
{
    FString Output;
    FJsonSerializer::Serialize(Data, TJsonWriterFactory<>::Create(&Output));
    return Output;
}
}

FString UBlindSupplicantNavigationAuthoring::BuildAndSaveNavigation(UWorld* World)
{
    auto Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("runtime_tested"), false);
#if WITH_EDITOR
    if (!World || World->WorldType != EWorldType::Editor ||
        World->GetOutermost()->GetName() != TEXT("/Game/GameMaps/DayNight_Lighting"))
    {
        Receipt->SetStringField(TEXT("error"), TEXT("M07 navigation authoring requires the existing DayNight_Lighting editor map."));
        return M07NavigationReceipt(Receipt);
    }
    if (!IsRunningCommandlet() && World->GetOutermost()->IsDirty())
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The loaded map contains existing unsaved edits; navigation authoring leaves it untouched."));
        return M07NavigationReceipt(Receipt);
    }
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav)
    {
        FNavigationSystem::AddNavigationSystemToWorld(*World, FNavigationSystemRunMode::EditorMode);
        Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    }
    if (!Nav)
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map navigation system could not be created."));
        return M07NavigationReceipt(Receipt);
    }
    // The map was saved before this appended profile existed. Keep the stable
    // config indices and apply them to the loaded map's navigation system.
    Nav->OverrideSupportedAgents(GetDefault<UNavigationSystemV1>()->GetSupportedAgents());
    const auto& Agents = Nav->GetSupportedAgents();
    int32 M07Index = INDEX_NONE;
    for (int32 Index = 0; Index < Agents.Num(); ++Index)
        if (Agents[Index].Name == TEXT("BlindSupplicantM07")) M07Index = Index;
    if (M07Index == INDEX_NONE)
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The persistent M07 SupportedAgents profile is missing."));
        return M07NavigationReceipt(Receipt);
    }
    int32 BoundsCount = 0;
    for (TActorIterator<ANavMeshBoundsVolume> It(World); It; ++It)
    {
        // Append this profile to existing authored brushes without changing
        // their geometry, other agent bits, or map placement.
        It->SupportedAgents.Set(M07Index);
        It->MarkPackageDirty();
        Nav->OnNavigationBoundsUpdated(*It);
        ++BoundsCount;
    }
    if (!BoundsCount)
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map has no authored navigation bounds; no map was saved."));
        return M07NavigationReceipt(Receipt);
    }
    auto Mask = Nav->GetSupportedAgentsMask();
    Mask.Set(M07Index);
    Nav->SetSupportedAgentsMask(Mask);
    Nav->OnWorldInitDone(FNavigationSystemRunMode::EditorMode);
    if (IsRunningCommandlet())
    {
        FlushAsyncLoading();
        // Editor map loading normally releases this lock in its UI callback.
        // This headless loader has already finished its load/components phase.
        Nav->RemoveNavigationBuildLock(ENavigationBuildLock::AsyncLoadLock,
            UNavigationSystemV1::ELockRemovalRebuildAction::NoRebuild);
    }
    if (Nav->IsNavigationBuildingLocked())
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The authoring map is still locked for navigation loading; it was not saved."));
        return M07NavigationReceipt(Receipt);
    }
    // This creates and saves asset navigation tiles. No path query, gameplay
    // spawn, actor tick, BeginPlay, PIE or acceptance probe is performed.
    Nav->Build();
    TArray<TSharedPtr<FJsonValue>> Created;
    for (TActorIterator<ANavigationData> It(World); It; ++It)
    {
        const auto& Config = It->GetConfig();
        if (Config.Name == TEXT("BlindSupplicantM07"))
            Created.Add(MakeShared<FJsonValueString>(It->GetPathName()));
    }
    if (Created.IsEmpty())
    {
        Receipt->SetStringField(TEXT("error"), TEXT("Navigation production did not create M07 data; the map was not saved."));
        return M07NavigationReceipt(Receipt);
    }
    World->MarkPackageDirty();
    auto* Package = World->GetOutermost();
    FSavePackageArgs Args;
    Args.TopLevelFlags = RF_Public | RF_Standalone;
    Args.SaveFlags = SAVE_NoError;
    const FString Filename = FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetMapPackageExtension());
    const bool bSaved = UPackage::SavePackage(Package, World, *Filename, Args);
    Receipt->SetBoolField(TEXT("saved"), bSaved);
    Receipt->SetBoolField(TEXT("navigation_built"), true);
    Receipt->SetStringField(TEXT("map"), Package->GetName());
    Receipt->SetNumberField(TEXT("profile_index"), M07Index);
    Receipt->SetNumberField(TEXT("radius_cm"), Agents[M07Index].AgentRadius);
    Receipt->SetNumberField(TEXT("height_cm"), Agents[M07Index].AgentHeight);
    Receipt->SetNumberField(TEXT("bounds_count"), BoundsCount);
    Receipt->SetArrayField(TEXT("navigation_data"), Created);
    if (!bSaved) Receipt->SetStringField(TEXT("error"), TEXT("M07 navigation map package save failed."));
#else
    Receipt->SetStringField(TEXT("error"), TEXT("Navigation production is available in an Editor build."));
#endif
    return M07NavigationReceipt(Receipt);
}

FString UBlindSupplicantNavigationAuthoring::BuildAndSaveMapNavigation(const FString& MapPackageName)
{
#if WITH_EDITOR
    if (!IsRunningCommandlet() || MapPackageName != TEXT("/Game/GameMaps/DayNight_Lighting"))
        return TEXT("{\"saved\":false,\"error\":\"The map-loader entry point is limited to the M07 background commandlet.\"}");
    auto* Package = LoadPackage(nullptr, *MapPackageName, LOAD_None);
    auto* World = Package ? UWorld::FindWorldInPackage(Package) : nullptr;
    if (!World || World->IsPartitionedWorld())
        return TEXT("{\"saved\":false,\"error\":\"The existing non-partitioned authoring map could not be loaded.\"}");
    World->WorldType = EWorldType::Editor;
    const bool bHadRoot = World->IsRooted();
    if (!bHadRoot) World->AddToRoot();
    const bool bCreatedContext = GEngine->GetWorldContextFromWorld(World) == nullptr;
    if (bCreatedContext) GEngine->CreateNewWorldContext(EWorldType::Editor).SetCurrentWorld(World);
    if (!World->IsInitialized())
        World->InitWorld(UWorld::InitializationValues().AllowAudioPlayback(false)
            .RequiresHitProxies(false).CreateAISystem(false).ShouldSimulatePhysics(false).CreateFXSystem(false));
    World->UpdateWorldComponents(true, false);
    const FString Receipt = BuildAndSaveNavigation(World);
    World->CleanupWorld();
    if (bCreatedContext) GEngine->DestroyWorldContext(World);
    if (!bHadRoot) World->RemoveFromRoot();
    return Receipt;
#else
    return TEXT("{\"saved\":false,\"error\":\"Editor authoring build required.\"}");
#endif
}
