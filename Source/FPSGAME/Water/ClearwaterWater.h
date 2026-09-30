#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ClearwaterWater.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UPostProcessComponent;
class UDirectionalLightComponent;

/**
 * Clearwater water body: a gridded plane displaced by the reduced Clearwater spectrum,
 * with UE SingleLayerWater optics and a spectrum derived from Clearwater (MIT).
 *
 * The actor exists so the surface is a real UStaticMeshComponent. That matters for two
 * reasons:
 *   - URiverPilotFXSubsystem only accepts UStaticMeshComponent surfaces, so this is what
 *     lets bullets, footsteps and bodies interact with the water with no new FX code;
 *   - the engine handles culling and LOD for a static mesh, which a runtime-built
 *     dynamic mesh would have to reimplement.
 *
 * The surface is flat at rest (the material's world-position offset carries the waves and
 * the normal carries the detail), so the CPU-side height query is the actor Z rather than a
 * spectrum evaluation. That keeps gameplay queries deterministic and cheap, and it is what
 * the project's existing flat water bodies already assume.
 *
 * Hits and wakes belong to the shared water subsystem. The actor only updates cached
 * sunlight at 4 Hz and blends the underwater effect at 30 Hz; no per-frame world scans.
 */
UCLASS()
class FPSGAME_API AClearwaterWater : public AActor
{
    GENERATED_BODY()
public:
    AClearwaterWater();

    /** Resolves the surface mesh/material and registers with the water FX subsystem. */
    void Configure();
    static int32 Install(UWorld* World);

    /** World-space water height at rest, in centimetres. */
    UFUNCTION(BlueprintPure, Category = "Clearwater")
    float GetWaterHeight() const { return GetActorLocation().Z; }

    /** How deep the water is at a world location, clamped at zero. */
    UFUNCTION(BlueprintPure, Category = "Clearwater")
    float GetDepthAt(const FVector& WorldLocation) const;

    /**
     * True when URiverPilotFXSubsystem accepted this surface, i.e. bullets, footsteps and
     * body-water queries reach it. Always false when the impact footprint is missing.
     */
    UFUNCTION(BlueprintPure, Category = "Clearwater")
    bool HasWaterInteraction() const;

    /** True while the view is below the water plane and the underwater volume is weighted. */
    UFUNCTION(BlueprintPure, Category = "Clearwater")
    bool IsCameraSubmerged() const { return bSubmerged; }

    /** Adds an impact ripple at a world location. Called for bullet/footstep/body contacts. */
    UFUNCTION(BlueprintCallable, Category = "Clearwater")
    void AddImpactRipple(const FVector& WorldLocation, float Strength = 1.f);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;

    UPROPERTY() TObjectPtr<UStaticMeshComponent> Surface = nullptr;

private:
    bool RegisterWithWaterFX();
    void UnregisterFromWaterFX();

    /** Pushes the current scene sun into the seabed's baked-caustic projection. */
    void UpdateCaustics(float TimeSeconds);
    /** Raises/lowers the underwater blendable from the camera position. */
    void UpdateSubmerged(float DeltaSeconds);

    /** Dynamic instance created by the FX subsystem, or one we make ourselves. */
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WaterMID = nullptr;

    /** The first dynamic instance found on any mesh tagged as the seabed, if present. */
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SeabedMID = nullptr;

    /** Owns the underwater blendable so its weight can be driven without an actor reference. */
    UPROPERTY(Transient) TObjectPtr<UPostProcessComponent> UnderwaterVolume = nullptr;

    /** Cached so the submerged toggle never has to hit the asset registry. */
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> UnderwaterMaterial = nullptr;
    TWeakObjectPtr<UDirectionalLightComponent> SceneSun;
    float NextSunUpdate = 0.f;
    float SubmergedBlend = 0.f;
    bool bRegistered = false;
    bool bSubmerged = false;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> UnderwaterMID = nullptr;
};
