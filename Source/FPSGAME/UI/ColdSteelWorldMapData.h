#pragma once

#include "CoreMinimal.h"
#include "../WorldGeneration/TemperateIronOutcrops.h"
#include "UObject/StrongObjectPtr.h"
#include "Engine/Texture2D.h"

class APawn;
class ATemperateHillsWorld;
class FColdSteelHillsMap;
struct FColdSteelDungeonMap;
struct FStreamableHandle;
struct FColdSteelMapSurfaceCache
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ATemperateHillsWorld> Terrain;
    FString Region;
    FIntVector Origin = FIntVector::ZeroValue;
    uint32 TerrainRevision = 0;
    TArray<TWeakObjectPtr<ULevel>> VisibleLevels;
    FBox2D Bounds = FBox2D(ForceInit);
    double TraceTop = 0., TraceBottom = 0.;
    TStrongObjectPtr<UTexture> Surface;
    TStrongObjectPtr<UTexture2D> ReliefOverlay;
};

struct FColdSteelMapLandmark
{
    FVector2D Point;
    FString Label;
    int32 Floor;
    TWeakObjectPtr<AActor> Actor;
    FString PortalDestination;
    double ActorZ = 0.;
    bool bSmithLesson = false;
    bool bTerrainStart = false;
};

/** One local viewing session. All coordinates are world-space centimetres (+X north). */
struct FColdSteelWorldMapData
{
    void Open(APawn* Viewer, FColdSteelMapSurfaceCache& Cache, FColdSteelDungeonMap& Discovery);
    void SampleSurface(APawn* Viewer, FColdSteelMapSurfaceCache& Cache);
    bool FinishLoadingHubPhoto(APawn* Viewer, FColdSteelMapSurfaceCache& Cache);
    bool RefreshTerrainIfChanged(APawn* Viewer, FColdSteelMapSurfaceCache& Cache);
    void NotifyStreamChanged() { bStreamChanged=bUsesSampledSurface; }
    bool TrackLandmark(AActor* Actor);
    bool RefreshLandmarks();
    bool RemoveLevelLandmarks(ULevel* Level);
    bool MarkerGround(APawn* Viewer,FVector2D XY,int32 Floor,FVector& Position) const;

    FString Title, RegionKey;
    FBox2D Bounds = FBox2D(ForceInit);
    TArray<FColdSteelMapLandmark> Landmarks;
    TStrongObjectPtr<UTexture> Surface;
    TStrongObjectPtr<UTexture2D> ReliefOverlay;
    bool bDungeon = false;
    bool bWaitingForDungeon = false;
    bool bWaitingForForest=false;
    bool ForestIdentityChanged(APawn* Viewer) const;
    bool IsSampling() const { return bPreparingHills || !Heights.IsEmpty(); }
    bool bSurfaceUnavailable = false;
    bool IsLoadingHubPhoto() const { return HubPhotoRequest.IsValid(); }

private:
    const FColdSteelDungeonMap* Fog = nullptr;
    TWeakObjectPtr<ULevel> DungeonLevel;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TArray<float> Heights;
    TArray<FColor> ForestPixels;
    int32 GridSize=192, NextShade=0;
    bool bForestMap=false;
    bool bUsesSampledSurface=false, bStreamChanged=false;
    int32 ForestSeed=0;
    FGuid ForestWorldId;
    bool bPreparingHills = false;
    TSharedPtr<FColdSteelHillsMap> HillsMap;
    TSharedPtr<FStreamableHandle> HubPhotoRequest;
    TArray<TWeakObjectPtr<ULevel>> SampledLevels;
    uint32 SampledTerrainRevision = 0;
    double TraceTop = 0, TraceBottom = 0;
    int32 NextSample = 0;
    bool RefreshSmithDestination();
    uint64 SmithRock = 0;
    TemperateIronOutcrops::FSearch IronSearch;
    double RetrySmithLocationAt = 0.;
    bool bSmithReturn = false;
    void FinishSurface();
    bool UseHubPhoto(UTexture2D* Photo, const UWorld* World);
    void BeginSampledSurface(APawn* Viewer, FColdSteelMapSurfaceCache& Cache);
};
