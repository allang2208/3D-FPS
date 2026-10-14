#include "MonsterAPSMigration.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonReader.h"

#if WITH_EDITOR
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "EngineUtils.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavMesh/RecastNavMesh.h"
#include "Navigation/APS_NavigationData.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#endif

namespace
{
FString APSMigrationReceipt(const TSharedRef<FJsonObject>& Receipt)
{
    FString Result;
    FJsonSerializer::Serialize(Receipt, TJsonWriterFactory<>::Create(&Result));
    return Result;
}

#if WITH_EDITOR
TArray<TSharedPtr<FJsonValue>> APSVectorValues(const FVector& Value)
{
    return {MakeShared<FJsonValueNumber>(Value.X), MakeShared<FJsonValueNumber>(Value.Y),
        MakeShared<FJsonValueNumber>(Value.Z)};
}

void ConfigureAPSRuntimeGeneration(ARecastNavMesh* Data)
{
    // These reflected authoring properties have protected C++ storage. Apply
    // them only to this agent's actor, preserving the other nav meshes.
    if (auto* Mode = FindFProperty<FEnumProperty>(ANavigationData::StaticClass(), TEXT("RuntimeGeneration")))
        Mode->GetUnderlyingProperty()->SetIntPropertyValue(Mode->ContainerPtrToValuePtr<void>(Data),
            static_cast<int64>(ERuntimeGenerationType::Dynamic));
    if (auto* Force = FindFProperty<FBoolProperty>(ANavigationData::StaticClass(), TEXT("bForceRebuildOnLoad")))
        // The producer explicitly rebuilds below. Persisting true clears those
        // saved tiles on every map load and leaves the agent waiting for a full build.
        Force->SetPropertyValue_InContainer(Data, false);
}

FString ProduceAPSNavigation(UWorld* World, const TArray<int32>& AgentIndices,
    const TArray<FNavDataConfig>& PersistentAgents)
{
    const bool bRuntimeTemplate = World->GetOutermost()->GetName() == TEXT("/Game/GameMaps/L_Dungeon_Randomized");
    auto Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("navigation_built"), false);
    Receipt->SetBoolField(TEXT("runtime_tested"), false);
    Receipt->SetStringField(TEXT("map"), World->GetOutermost()->GetName());
    Receipt->SetStringField(TEXT("source_revision"), TEXT("APSNavigationMigration20261007"));
    Receipt->SetStringField(TEXT("operation"), TEXT("Re-register APS-configured agents on AdaptivePathfindingSystem nav data; preserve other agents and authored bounds"));

    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav)
    {
        FNavigationSystem::AddNavigationSystemToWorld(*World, FNavigationSystemRunMode::EditorMode);
        Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    }
    if (!Nav)
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map navigation system could not be created."));
        return APSMigrationReceipt(Receipt);
    }

    auto PreservedMask = Nav->GetSupportedAgentsMask();
    for (int32 Index : AgentIndices) PreservedMask.Set(Index);
    Nav->OverrideSupportedAgents(PersistentAgents);
    Nav->SetSupportedAgentsMask(PreservedMask);

    TArray<TSharedPtr<FJsonValue>> Bounds;
    for (TActorIterator<ANavMeshBoundsVolume> It(World); It; ++It)
    {
        // Add only the migrated profiles: no brush movement, expansion or
        // replacement of other agents' selectors is part of this migration.
        for (int32 Index : AgentIndices) It->SupportedAgents.Set(Index);
        It->MarkPackageDirty();
        Nav->OnNavigationBoundsUpdated(*It);
        auto Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("actor"), It->GetPathName());
        const FBox Box = It->GetComponentsBoundingBox(true);
        Item->SetArrayField(TEXT("minimum_cm"), APSVectorValues(Box.Min));
        Item->SetArrayField(TEXT("maximum_cm"), APSVectorValues(Box.Max));
        Bounds.Add(MakeShared<FJsonValueObject>(Item));
    }
    if (Bounds.IsEmpty())
    {
        Receipt->SetStringField(TEXT("error"), TEXT("The map has no authored navigation coverage; no map was saved."));
        return APSMigrationReceipt(Receipt);
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
        return APSMigrationReceipt(Receipt);
    }

    TArray<TSharedPtr<FJsonValue>> Profiles;
    for (int32 AgentIndex : AgentIndices)
    {
        const auto& Config = PersistentAgents[AgentIndex];
        // Resolve the registered agent that path following actually uses. A
        // rejected legacy actor may still be enumerable during world startup.
        auto* Data = Cast<AAPS_NavigationData>(Nav->GetNavDataForAgentName(Config.Name));
        if (!IsValid(Data) || !Data->GetConfig().IsEquivalent(Config))
        {
            Receipt->SetStringField(TEXT("error"), FString::Printf(TEXT("Map initialization did not register %s on APS nav data"), *Config.Name.ToString()));
            return APSMigrationReceipt(Receipt);
        }
        auto Profile = MakeShared<FJsonObject>();
        Profile->SetStringField(TEXT("name"), Config.Name.ToString());
        Profile->SetNumberField(TEXT("previous_active_tiles"), Data->GetNumActiveTiles());
        Data->SetConfig(Config); // Applies step height to every Recast resolution.
        ConfigureAPSRuntimeGeneration(Data);
        Data->RebuildAll();
        Data->EnsureBuildCompletion();
        const int32 ActiveTiles = Data->GetNumActiveTiles();
        Profile->SetNumberField(TEXT("active_tiles"), ActiveTiles);
        Profile->SetStringField(TEXT("navigation_data"), Data->GetPathName());
        Profile->SetStringField(TEXT("navigation_class"), Data->GetClass()->GetPathName());
        Profile->SetNumberField(TEXT("profile_index"), AgentIndex);
        Profile->SetNumberField(TEXT("radius_cm"), Config.AgentRadius);
        Profile->SetNumberField(TEXT("height_cm"), Config.AgentHeight);
        Profile->SetNumberField(TEXT("step_cm"), Config.AgentStepHeight);
        Profiles.Add(MakeShared<FJsonValueObject>(Profile));
        Receipt->SetArrayField(TEXT("profiles"), Profiles);
        // The randomized dungeon is an empty production template. Its existing
        // generator moves the saved bounds and builds tiles after room assembly.
        if (ActiveTiles <= 0 && !bRuntimeTemplate)
        {
            Receipt->SetStringField(TEXT("error"), TEXT("Navigation migration yielded no active tiles; no map was saved."));
            return APSMigrationReceipt(Receipt);
        }
        Data->MarkPackageDirty();
    }
    Receipt->SetBoolField(TEXT("force_rebuild_on_load"), false);
    Receipt->SetStringField(TEXT("runtime_generation"), TEXT("Dynamic"));
    Receipt->SetArrayField(TEXT("authored_bounds"), Bounds);
    World->MarkPackageDirty();
    auto* Package = World->GetOutermost();
    FSavePackageArgs Save;
    Save.TopLevelFlags = RF_Public | RF_Standalone;
    Save.SaveFlags = SAVE_NoError;
    const FString Filename = FPackageName::LongPackageNameToFilename(
        Package->GetName(), FPackageName::GetMapPackageExtension());
    const bool bSaved = UPackage::SavePackage(Package, World, *Filename, Save);
    Receipt->SetBoolField(TEXT("navigation_built"), !bRuntimeTemplate);
    Receipt->SetBoolField(TEXT("runtime_template_saved"), bRuntimeTemplate && bSaved);
    Receipt->SetBoolField(TEXT("saved"), bSaved);
    if (!bSaved) Receipt->SetStringField(TEXT("error"), TEXT("The navigation map package could not be saved."));
    return APSMigrationReceipt(Receipt);
}
#endif
}

FString UMonsterAPSMigration::MigrateNavigationToAPS(const FString& MapPackageName)
{
#if WITH_EDITOR
    if (!IsRunningCommandlet() || (MapPackageName != TEXT("/Game/GameMaps/DayNight_Lighting") &&
        MapPackageName != TEXT("/Game/GameMaps/L_Dungeon_Randomized")))
        return TEXT("{\"saved\":false,\"error\":\"This migration only supports the existing DayNight map and randomized-dungeon template.\"}");
    auto* Package = LoadPackage(nullptr, *MapPackageName, LOAD_None);
    auto* World = Package ? UWorld::FindWorldInPackage(Package) : nullptr;
    if (!World || World->IsPartitionedWorld())
        return TEXT("{\"saved\":false,\"error\":\"The existing non-partitioned map could not be loaded.\"}");
    World->WorldType = EWorldType::Editor;
    const bool bHadRoot = World->IsRooted();
    if (!bHadRoot) World->AddToRoot();
    const bool bCreatedContext = GEngine->GetWorldContextFromWorld(World) == nullptr;
    if (bCreatedContext) GEngine->CreateNewWorldContext(EWorldType::Editor).SetCurrentWorld(World);
    // Replace the saved actor class before InitWorld registers it. Otherwise
    // registration rejects the stale class and auto-creates a replacement,
    // leaving a dead actor beside the APS one during this authoring operation.
    const auto& Agents = GetDefault<UNavigationSystemV1>()->GetSupportedAgents();
    TArray<int32> AgentIndices;
    for (int32 Index = 0; Index < Agents.Num(); ++Index)
    {
        UClass* Required = Agents[Index].GetNavDataClass<ANavigationData>().Get();
        if (Required && Required->IsChildOf(AAPS_NavigationData::StaticClass())) AgentIndices.Add(Index);
    }
    TArray<TSharedPtr<FJsonValue>> Replaced;
    if (AgentIndices.IsEmpty())
        return TEXT("{\"saved\":false,\"error\":\"No supported agent is configured for APS_NavigationData.\"}");
    for (AActor* Actor : TArray<AActor*>(World->PersistentLevel->Actors))
    {
        auto* Data = Cast<ANavigationData>(Actor);
        if (!IsValid(Data) || Data->IsActorBeingDestroyed()) continue;
        const FName Name = Data->GetConfig().Name;
        const auto* Config = Agents.FindByPredicate([Name](const auto& Agent) { return Agent.Name == Name; });
        if (!Config) continue;
        UClass* Required = Config->GetNavDataClass<ANavigationData>().Get();
        if (!Required || !Required->IsChildOf(AAPS_NavigationData::StaticClass())) continue;
        if (Data->GetClass() == Required)
        {
            // Already migrated; still refresh the live config below.
            continue;
        }
        FActorSpawnParameters Spawn;
        Spawn.bNoFail = true;
        auto* Fresh = World->SpawnActor<ANavigationData>(Required, Data->GetActorLocation(), Data->GetActorRotation(), Spawn);
        if (!IsValid(Fresh))
            return TEXT("{\"saved\":false,\"error\":\"The APS nav actor could not be spawned in the map.\"}");
        Fresh->SetConfig(*Config);
        if (auto* RecastFresh = Cast<ARecastNavMesh>(Fresh)) ConfigureAPSRuntimeGeneration(RecastFresh);
        auto Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("agent"), Name.ToString());
        Item->SetStringField(TEXT("removed"), Data->GetPathName());
        Item->SetStringField(TEXT("added"), Fresh->GetPathName());
        Replaced.Add(MakeShared<FJsonValueObject>(Item));
        Data->Destroy();
        World->MarkPackageDirty();
    }
    for (AActor* Actor : World->PersistentLevel->Actors)
    {
        auto* Data = Cast<ANavigationData>(Actor);
        if (!IsValid(Data) || Data->IsActorBeingDestroyed()) continue;
        const FName Name = Data->GetConfig().Name;
        if (const auto* Config = Agents.FindByPredicate([Name](const auto& Agent) { return Agent.Name == Name; }))
            Data->SetConfig(*Config);
    }
    if (!World->IsInitialized())
        World->InitWorld(UWorld::InitializationValues().AllowAudioPlayback(false)
            .RequiresHitProxies(false).CreateAISystem(false).ShouldSimulatePhysics(false).CreateFXSystem(false));
    World->UpdateWorldComponents(true, false);
    FString Result = ProduceAPSNavigation(World, AgentIndices, Agents);
    // Fold the replaced-actor audit into the produce receipt.
    {
        auto FinalReceipt = MakeShared<FJsonObject>();
        if (TSharedPtr<FJsonObject> Parsed; FJsonSerializer::Deserialize(
                TJsonReaderFactory<>::Create(Result), Parsed) && Parsed.IsValid())
            FinalReceipt = Parsed.ToSharedRef();
        FinalReceipt->SetArrayField(TEXT("replaced_actors"), Replaced);
        Result = APSMigrationReceipt(FinalReceipt);
    }
    World->CleanupWorld();
    if (bCreatedContext) GEngine->DestroyWorldContext(World);
    if (!bHadRoot) World->RemoveFromRoot();
    return Result;
#else
    return TEXT("{\"saved\":false,\"error\":\"The APS navigation migration requires an Editor build.\"}");
#endif
}
