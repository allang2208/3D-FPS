#include "BlindSupplicantNavigationRepairV08.h"
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
FString NavigationRepairReceipt(const TSharedRef<FJsonObject>& Receipt)
{
    FString Result;
    FJsonSerializer::Serialize(Receipt, TJsonWriterFactory<>::Create(&Result));
    return Result;
}

#if WITH_EDITOR
TArray<TSharedPtr<FJsonValue>> VectorValues(const FVector& Value)
{
    return {MakeShared<FJsonValueNumber>(Value.X), MakeShared<FJsonValueNumber>(Value.Y),
        MakeShared<FJsonValueNumber>(Value.Z)};
}

void ConfigureM07RuntimeGeneration(ARecastNavMesh* Data)
{
    // These reflected authoring properties have protected C++ storage. Apply
    // them only to this agent's actor, preserving the other four nav meshes.
    if (auto* Mode = FindFProperty<FEnumProperty>(ANavigationData::StaticClass(), TEXT("RuntimeGeneration")))
        Mode->GetUnderlyingProperty()->SetIntPropertyValue(Mode->ContainerPtrToValuePtr<void>(Data),
            static_cast<int64>(ERuntimeGenerationType::Dynamic));
    if (auto* Force = FindFProperty<FBoolProperty>(ANavigationData::StaticClass(), TEXT("bForceRebuildOnLoad")))
        // The producer explicitly rebuilds below. Persisting true clears those
        // saved tiles on every map load and leaves M07 waiting for a full build.
        Force->SetPropertyValue_InContainer(Data, false);
}

FString ProduceNavigation(UWorld* World)
{
    auto Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("navigation_built"), false);
    Receipt->SetBoolField(TEXT("runtime_tested"), false);
    Receipt->SetStringField(TEXT("map"), World->GetOutermost()->GetName());
    Receipt->SetStringField(TEXT("source_revision"), TEXT("BodyMotionV18NavigationLoadRepair"));
    Receipt->SetStringField(TEXT("operation"), TEXT("Preserve M07 saved tiles on load; rebuild its tiles synchronously; save existing map"));

    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav)
    {
        FNavigationSystem::AddNavigationSystemToWorld(*World, FNavigationSystemRunMode::EditorMode);
        Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    }
    if (!Nav)
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map navigation system could not be created."));
        return NavigationRepairReceipt(Receipt);
    }

    const auto& PersistentAgents = GetDefault<UNavigationSystemV1>()->GetSupportedAgents();
    int32 AgentIndex = INDEX_NONE;
    for (int32 Index = 0; Index < PersistentAgents.Num(); ++Index)
        if (PersistentAgents[Index].Name == TEXT("BlindSupplicantM07")) AgentIndex = Index;
    if (AgentIndex == INDEX_NONE ||
        !FMath::IsNearlyEqual(PersistentAgents[AgentIndex].AgentRadius, 50.f) ||
        !FMath::IsNearlyEqual(PersistentAgents[AgentIndex].AgentHeight, 312.f))
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The persistent M07 navigation profile must remain radius 50 / height 312 cm."));
        return NavigationRepairReceipt(Receipt);
    }
    const FNavDataConfig M07Config = PersistentAgents[AgentIndex];
    auto PreservedMask = Nav->GetSupportedAgentsMask();
    PreservedMask.Set(AgentIndex);
    Nav->OverrideSupportedAgents(PersistentAgents);
    Nav->SetSupportedAgentsMask(PreservedMask);

    TArray<TSharedPtr<FJsonValue>> Bounds;
    for (TActorIterator<ANavMeshBoundsVolume> It(World); It; ++It)
    {
        // Add only M07 to authored coverage: no brush movement, expansion or
        // replacement of other agents' selectors is part of this repair.
        It->SupportedAgents.Set(AgentIndex);
        It->MarkPackageDirty();
        Nav->OnNavigationBoundsUpdated(*It);
        auto Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("actor"), It->GetPathName());
        const FBox Box = It->GetComponentsBoundingBox(true);
        Item->SetArrayField(TEXT("minimum_cm"), VectorValues(Box.Min));
        Item->SetArrayField(TEXT("maximum_cm"), VectorValues(Box.Max));
        Bounds.Add(MakeShared<FJsonValueObject>(Item));
    }
    if (Bounds.IsEmpty())
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map has no authored navigation coverage; no map was saved."));
        return NavigationRepairReceipt(Receipt);
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
        return NavigationRepairReceipt(Receipt);
    }

    ARecastNavMesh* M07Data = nullptr;
    for (TActorIterator<ARecastNavMesh> It(World); It; ++It)
    {
        if (It->GetConfig().Name == TEXT("BlindSupplicantM07"))
        {
            if (M07Data)
            {
                Receipt->SetStringField(TEXT("error"), TEXT("The map has duplicate M07 navigation actors; no map was saved."));
                return NavigationRepairReceipt(Receipt);
            }
            M07Data = *It;
        }
    }
    if (!M07Data)
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map initialization did not register the M07 navigation actor."));
        return NavigationRepairReceipt(Receipt);
    }

    Receipt->SetNumberField(TEXT("previous_active_tiles"), M07Data->GetNumActiveTiles());
    Receipt->SetNumberField(TEXT("previous_radius_cm"), M07Data->GetConfig().AgentRadius);
    Receipt->SetNumberField(TEXT("previous_height_cm"), M07Data->GetConfig().AgentHeight);
    M07Data->SetConfig(M07Config);
    ConfigureM07RuntimeGeneration(M07Data);
    if (const auto* Force = FindFProperty<FBoolProperty>(ANavigationData::StaticClass(), TEXT("bForceRebuildOnLoad")))
        Receipt->SetBoolField(TEXT("force_rebuild_on_load"), Force->GetPropertyValue_InContainer(M07Data));
    Receipt->SetStringField(TEXT("runtime_generation"), TEXT("Dynamic"));
    M07Data->RebuildAll();
    M07Data->EnsureBuildCompletion();
    const int32 ActiveTiles = M07Data->GetNumActiveTiles();
    Receipt->SetNumberField(TEXT("active_tiles"), ActiveTiles);
    Receipt->SetStringField(TEXT("navigation_data"), M07Data->GetPathName());
    Receipt->SetNumberField(TEXT("profile_index"), AgentIndex);
    Receipt->SetNumberField(TEXT("radius_cm"), M07Config.AgentRadius);
    Receipt->SetNumberField(TEXT("height_cm"), M07Config.AgentHeight);
    Receipt->SetNumberField(TEXT("step_cm"), M07Config.AgentStepHeight);
    Receipt->SetArrayField(TEXT("authored_bounds"), Bounds);
    if (ActiveTiles <= 0)
    {
        // An actor alone was the previous receipt's completion condition.
        // Empty production output cannot be called a saved navigable asset.
        Receipt->SetStringField(TEXT("error"), TEXT("M07 tile generation produced no active data; the map was not saved."));
        return NavigationRepairReceipt(Receipt);
    }

    M07Data->MarkPackageDirty();
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
    return NavigationRepairReceipt(Receipt);
}
#endif
}

FString UBlindSupplicantNavigationRepairV08::BuildAndSaveMapNavigation(const FString& MapPackageName)
{
#if WITH_EDITOR
    if (!IsRunningCommandlet() || MapPackageName != TEXT("/Game/GameMaps/DayNight_Lighting"))
        return TEXT("{\"saved\":false,\"error\":\"This repair is limited to the M07 background map-production commandlet.\"}");
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
    const FString Result = ProduceNavigation(World);
    World->CleanupWorld();
    if (bCreatedContext) GEngine->DestroyWorldContext(World);
    if (!bHadRoot) World->RemoveFromRoot();
    return Result;
#else
    return TEXT("{\"saved\":false,\"error\":\"The M07 navigation repair requires an Editor build.\"}");
#endif
}
