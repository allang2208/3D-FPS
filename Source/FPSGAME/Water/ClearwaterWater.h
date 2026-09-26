#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ClearwaterWater.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UPostProcessComponent;

/**
 * Clearwater water body: a gridded plane displaced by the reduced Clearwater spectrum,
 * shaded by the optics block ported from https://github.com/Aureliengmz/clearwater (MIT).
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
 * Ticking exists only for effects a material cannot animate on its own: the caustic scroll
 * follows the sun, the impact ripples follow the interaction system, and the underwater
 * blendable follows the camera. Everything else is evaluated in the shader.
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

    /** Pushes the sun-driven caustic scroll into the water and seabed instances. */
    void UpdateCaustics(float TimeSeconds);
    /** Ages the impact ripple slots and writes them to the material. */
    void UpdateRipples(float DeltaSeconds);
    /** Raises/lowers the underwater blendable from the camera position. */
    void UpdateSubmerged();

    /** Dynamic instance created by the FX subsystem, or one we make ourselves. */
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WaterMID = nullptr;

    /** The first dynamic instance found on any mesh tagged as the seabed, if present. */
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SeabedMID = nullptr;

    /** Owns the underwater blendable so its weight can be driven without an actor reference. */
    UPROPERTY(Transient) TObjectPtr<UPostProcessComponent> UnderwaterVolume = nullptr;

    /** Cached so the submerged toggle never has to hit the asset registry. */
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> UnderwaterMaterial = nullptr;

    /** Ring buffer of impact ripples: xy world position, z age in seconds, w strength. */
    FVector4 RippleSlots[4] = {
        FVector4(0, 0, -1, 0), FVector4(0, 0, -1, 0),
        FVector4(0, 0, -1, 0), FVector4(0, 0, -1, 0) };
    int32 RippleCursor = 0;
    /** 1 while any ripple slot is still ringing, so the material is only written when needed. */
    int32 RipplesActive = 0;

    float SunElevationDeg = 31.f;
    float SunAzimuthDeg = 6.f;
    bool bRegistered = false;
    bool bSubmerged = false;
};
