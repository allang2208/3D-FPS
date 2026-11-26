// Player-body async preloader (2026-09-21).
//
// Measurements on DayNight_Lighting (see Docs/Performance/hitch-player-body-20260921.md)
// showed 41 synchronous package loads of 25-467 ms each, all inside the first
// ~10 s of play. The slow ones are the world-space weapon copies that
// UFPSPlayerBodyComponent::CaptureEquipment()/RebuildWeapons() pull in, plus the
// body mesh and the 60 clips listed in Content/ColdSteelData/player_body.json.
//
// Weapon/body bootstrap paths keep their existing behavior. Carried equipment
// has a replaceable async scope; legacy outfit swaps also request their recipe
// asynchronously before replacing the old visible assembly.
//
// Speculative literal-registry candidates are opt-in: the registry also contains
// mutually exclusive fallback meshes, which must not all be pinned by default.
// Diagnostic switches: fps.body.AsyncPreload (1), fps.body.AsyncPreloadCandidates (0).

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Engine/StreamableManager.h"

#include "FPSBodyAssetPreloader.generated.h"

UCLASS()
class FPSGAME_API UFPSBodyAssetPreloader : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    /** Requests every asset path in the set; already-resident paths are skipped. */
    void RequestAssets(const TSet<FSoftObjectPath>& Paths);

    /** Keep the actual native pawn bootstrap resident for subsequent joins/respawns.
     * Called before the saved equipment replaces these temporary defaults. */
    void RetainSpawnAssets(class AActor* Character);

    /** Diagnostics: what has been requested and how much has landed. */
    int32 GetRequestedCount() const { return RequestedPaths.Num() + InventoryPaths.Num(); }
    int32 GetLoadedCount() const { return LoadedCount; }

private:
    UPROPERTY() TArray<TObjectPtr<UObject>> SpawnAssets;
    TSet<TWeakObjectPtr<UClass>> CapturedSpawnClasses;
    void KickoffOnce();
    void OnTick(float DeltaTime);
    void CollectFromStatusModel();
    void UpdateLoadedCount();
    void RecordResourceState(const TCHAR* Phase) const;

    TSet<FSoftObjectPath> RequestedPaths;
    TArray<TSharedPtr<FStreamableHandle>> Handles;
    // Fixed body/default references are separate from the replaceable carried set.
    TSet<FSoftObjectPath> InventoryPaths;
    TSharedPtr<FStreamableHandle> InventoryHandle, PendingInventoryHandle;
    TSharedPtr<class FJsonObject> BodyConfig;
    TWeakObjectPtr<class UColdSteelStatusModel> StatusModel;
    TWeakObjectPtr<UWorld> InventoryWorld;
    FDelegateHandle InventoryChangedHandle;
    uint64 InventoryRequestGeneration = 0;
    double NextInventoryRefreshSeconds = 0.;
    bool bInventoryDirty = true;
    FTSTicker::FDelegateHandle TickHandle;
    int32 LoadedCount = 0;
    bool bKickedOff = false;
};
