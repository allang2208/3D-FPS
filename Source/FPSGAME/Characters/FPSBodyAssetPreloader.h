// Player-body async preloader (2026-09-21).
//
// Measurements on DayNight_Lighting (see Docs/Performance/hitch-player-body-20260921.md)
// showed 41 synchronous package loads of 25-467 ms each, all inside the first
// ~10 s of play. The slow ones are the world-space weapon copies that
// UFPSPlayerBodyComponent::CaptureEquipment()/RebuildWeapons() pull in, plus the
// body mesh and the 60 clips listed in Content/ColdSteelData/player_body.json.
//
// Those call sites need the asset synchronously, so this does not restructure
// them. Instead it requests the same asset set through FStreamableManager before
// the character begins play, which turns the later synchronous load into a cache
// hit and takes the disk wait out of the frame.
//
// Diagnostic switches: `fps.body.AsyncPreload` (default 1) and `fpsbodypreload`.

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

    /** Diagnostics: what has been requested and how much has landed. */
    int32 GetRequestedCount() const { return RequestedPaths.Num(); }
    int32 GetLoadedCount() const { return LoadedCount; }

private:
    void KickoffOnce();
    void OnTick(float DeltaTime);
    void CollectFromStatusModel();

    TSet<FSoftObjectPath> RequestedPaths;
    TArray<TSharedPtr<FStreamableHandle>> Handles;
    /** Definitions already resolved from the inventory; resolved at most once. */
    TSet<FString> ScannedDefinitions;
    FTSTicker::FDelegateHandle TickHandle;
    int32 LoadedCount = 0;
    bool bKickedOff = false;
};