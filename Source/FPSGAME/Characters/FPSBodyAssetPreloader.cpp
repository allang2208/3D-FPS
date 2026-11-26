// Player-body async preloader implementation. See FPSBodyAssetPreloader.h.

#include "FPSBodyAssetPreloader.h"
#include "../Diagnostics/FPSResourceLifecycle.h"
#include "FPSBodyOutfitResources.h"

#include "FPSPreloadAssetRegistry.gen.h"
#include "FPSPlayerBodyTypes.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"

#include "Animation/AnimSequence.h"
#include "AssetRegistry/ARFilter.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/AssetManager.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"
#include "UObject/SoftObjectPtr.h"
#include "UObject/UnrealType.h"

namespace FPSBodyPreloadPrivate
{
    /** Only content under these roots is warmed; plugin and engine content is left alone. */
    bool IsWantedPath(const FString& Path);
    void AddPath(TSet<FSoftObjectPath>& Out, const FString& Path);

    int32 GAsyncPreload = 1;
    int32 GMaxAssets = 400;
    int32 GExpandFolders = 0;
    int32 GPreloadCandidates = 0;

    FAutoConsoleVariableRef CVarPreloadCandidates(
        TEXT("fps.body.AsyncPreloadCandidates"),
        GPreloadCandidates,
        TEXT("0 = preload body, class defaults and inventory only (default). 1 also retains\n")
        TEXT("the generated equipment literal registry until GameInstance shutdown. This\n")
        TEXT("includes unselected fallback meshes; enable only for an explicit comparison."),
        ECVF_Default);

    FAutoConsoleVariableRef CVarAsyncPreload(
        TEXT("fps.body.AsyncPreload"),
        GAsyncPreload,
        TEXT("1 = request the player body and equipment assets asynchronously before the\n")
        TEXT("character begins play, so the later synchronous loads become cache hits (default)."),
        ECVF_Default);

    FAutoConsoleVariableRef CVarExpandFolders(
        TEXT("fps.body.AsyncPreloadExpandFolders"),
        GExpandFolders,
        TEXT("0 = warm only the explicitly named asset paths (default). 1 additionally sweeps\n")
        TEXT("the folders those paths live in through the asset registry, which reaches the\n")
        TEXT("Printf-built clip names but also pulls in dead design revisions: Content/Weapons\n")
        TEXT("holds 3383 packages while only ~131 are referenced, so 1 costs ~19 s of async\n")
        TEXT("loading and starves the game thread. Measure before enabling."),
        ECVF_Default);

    /** Content roots whose whole subtree is warmed, for assets the constants do not
     *  name individually. Kept to the folders the equipment code actually reads. */
    const TCHAR* const ExpandRoots[] = {
        TEXT("/Game/Weapons/AKM/"),
        TEXT("/Game/Weapons/Saiga12K/"),
        TEXT("/Game/Weapons/A762/"),
        TEXT("/Game/Weapons/PKMLowpoly20260922/"),
        TEXT("/Game/Weapons/M249/"),
        TEXT("/Game/Weapons/QBZ191/"),
        TEXT("/Game/Weapons/ASH12/"),
        TEXT("/Game/Weapons/M1911/"),
        TEXT("/Game/Weapons/DanWesson715/"),
        TEXT("/Game/Weapons/M16A2/"),
        TEXT("/Game/Weapons/M4DrumDrop/"),
        TEXT("/Game/Weapons/M4MuzzlesV1/"),
        TEXT("/Game/Weapons/M4HK416Audio/"),
        TEXT("/Game/Weapons/M4VREGripExtensions/"),
        TEXT("/Game/Weapons/GunplayFX/"),
        TEXT("/Game/Weapons/AttachmentFinish20260913/"),
        TEXT("/Game/Weapons/ExtMagContact20260919/"),
        TEXT("/Game/Weapons/FreeFirearmAudio20260913/"),
        TEXT("/Game/Weapons/RifleTacticalSprint20260915/"),
        TEXT("/Game/Weapons/DualPistolQuickCombat20260920/"),
        TEXT("/Game/Weapons/AKMDrumFreeDrop20260920/"),
        TEXT("/Game/Weapons/TacticalSuppressor20260913/"),
        TEXT("/Game/Items/"),
        TEXT("/Game/Characters/Mannequins/PlayerBodySkin"),
    };

    bool IsUnderExpandRoot(const FString& Path)
    {
        for (const TCHAR* Root : ExpandRoots)
        {
            if (Path.StartsWith(Root))
            {
                return true;
            }
        }
        return false;
    }

    /** Every asset inside the given package folders, recursively. This is what covers
     *  the Printf-built clip and sound names (A_A762_<clip>, S_AKM_<cue>, ...), which no
     *  static enumeration can list. */
    void ExpandFolders(TSet<FSoftObjectPath>& Out)
    {
        if (GExpandFolders == 0)
        {
            return;
        }
        FAssetRegistryModule& Module = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
        IAssetRegistry& Registry = Module.Get();

        // The folders that hold a directly requested asset, plus the explicit roots.
        TSet<FString> Folders;
        for (const TCHAR* Path : FPSPreloadRegistry::Paths)
        {
            const FString Package(Path);
            if (!IsUnderExpandRoot(Package))
            {
                continue;
            }
            int32 Slash = INDEX_NONE;
            if (Package.FindLastChar(TEXT('/'), Slash) && Slash > 0)
            {
                Folders.Add(Package.Left(Slash));
            }
        }
        for (const TCHAR* Root : ExpandRoots)
        {
            Folders.Add(FString(Root).LeftChop(1));
        }

        TArray<FAssetData> Assets;
        for (const FString& Folder : Folders)
        {
            Registry.GetAssetsByPath(FName(*Folder), Assets, /*bRecursive*/ true);
        }
        for (const FAssetData& Asset : Assets)
        {
            const FString Package = Asset.PackageName.ToString();
            if (IsWantedPath(Package) && IsUnderExpandRoot(Package))
            {
                AddPath(Out, Package);
            }
        }
        UE_LOG(LogTemp, Display, TEXT("BodyAssetPreloader: %d folders expanded via the asset registry"),
            Folders.Num());
    }

    /** Only content under these roots is warmed; plugin and engine content is left alone. */
    bool IsWantedPath(const FString& Path)
    {
        if (!Path.StartsWith(TEXT("/Game/")))
        {
            return false;
        }
        // World packages belong to map travel, not equipment warmup. Keeping an
        // asynchronously loaded world package alive across LoadMap's GC can leave
        // a package without its world and make a joining client fail to load it.
        // Development and audit-only content is deliberately excluded as well.
        static const TCHAR* SkipRoots[] = { TEXT("/Game/GameMaps/"), TEXT("/Game/Dev/"), TEXT("/Game/Developers/"), TEXT("/Game/Test/") };
        for (const TCHAR* Skip : SkipRoots)
        {
            if (Path.StartsWith(Skip))
            {
                return false;
            }
        }
        return true;
    }

    void AddPath(TSet<FSoftObjectPath>& Out, const FString& Path)
    {
        if (IsWantedPath(Path))
        {
            // Registry entries are package names; reflected/inventory references
            // include the object name. They must share one admission/retention key.
            const FString ObjectPath = Path.Contains(TEXT("."))
                ? Path : Path + TEXT(".") + FPackageName::GetShortName(Path);
            Out.Add(FSoftObjectPath(ObjectPath));
        }
    }

    template <typename T>
    void AddSoft(TSet<FSoftObjectPath>& Out, const TSoftObjectPtr<T>& Soft)
    {
        if (!Soft.IsNull())
        {
            AddPath(Out, Soft.ToSoftObjectPath().ToString());
        }
    }

    /** Pulls every asset a component already references, which is exactly the set a
     *  runtime weapon swap re-loads: the viewmodel mesh, its materials, the static
     *  attachment parts and their materials. */
    void CollectFromComponent(TSet<FSoftObjectPath>& Out, UActorComponent* Component)
    {
        if (const auto* Skeletal = Cast<USkeletalMeshComponent>(Component))
        {
            if (const USkeletalMesh* Mesh = Skeletal->GetSkeletalMeshAsset())
            {
                AddPath(Out, Mesh->GetPathName());
                for (const auto& Material : Mesh->GetMaterials())
                {
                    if (Material.MaterialInterface)
                    {
                        AddPath(Out, Material.MaterialInterface->GetPathName());
                    }
                }
            }
            if (const UPhysicsAsset* Physics = Skeletal->GetPhysicsAsset())
            {
                AddPath(Out, Physics->GetPathName());
            }
        }
        else if (const auto* Static = Cast<UStaticMeshComponent>(Component))
        {
            if (const UStaticMesh* Mesh = Static->GetStaticMesh())
            {
                AddPath(Out, Mesh->GetPathName());
            }
        }

        if (const UMeshComponent* MeshComponent = Cast<UMeshComponent>(Component))
        {
            for (int32 Index = 0; Index < MeshComponent->GetNumOverrideMaterials(); ++Index)
            {
                if (const UMaterialInterface* Material = MeshComponent->GetMaterial(Index))
                {
                    AddPath(Out, Material->GetPathName());
                }
            }
        }
    }

    /** Soft references held directly on the class (animations and sounds declared as
     *  UPROPERTY TSoftObjectPtr or as object properties). */
    void CollectFromClassDefaults(TSet<FSoftObjectPath>& Out, UClass* Class)
    {
        if (!Class)
        {
            return;
        }
        for (UObject* Default = Class->GetDefaultObject(); Default; Default = nullptr)
        {
            if (const UClass* ClassToInspect = Default->GetClass())
            {
                for (TFieldIterator<FProperty> It(ClassToInspect); It; ++It)
                {
                    FProperty* Property = *It;
                    if (const auto* SoftObject = CastField<FSoftObjectProperty>(Property))
                    {
                        const FSoftObjectPtr& Value = SoftObject->GetPropertyValue_InContainer(Default);
                        AddPath(Out, Value.ToSoftObjectPath().ToString());
                    }
                    else if (const auto* ObjectProperty = CastField<FObjectProperty>(Property))
                    {
                        if (const UObject* Value = ObjectProperty->GetPropertyValue_InContainer(Default))
                        {
                            if (Value->IsAsset())
                            {
                                AddPath(Out, Value->GetPathName());
                            }
                        }
                    }
                }
            }
            break;
        }
    }

    /** Fixed body/animation resources; outfit recipes belong to the carried set. */
    void CollectFromBodyConfig(TSet<FSoftObjectPath>& Out, TSharedPtr<FJsonObject>& CachedConfig)
    {
        FString Json;
        const FString ConfigPath = FPaths::ProjectContentDir() / TEXT("ColdSteelData/player_body.json");
        if (!FFileHelper::LoadFileToString(Json, *ConfigPath))
        {
            return;
        }
        TSharedPtr<FJsonObject> Root;
        if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
        {
            return;
        }
        CachedConfig = Root;

        FString BodyMesh;
        if (Root->TryGetStringField(TEXT("body_mesh"), BodyMesh))
        {
            AddPath(Out, BodyMesh);
        }
        if (Root->TryGetStringField(TEXT("weapon_pose_reference_mesh"), BodyMesh)) AddPath(Out,BodyMesh);

        const TSharedPtr<FJsonObject>* Clips = nullptr;
        if (Root->TryGetObjectField(TEXT("clips"), Clips))
        {
            for (const auto& Pair : (*Clips)->Values)
            {
                if (Pair.Value.IsValid())
                {
                    AddPath(Out, Pair.Value->AsString());
                }
            }
        }

        // ApplyAppearance already asynchronously loads the selected head, its
        // shared facial grooms and selected hairstyle, retaining the request
        // until the real components own them. Do not pin every catalogue variant
        // in this GameInstance-wide bootstrap batch after the player changes hair.
        // Legacy ApplyOutfit also has an async recipe fallback for newly acquired
        // items. Preloading every catalog entry is no longer needed for swaps.
    }

    /** Every weapon the inventory can equip. The paths are read from each item's own
     *  Data blob, so this uses the same text layer the equipment and UI code use and
     *  materialises no items (CreateItem mints a GUID per call). */
    void CollectFromInventory(TSet<FSoftObjectPath>& Out, UColdSteelStatusModel* Model,
        const TSharedPtr<FJsonObject>& Config)
    {
        if (!Model)
        {
            return;
        }
        static const TCHAR* AssetKeys[] = {
            TEXT("viewmodel_mesh"), TEXT("world_mesh"), TEXT("tool_viewmodel"),
            TEXT("tool_mesh"), TEXT("mesh"), TEXT("preview_mesh"),
        };
        const TSharedPtr<FJsonObject>* Outfits = nullptr;
        if (Config) Config->TryGetObjectField(TEXT("outfits"), Outfits);
        const auto* Shirt=Model->Items().FindByPredicate([](const FColdSteelItem& Item){return Item.Place==1&&Item.Cell==7;});
        const FName ShirtDefinition=Shirt?FName(*Shirt->Definition):NAME_None;
        TSet<FString> Definitions;
        for (const FColdSteelItem& Item : Model->Items())
        {
            // Warehouse/world records share this array but are not carried gear.
            if (Item.Place != 0 && Item.Place != 1 && Item.Place != 5) continue;
            for (const TCHAR* Key : AssetKeys)
            {
                const FString Value = ColdSteelInventory::Text(Item, Key);
                if (!Value.IsEmpty())
                {
                    AddPath(Out, Value);
                }
            }
            if (Outfits && !Definitions.Contains(Item.Definition))
            {
                Definitions.Add(Item.Definition);
                if (const auto Recipe = (*Outfits)->TryGetField(Item.Definition))
                    FPSBodyOutfitResources::GatherOutfit(Recipe, ShirtDefinition, Out);
            }
        }
    }
}

void UFPSBodyAssetPreloader::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    RecordResourceState(TEXT("Body.Initialize"));
    TickHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateWeakLambda(this, [this](float DeltaTime)
        {
            OnTick(DeltaTime);
            return true;
        }));
}

void UFPSBodyAssetPreloader::Deinitialize()
{
    SpawnAssets.Reset(); CapturedSpawnClasses.Reset();
    RecordResourceState(TEXT("Body.BeforeDeinitialize"));
    ++InventoryRequestGeneration;
    if (StatusModel.IsValid()) StatusModel->OnChanged.Remove(InventoryChangedHandle);
    InventoryChangedHandle.Reset(); StatusModel.Reset();
    if (PendingInventoryHandle) PendingInventoryHandle->CancelHandle();
    PendingInventoryHandle.Reset(); InventoryHandle.Reset(); InventoryPaths.Reset(); BodyConfig.Reset();
    if (TickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
        TickHandle.Reset();
    }
    // The streamable manager also owns pending handles. Dropping our pointer
    // alone leaves their requests alive after this GameInstance has shut down.
    for (const auto& Handle : Handles)
        if (Handle.IsValid() && !Handle->HasLoadCompleted()) Handle->CancelHandle();
    Handles.Reset();
    RecordResourceState(TEXT("Body.AfterDeinitialize"));
    Super::Deinitialize();
}

void UFPSBodyAssetPreloader::RecordResourceState(const TCHAR* Phase) const
{
    int32 Pending = 0;
    for (const auto& Handle : Handles)
        if (Handle && !Handle->HasLoadCompleted() && !Handle->WasCanceled()) ++Pending;
    TArray<FSoftObjectPath> RetainedPaths;
    if (InventoryHandle) InventoryHandle->GetRequestedAssets(RetainedPaths);
    FPSResourceLifecycle::Record(this, Phase, {
        {TEXT("bootstrap_handles"), Handles.Num()}, {TEXT("bootstrap_pending_handles"), Pending},
        {TEXT("bootstrap_requested_path_history"), RequestedPaths.Num()},
        {TEXT("inventory_target_paths"), InventoryPaths.Num()},
        {TEXT("inventory_retained_paths"), RetainedPaths.Num()},
        {TEXT("inventory_pending_handle"), PendingInventoryHandle.IsValid() ? 1 : 0}});
}

void UFPSBodyAssetPreloader::OnTick(float /*DeltaTime*/)
{
    // Keeps ticking until a game world exists; KickoffOnce sets the flag itself.
    if (!bKickedOff && FPSBodyPreloadPrivate::GAsyncPreload != 0)
    {
        KickoffOnce();
    }
    if (bKickedOff && FPSBodyPreloadPrivate::GAsyncPreload != 0)
    {
        const double Now = FPlatformTime::Seconds();
        if (Now < NextInventoryRefreshSeconds) return;
        NextInventoryRefreshSeconds = Now + .5;
        auto* World = GetGameInstance()->GetWorld();
        if (!World || !World->IsGameWorld()) return;
        if (InventoryWorld.Get() != World) { InventoryWorld = World; bInventoryDirty = true; }
        if (bInventoryDirty) { bInventoryDirty = false; CollectFromStatusModel(); }
    }
}

void UFPSBodyAssetPreloader::KickoffOnce()
{
    UWorld* World = GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr;
    // Editor preview and inactive worlds would warm assets from the wrong context.
    if (!World || !World->IsGameWorld())
    {
        return;
    }
    bKickedOff = true;

    TSet<FSoftObjectPath> Paths;
    FPSBodyPreloadPrivate::CollectFromBodyConfig(Paths, BodyConfig);
    FPSBodyPreloadPrivate::CollectFromClassDefaults(Paths, AFPSGAMECharacter::StaticClass());

    // Component defaults carry the viewmodel and attachment meshes for the class,
    // including the per-weapon variants the family headers point at.
    if (const AActor* Defaults = Cast<AActor>(AFPSGAMECharacter::StaticClass()->GetDefaultObject()))
    {
        TInlineComponentArray<UActorComponent*> Components;
        Defaults->GetComponents(Components);
        for (UActorComponent* Component : Components)
        {
            FPSBodyPreloadPrivate::CollectFromComponent(Paths, Component);
        }
    }

    // Spend the bounded admission slots on the actual body/defaults/inventory
    // before speculative weapon-family candidates. Do not depend on TSet order
    // to keep currently needed equipment ahead of a generated registry.
    RequestAssets(Paths);
    const int32 PrimaryCount = RequestedPaths.Num();

    StatusModel = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (StatusModel.IsValid())
        InventoryChangedHandle = StatusModel->OnChanged.AddWeakLambda(this, [this]() { bInventoryDirty = true; });
    CollectFromStatusModel(); bInventoryDirty = false; InventoryWorld = World;

    TSet<FSoftObjectPath> EquipmentPaths;
    if (FPSBodyPreloadPrivate::GPreloadCandidates != 0)
    {
        // A literal registry is not the equipped asset set. It also contains
        // mutually exclusive fallback revisions which runtime loaders will not
        // select together. Do not pin all their GPU resources by default.
        for (const TCHAR* Path : FPSPreloadRegistry::Paths)
        {
            FPSBodyPreloadPrivate::AddPath(EquipmentPaths, Path);
        }
    }
    const int32 NamedCount = EquipmentPaths.Num();
    if (FPSBodyPreloadPrivate::GPreloadCandidates != 0)
        FPSBodyPreloadPrivate::ExpandFolders(EquipmentPaths);
    RequestAssets(EquipmentPaths);

    UE_LOG(LogTemp, Display,
        TEXT("BodyAssetPreloader: requested %d assets asynchronously (fixed body/defaults=%d, additional equipment=%d, registry candidates=%d, folder candidates=%d); carried scope has %d paths"),
        GetRequestedCount(), PrimaryCount, RequestedPaths.Num() - PrimaryCount,
        NamedCount, EquipmentPaths.Num() - NamedCount, InventoryPaths.Num());
}

void UFPSBodyAssetPreloader::UpdateLoadedCount()
{
    LoadedCount = 0;
    for (const auto& Path : RequestedPaths) LoadedCount += Path.ResolveObject() != nullptr;
    for (const auto& Path : InventoryPaths) LoadedCount += Path.ResolveObject() != nullptr;
}

void UFPSBodyAssetPreloader::CollectFromStatusModel()
{
    auto* Model = StatusModel.Get();
    if (!Model) return;
    TSet<FSoftObjectPath> Wanted;
    FPSBodyPreloadPrivate::CollectFromInventory(Wanted, Model, BodyConfig);
    for (const auto& Path : RequestedPaths) Wanted.Remove(Path);
    const int32 Limit = FPSBodyPreloadPrivate::GMaxAssets > 0
        ? FMath::Max(0, FPSBodyPreloadPrivate::GMaxAssets - RequestedPaths.Num()) : MAX_int32;
    if (Wanted.Num() > Limit)
    {
        TArray<FSoftObjectPath> Ordered = Wanted.Array();
        Ordered.Sort([](const auto& A, const auto& B) { return A.ToString() < B.ToString(); });
        Wanted.Reset();
        for (int32 I = 0; I < Limit; ++I) Wanted.Add(Ordered[I]);
    }
    bool Same = Wanted.Num() == InventoryPaths.Num();
    for (const auto& Path : Wanted) if (!InventoryPaths.Contains(Path)) { Same = false; break; }
    if (Same) return;
    const uint64 Generation = ++InventoryRequestGeneration;
    if (PendingInventoryHandle) PendingInventoryHandle->CancelHandle();
    PendingInventoryHandle.Reset(); InventoryPaths = MoveTemp(Wanted);
    if (InventoryPaths.IsEmpty())
    {
        InventoryHandle.Reset(); UpdateLoadedCount();
        RecordResourceState(TEXT("Body.InventoryReleased"));
        UE_LOG(LogTemp, Display, TEXT("BodyAssetPreloader: released carried-gear scope (no carried paths)"));
        return;
    }
    // Keep the previous set until the new async set finishes. Real equipped,
    // dropped and preview components retain their own assets after this handoff.
    PendingInventoryHandle = UAssetManager::GetStreamableManager().RequestAsyncLoad(InventoryPaths.Array(),
        FStreamableDelegate::CreateWeakLambda(this, [this, Generation]()
        {
            if (Generation != InventoryRequestGeneration) return;
            InventoryHandle = MoveTemp(PendingInventoryHandle);
            UpdateLoadedCount();
            RecordResourceState(TEXT("Body.InventoryReplaced"));
            UE_LOG(LogTemp, Display, TEXT("BodyAssetPreloader: replaced carried-gear scope (%d paths); obsolete scope released"), InventoryPaths.Num());
        }), FStreamableManager::DefaultAsyncLoadPriority);
    RecordResourceState(TEXT("Body.InventoryRequested"));
}

void UFPSBodyAssetPreloader::RequestAssets(const TSet<FSoftObjectPath>& Paths)
{
    if (Paths.Num() == 0 || !GetGameInstance())
    {
        return;
    }
    TArray<FSoftObjectPath> ToRequest;
    ToRequest.Reserve(Paths.Num());
    for (const FSoftObjectPath& Path : Paths)
    {
        if (Path.IsNull() || RequestedPaths.Contains(Path) || InventoryPaths.Contains(Path))
        {
            continue;
        }
        if (FPSBodyPreloadPrivate::GMaxAssets > 0 && GetRequestedCount() >= FPSBodyPreloadPrivate::GMaxAssets)
        {
            UE_LOG(LogTemp, Warning, TEXT("BodyAssetPreloader: asset cap %d reached, %d paths skipped"),
                FPSBodyPreloadPrivate::GMaxAssets, Paths.Num() - ToRequest.Num());
            break;
        }
        RequestedPaths.Add(Path);
        ToRequest.Add(Path);
    }
    if (ToRequest.Num() == 0)
    {
        return;
    }

    TWeakObjectPtr<UFPSBodyAssetPreloader> WeakThis(this);
    TSharedPtr<FStreamableHandle> Handle = UAssetManager::GetStreamableManager().RequestAsyncLoad(
        ToRequest,
        FStreamableDelegate::CreateWeakLambda(this, [WeakThis]()
        {
            if (UFPSBodyAssetPreloader* Self = WeakThis.Get())
            {
                // Primary and optional batches may complete in either order.
                // Report resolved objects, not all requests when the first finishes.
                Self->UpdateLoadedCount();
                UE_LOG(LogTemp, Display, TEXT("BodyAssetPreloader: %d / %d assets loaded"),
                    Self->LoadedCount, Self->GetRequestedCount());
            }
        }),
        // Default priority (0): AsyncLoadHighPriority (100) competes with the streaming
        // the game itself needs at startup and measurably slowed the warm-up instead of
        // helping it -- with it, slow loads went 42 -> 60.
        FStreamableManager::DefaultAsyncLoadPriority);
    if (Handle.IsValid())
    {
        Handles.Add(Handle);
        RecordResourceState(TEXT("Body.BootstrapRequested"));
    }
}
