// Player-body async preloader implementation. See FPSBodyAssetPreloader.h.

#include "FPSBodyAssetPreloader.h"

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

    int32 GAsyncPreload = 1;
    int32 GMaxAssets = 400;
    int32 GExpandFolders = 0;

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
        TEXT("/Game/Weapons/A762/"),
        TEXT("/Game/Weapons/PKMLowpoly20260922/"),
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
                Out.Add(FSoftObjectPath(Package));
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
        // Development and audit-only content is deliberately excluded.
        static const TCHAR* SkipRoots[] = { TEXT("/Game/Dev/"), TEXT("/Game/Developers/"), TEXT("/Game/Test/") };
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
            Out.Add(FSoftObjectPath(Path));
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

    /** Player body mesh, every animation clip, and the outfit world meshes declared in
     *  Content/ColdSteelData/player_body.json. */
    void CollectFromBodyConfig(TSet<FSoftObjectPath>& Out)
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

        FString BodyMesh;
        if (Root->TryGetStringField(TEXT("body_mesh"), BodyMesh))
        {
            AddPath(Out, BodyMesh);
        }

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

        const TSharedPtr<FJsonObject>* Outfits = nullptr;
        if (Root->TryGetObjectField(TEXT("outfits"), Outfits))
        {
            for (const auto& Pair : (*Outfits)->Values)
            {
                const TSharedPtr<FJsonObject>* Settings = nullptr;
                if (!Pair.Value.IsValid() || !Pair.Value->TryGetObject(Settings))
                {
                    continue;
                }
                FString WorldMesh;
                if ((*Settings)->TryGetStringField(TEXT("world_mesh"), WorldMesh))
                {
                    AddPath(Out, WorldMesh);
                }
                FString WorldStaticMesh;
                if ((*Settings)->TryGetStringField(TEXT("world_static_mesh"), WorldStaticMesh))
                {
                    AddPath(Out, WorldStaticMesh);
                }
                const TSharedPtr<FJsonObject>* Overrides = nullptr;
                if ((*Settings)->TryGetObjectField(TEXT("body_materials"), Overrides) ||
                    (*Settings)->TryGetObjectField(TEXT("first_person_materials"), Overrides))
                {
                    for (const auto& Entry : (*Overrides)->Values)
                    {
                        if (Entry.Value.IsValid())
                        {
                            AddPath(Out, Entry.Value->AsString());
                        }
                    }
                }
            }
        }
    }

    /** Every weapon the inventory can equip. The paths are read from each item's own
     *  Data blob, so this uses the same text layer the equipment and UI code use and
     *  materialises no items (CreateItem mints a GUID per call). */
    void CollectFromInventory(TSet<FSoftObjectPath>& Out, UColdSteelStatusModel* Model)
    {
        if (!Model)
        {
            return;
        }
        static const TCHAR* AssetKeys[] = {
            TEXT("viewmodel_mesh"), TEXT("world_mesh"), TEXT("tool_viewmodel"),
            TEXT("tool_mesh"), TEXT("mesh"), TEXT("preview_mesh"),
        };
        for (const FColdSteelItem& Item : Model->Items())
        {
            for (const TCHAR* Key : AssetKeys)
            {
                const FString Value = ColdSteelInventory::Text(Item, Key);
                if (!Value.IsEmpty())
                {
                    AddPath(Out, Value);
                }
            }
        }
    }
}

void UFPSBodyAssetPreloader::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    TickHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateWeakLambda(this, [this](float DeltaTime)
        {
            OnTick(DeltaTime);
            return true;
        }));
}

void UFPSBodyAssetPreloader::Deinitialize()
{
    if (TickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
        TickHandle.Reset();
    }
    Handles.Reset();
    Super::Deinitialize();
}

void UFPSBodyAssetPreloader::OnTick(float /*DeltaTime*/)
{
    // Keeps ticking until a game world exists; KickoffOnce sets the flag itself.
    if (FPSBodyPreloadPrivate::GAsyncPreload != 0)
    {
        KickoffOnce();
    }
    if (bKickedOff && TickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
        TickHandle.Reset();
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
    FPSBodyPreloadPrivate::CollectFromBodyConfig(Paths);
    FPSBodyPreloadPrivate::CollectFromClassDefaults(Paths, AFPSGAMECharacter::StaticClass());

    // The equipment load sites read these compile-time constants, so this is the only
    // complete enumeration of the weapon viewmodels, sounds and attachment meshes.
    for (const TCHAR* Path : FPSPreloadRegistry::Paths)
    {
        FPSBodyPreloadPrivate::AddPath(Paths, Path);
    }

    if (UColdSteelStatusModel* Model = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        FPSBodyPreloadPrivate::CollectFromInventory(Paths, Model);
    }

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

    const int32 NamedCount = Paths.Num();
    FPSBodyPreloadPrivate::ExpandFolders(Paths);

    RequestAssets(Paths);

    UE_LOG(LogTemp, Display,
        TEXT("BodyAssetPreloader: requested %d assets asynchronously (%d named, %d recovered by folder expansion); toggle with fps.body.AsyncPreload"),
        RequestedPaths.Num(), NamedCount, RequestedPaths.Num() - NamedCount);
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
        if (Path.IsNull() || RequestedPaths.Contains(Path))
        {
            continue;
        }
        if (FPSBodyPreloadPrivate::GMaxAssets > 0 && RequestedPaths.Num() >= FPSBodyPreloadPrivate::GMaxAssets)
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
                Self->LoadedCount = Self->RequestedPaths.Num();
                UE_LOG(LogTemp, Display, TEXT("BodyAssetPreloader: %d assets resident"), Self->LoadedCount);
            }
        }),
        // Default priority (0): AsyncLoadHighPriority (100) competes with the streaming
        // the game itself needs at startup and measurably slowed the warm-up instead of
        // helping it -- with it, slow loads went 42 -> 60.
        FStreamableManager::DefaultAsyncLoadPriority);
    if (Handle.IsValid())
    {
        Handles.Add(Handle);
    }
}