#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "TemperateVillageSite.h"
#include "VillageDistantGlow.generated.h"

class AFPSWeatherManager;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UPointLightComponent;

/**
 * Lightweight ultra-far night silhouette & beacon system for the temperate hills
 * village (60 m - 1.4 km):
 * - Mode 0: Hooded exterior lamp sprites bound to live repaired fixtures
 * - Mode 1: Wide, ground-hugging backlit valley haze dome behind silhouettes
 * - Mode 2: Horizontal terrain-seated warm ground spill pools under lamps
 * - WindowISM: Physically embedded warm windows on repaired village buildings
 * - Tier 2: One low unshadowed distant ambient bounce light
 */
UCLASS(ClassGroup=WorldGeneration)
class FPSGAME_API UVillageDistantGlowComponent : public USceneComponent
{
    GENERATED_BODY()

public:
    UVillageDistantGlowComponent();

    void InitializeForSite(const FTemperateVillageSite& Site, TFunctionRef<double(double, double)> TerrainHeightFn);

    /** Call after building repairs or street light refreshes so anchors re-sync cleanly. */
    void RequestAnchorRefresh();

    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
    void RebuildAnchors();

    UPROPERTY(Transient)
    TObjectPtr<UInstancedStaticMeshComponent> BeaconISM;

    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> BeaconMID;

    UPROPERTY(Transient)
    TObjectPtr<UInstancedStaticMeshComponent> WindowISM;

    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> WindowMID;

    UPROPERTY(Transient)
    TObjectPtr<UPointLightComponent> TownGlowLight;

    UPROPERTY(Transient)
    TWeakObjectPtr<AFPSWeatherManager> Weather;

    FTemperateVillageSite CachedSite;
    FVector TownCenterWorld = FVector::ZeroVector;
    float LastNightIntensity = -1.f;
    float LastBounceIntensity = -1.f;
    uint32 LastSyncedRevision = MAX_uint32;
    int32 LastSyncedFixtureCount = -1;
    double NextFixtureCheckTime = 0.0;
    bool bAnchorsDirty = true;
    bool bInitialized = false;
};
