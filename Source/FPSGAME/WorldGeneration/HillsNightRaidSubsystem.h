#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "HillsNightRaidSubsystem.generated.h"

class AActor;
class ATemperateHillsWorld;
class AChapelShrine;
class AHillsNightPortal;
class AFPSWeatherManager;
class ANurseZombie;
class APawn;
class APlayerController;
class AHillsNightReplicationGate;
struct FStreamableHandle;
class FNetGUIDCache;

/** Server-owned nightly spawn budget; the existing monster BT owns all combat decisions. */
UCLASS()
class FPSGAME_API UHillsNightRaidSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
    /** Terrain-only pins; these do not expand the player's vegetation or rendering view radius. */
    void GetGroundPins(TArray<FVector>& Centers,FVector& Village,float& VillageRadius) const;
    bool Checkpoint();
    bool IsSessionReady() const {return bSessionReady&&!bRestorePending;}
    bool AreAssetsReady() const {return !bEnabled||bAssetsReady;}
    bool HasAssetPreparationFailed() const {return bAssetPreparationFailed;}
    bool IsViewerPrepared(const AActor* Viewer) const;
private:
    bool RestoreSession();
    bool RestoreActors();
    void WorldTearingDown(UWorld* World);
    ANurseZombie* CreateRaider(bool Heavy,const FTransform& Transform,float SavedHealth=-1.f);
    UPROPERTY() TObjectPtr<class UHillsNightRaidSave> PendingSave;
    FString SaveSlot;
    bool bClockRestored=false,bSessionReady=false,bRestorePending=false,bSaveWritable=true;
    int32 RestoreIndex=0;
    double NextCheckpoint=0.;
    enum class ESpawnResult : uint8
    {Spawned,PlayerNearby,NavigationPending,NoNavigation,NoSpawnFloor,NoShrineApproach,NoRoute,Occupied,SpawnRejected,MissingController};
    void PrepareAssets();
    void AssetsReady();
    void ReleaseNetworkLoadingPolicy();
    bool ChoosePortalSite();
    bool IsPortalSpaceClear(const FVector& Ground) const;
    bool IsPlayerNear(const FVector& Point,float Distance) const;
    ESpawnResult SpawnOne();
    static const TCHAR* SpawnResultName(ESpawnResult Result);
    int32 LivingCount() const;
    void UpdateInvokers();
    void UpdateReplicationGates();
    TMap<TWeakObjectPtr<APlayerController>,TWeakObjectPtr<AHillsNightReplicationGate>> ReplicationGates;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<AChapelShrine> Shrine;
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    TWeakObjectPtr<AHillsNightPortal> Portal;
    TArray<TWeakObjectPtr<ANurseZombie>> Raiders;
    TArray<TWeakObjectPtr<APawn>> PlayerInvokers;
    UPROPERTY() TArray<TSubclassOf<ANurseZombie>> MonsterClasses;
    TSharedPtr<FStreamableHandle> Preload;
    TWeakPtr<FNetGUIDCache> PreparedNetCache;
    uint8 PreviousNetLoadMode=0;
    int32 AssetLoadFailures=0;
    bool bAssetPreparationFailed=false;
    FRandomStream Random;
    FVector PortalSite=FVector::ZeroVector;
    FRotator PortalFacing=FRotator::ZeroRotator;
    bool bEnabled=true,bAssetsReady=false,bNight=false,bClockInitialized=false,bSiteChosen=false;
    int32 NightSerial=MIN_int32,SpawnedThisNight=0,WaveRemaining=0;
    int32 SpawnFailures=0,GroundWaitAttempts=0;
    int32 MaxAlive=12,MaxPerNight=36,WaveSize=3;
    float NightStart=19.f,NightEnd=6.f,WaveInterval=30.f,WarmupSeconds=12.f,Durability=1800.f;
    double NextUpdate=0.,NextPortalAttempt=0.,NextSpawn=0.,NextWave=0.,NextPlacementLog=0.;
    double NextAssetAttempt=0.,NextSpawnLog=0.;
};
