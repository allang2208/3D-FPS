#include "M10Mawcrawler.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

#if WITH_EDITOR
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavMesh/RecastNavMesh.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#endif

namespace
{
FString M10NavigationReceipt(const TSharedRef<FJsonObject>& Receipt)
{
    FString Result;
    FJsonSerializer::Serialize(Receipt, TJsonWriterFactory<>::Create(&Result));
    return Result;
}

#if WITH_EDITOR
TArray<TSharedPtr<FJsonValue>> M10VectorValues(const FVector& Value)
{
    return {MakeShared<FJsonValueNumber>(Value.X), MakeShared<FJsonValueNumber>(Value.Y),
        MakeShared<FJsonValueNumber>(Value.Z)};
}

void ConfigureM10RuntimeGeneration(ARecastNavMesh* Data)
{
    // These reflected authoring properties have protected C++ storage. Apply
    // them only to this agent's actor, preserving the other nav meshes.
    if (auto* Mode = FindFProperty<FEnumProperty>(ANavigationData::StaticClass(), TEXT("RuntimeGeneration")))
        Mode->GetUnderlyingProperty()->SetIntPropertyValue(Mode->ContainerPtrToValuePtr<void>(Data),
            static_cast<int64>(ERuntimeGenerationType::Dynamic));
    if (auto* Force = FindFProperty<FBoolProperty>(ANavigationData::StaticClass(), TEXT("bForceRebuildOnLoad")))
        // The producer explicitly rebuilds below. Persisting true clears those
        // saved tiles on every map load and leaves M10 waiting for a full build.
        Force->SetPropertyValue_InContainer(Data, false);
}

FString ProduceM10Navigation(UWorld* World)
{
    auto Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("navigation_built"), false);
    Receipt->SetBoolField(TEXT("runtime_tested"), false);
    Receipt->SetStringField(TEXT("map"), World->GetOutermost()->GetName());
    Receipt->SetStringField(TEXT("source_revision"), TEXT("M10DedicatedRigV1"));
    Receipt->SetStringField(TEXT("operation"), TEXT("Preserve M10 saved tiles on load; rebuild its tiles synchronously; save existing map"));

    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav)
    {
        FNavigationSystem::AddNavigationSystemToWorld(*World, FNavigationSystemRunMode::EditorMode);
        Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    }
    if (!Nav)
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map navigation system could not be created."));
        return M10NavigationReceipt(Receipt);
    }

    const auto& PersistentAgents = GetDefault<UNavigationSystemV1>()->GetSupportedAgents();
    int32 AgentIndex = INDEX_NONE;
    for (int32 Index = 0; Index < PersistentAgents.Num(); ++Index)
        if (PersistentAgents[Index].Name == TEXT("M10Mawcrawler")) AgentIndex = Index;
    if (AgentIndex == INDEX_NONE ||
        !FMath::IsNearlyEqual(PersistentAgents[AgentIndex].AgentRadius, 225.f) ||
        !FMath::IsNearlyEqual(PersistentAgents[AgentIndex].AgentHeight, 450.f))
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The persistent M10 navigation profile must remain radius 225 / height 450 cm."));
        return M10NavigationReceipt(Receipt);
    }
    const FNavDataConfig M10Config = PersistentAgents[AgentIndex];
    auto PreservedMask = Nav->GetSupportedAgentsMask();
    PreservedMask.Set(AgentIndex);
    Nav->OverrideSupportedAgents(PersistentAgents);
    Nav->SetSupportedAgentsMask(PreservedMask);

    TArray<TSharedPtr<FJsonValue>> Bounds;
    for (TActorIterator<ANavMeshBoundsVolume> It(World); It; ++It)
    {
        // Add only M10 to authored coverage: no brush movement, expansion or
        // replacement of other agents' selectors is part of this repair.
        It->SupportedAgents.Set(AgentIndex);
        It->MarkPackageDirty();
        Nav->OnNavigationBoundsUpdated(*It);
        auto Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("actor"), It->GetPathName());
        const FBox Box = It->GetComponentsBoundingBox(true);
        Item->SetArrayField(TEXT("minimum_cm"), M10VectorValues(Box.Min));
        Item->SetArrayField(TEXT("maximum_cm"), M10VectorValues(Box.Max));
        Bounds.Add(MakeShared<FJsonValueObject>(Item));
    }
    if (Bounds.IsEmpty())
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map has no authored navigation coverage; no map was saved."));
        return M10NavigationReceipt(Receipt);
    }

    // OnWorldInitDone processes existing bounds, actor registration and the
    // navigation geometry octree. Headless loading has no editor UI callback
    // to release its completed asynchronous-load lock.
    FlushAsyncLoading();
    Nav->OnWorldInitDone(FNavigationSystemRunMode::EditorMode);
    Nav->RemoveNavigationBuildLock(ENavigationBuildLock::AsyncLoadLock,
        UNavigationSystemV1::ELockRemovalRebuildAction::NoRebuild);
    // An explicit asset build is permitted even when the user's automatic
    // editor navigation updates are disabled (matching NavSystem::Build).
    if (Nav->IsNavigationBuildingLocked(static_cast<uint8>(~ENavigationBuildLock::NoUpdateInEditor)))
    {
        Receipt->SetStringField(TEXT("error"), TEXT("Navigation is still locked for loading; no map was saved."));
        return M10NavigationReceipt(Receipt);
    }

    ARecastNavMesh* M10Data = nullptr;
    for (TActorIterator<ARecastNavMesh> It(World); It; ++It)
    {
        if (It->GetConfig().Name == TEXT("M10Mawcrawler"))
        {
            if (M10Data)
            {
                Receipt->SetStringField(TEXT("error"), TEXT("The map has duplicate M10 navigation actors; no map was saved."));
                return M10NavigationReceipt(Receipt);
            }
            M10Data = *It;
        }
    }
    if (!M10Data)
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map initialization did not register the M10 navigation actor."));
        return M10NavigationReceipt(Receipt);
    }

    Receipt->SetNumberField(TEXT("previous_active_tiles"), M10Data->GetNumActiveTiles());
    Receipt->SetNumberField(TEXT("previous_radius_cm"), M10Data->GetConfig().AgentRadius);
    Receipt->SetNumberField(TEXT("previous_height_cm"), M10Data->GetConfig().AgentHeight);
    M10Data->SetConfig(M10Config);
    ConfigureM10RuntimeGeneration(M10Data);
    if (const auto* Force = FindFProperty<FBoolProperty>(ANavigationData::StaticClass(), TEXT("bForceRebuildOnLoad")))
        Receipt->SetBoolField(TEXT("force_rebuild_on_load"), Force->GetPropertyValue_InContainer(M10Data));
    Receipt->SetStringField(TEXT("runtime_generation"), TEXT("Dynamic"));
    M10Data->RebuildAll();
    M10Data->EnsureBuildCompletion();
    const int32 ActiveTiles = M10Data->GetNumActiveTiles();
    Receipt->SetNumberField(TEXT("active_tiles"), ActiveTiles);
    Receipt->SetStringField(TEXT("navigation_data"), M10Data->GetPathName());
    Receipt->SetNumberField(TEXT("profile_index"), AgentIndex);
    Receipt->SetNumberField(TEXT("radius_cm"), M10Config.AgentRadius);
    Receipt->SetNumberField(TEXT("height_cm"), M10Config.AgentHeight);
    Receipt->SetNumberField(TEXT("step_cm"), M10Config.AgentStepHeight);
    Receipt->SetArrayField(TEXT("authored_bounds"), Bounds);
    if (ActiveTiles <= 0)
    {
        // An actor alone was the previous receipt's completion condition.
        // Empty production output cannot be called a saved navigable asset.
        Receipt->SetStringField(TEXT("error"), TEXT("M10 tile generation produced no active data; the map was not saved."));
        return M10NavigationReceipt(Receipt);
    }

    M10Data->MarkPackageDirty();
    World->MarkPackageDirty();
    auto* Package = World->GetOutermost();
    FSavePackageArgs Save;
    Save.TopLevelFlags = RF_Public | RF_Standalone;
    Save.SaveFlags = SAVE_NoError;
    const FString Filename = FPackageName::LongPackageNameToFilename(
        Package->GetName(), FPackageName::GetMapPackageExtension());
    const bool bSaved = UPackage::SavePackage(Package, World, *Filename, Save);
    Receipt->SetBoolField(TEXT("navigation_built"), true);
    Receipt->SetBoolField(TEXT("saved"), bSaved);
    if (!bSaved) Receipt->SetStringField(TEXT("error"), TEXT("The navigation map package could not be saved."));
    return M10NavigationReceipt(Receipt);
}
#endif
}

FString AM10Mawcrawler::BuildMapNavigation(const FString& MapPackageName)
{
#if WITH_EDITOR
    if (!IsRunningCommandlet() || MapPackageName != TEXT("/Game/GameMaps/DayNight_Lighting"))
        return TEXT("{\"saved\":false,\"error\":\"This repair is limited to the M10 background map-production commandlet.\"}");
    auto* Package = LoadPackage(nullptr, *MapPackageName, LOAD_None);
    auto* World = Package ? UWorld::FindWorldInPackage(Package) : nullptr;
    if (!World || World->IsPartitionedWorld())
        return TEXT("{\"saved\":false,\"error\":\"The existing non-partitioned DayNight map could not be loaded.\"}");
    World->WorldType = EWorldType::Editor;
    const bool bHadRoot = World->IsRooted();
    if (!bHadRoot) World->AddToRoot();
    const bool bCreatedContext = GEngine->GetWorldContextFromWorld(World) == nullptr;
    if (bCreatedContext) GEngine->CreateNewWorldContext(EWorldType::Editor).SetCurrentWorld(World);
    if (!World->IsInitialized())
        World->InitWorld(UWorld::InitializationValues().AllowAudioPlayback(false)
            .RequiresHitProxies(false).CreateAISystem(false).ShouldSimulatePhysics(false).CreateFXSystem(false));
    World->UpdateWorldComponents(true, false);
    const FString Result = ProduceM10Navigation(World);
    World->CleanupWorld();
    if (bCreatedContext) GEngine->DestroyWorldContext(World);
    if (!bHadRoot) World->RemoveFromRoot();
    return Result;
#else
    return TEXT("{\"saved\":false,\"error\":\"The M10 navigation repair requires an Editor build.\"}");
#endif
}

FString AM10Mawcrawler::BuildNavigation(UWorld* World)
{
#if WITH_EDITOR
    if(!World || World->WorldType!=EWorldType::Editor || World->GetOutermost()->GetName()!=TEXT("/Game/GameMaps/DayNight_Lighting") || World->GetOutermost()->IsDirty()) return TEXT("{\"saved\":false,\"error\":\"Requires the clean DayNight editor map; existing unsaved content is preserved.\"}");
    return ProduceM10Navigation(World);
#else
    return TEXT("{\"saved\":false,\"error\":\"Editor build required\"}");
#endif
}
