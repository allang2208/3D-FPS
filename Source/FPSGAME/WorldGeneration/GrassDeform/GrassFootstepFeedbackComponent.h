#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Chaos/ChaosEngineInterface.h"
#include "Engine/DataAsset.h"
#include "Engine/EngineTypes.h"
#include "UObject/SoftObjectPtr.h"
#include "GrassFootstepFeedbackComponent.generated.h"

class UDecalComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UNiagaraComponent;
class UNiagaraSystem;

/**
 * One slot of the footstep decal trail.
 *
 * A reflected struct with UPROPERTY component references, following the project's existing pooled
 * decal pattern (WeatherSurfaceComponent's FWeatherSurfacePatch). The references matter: the MID is
 * created per slot and referenced only from the owning component's pool array, so without
 * reflection the garbage collector would be free to collect it out from under a live decal.
 */
USTRUCT()
struct FGrassFootstepDecalSlot
{
    GENERATED_BODY()

    UPROPERTY(Transient) TObjectPtr<UDecalComponent> Decal = nullptr;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Material = nullptr;

    /** Seconds since this decal was placed; >= DecalLifeSeconds means the slot is free. */
    float Age = 0.f;
    bool bInUse = false;
};

/**
 * Authoring asset for the M3 footstep feedback (plan section 5).
 *
 * Everything a designer may want to retune without a recompile lives here: which physical surfaces
 * count as "grass" (the whitelist that gates the whole feature) and which Niagara / decal assets to
 * use. The *runtime budget* numbers (pool sizes, radii, fade rates) are deliberately NOT here - they
 * are compile-time constants in GrassFootstepFeedbackComponent.h, together with the rest of the
 * M3 tuning, so a content edit cannot raise the per-frame cost of the system.
 *
 * The asset is created by Tools/GrassDeform/setup_assets_m3.py as
 * /Game/WorldGeneration/GrassDeform/DA_GrassFootstepFeedback.
 */
UCLASS(BlueprintType)
class FPSGAME_API UGrassFootstepFeedbackConfig : public UDataAsset
{
    GENERATED_BODY()

public:
    /**
     * Physical surfaces that trigger the feedback. Empty means "nothing triggers", which is the
     * safe default: the component then stays completely inert instead of stamping the RT on every
     * footstep in the level.
     *
     * Note the project's actual surface naming: UFPSFootstepAudioComponent plays its ground steps
     * with SurfaceType_Default (it classifies by name and passes Default through the plugin), so a
     * whitelist that only listed SurfaceType_Grass would never fire. setup_assets_m3.py therefore
     * seeds this set with the surface types whose *project* name reads as grass/dirt/soil/gravel
     * plus SurfaceType_Default, and the user can narrow it in the editor.
     */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Grass Footstep")
    TSet<TEnumAsByte<EPhysicalSurface>> Surfaces;

    /** Grass-bit + dust puff played at the contact point. Soft: the component resolves it on the
     *  first accepted footstep so the asset never forces a load at module startup. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Grass Footstep")
    TSoftObjectPtr<UNiagaraSystem> PuffSystem;

    /** Deferred decal material used for the trampled trail. One MID per pool slot, so the fade
     *  scalar is animated per decal. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Grass Footstep")
    TSoftObjectPtr<UMaterialInterface> DecalMaterial;

    /** Number of decal components in the trail pool. The pool is created lazily on the first
     *  accepted footstep and then reused forever; the user-visible acceptance criterion for M3 is
     *  that this number never grows (plan section 9). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Grass Footstep", meta = (ClampMin = "0", ClampMax = "64"))
    int32 DecalPoolSize = 12;

    /** Seconds a decal takes to fade to nothing. The oldest decal in the pool is recycled when all
     *  slots are in use, so this also bounds how far back the trail reaches. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Grass Footstep", meta = (ClampMin = "0.1"))
    float DecalLifeSeconds = 6.f;

    /** Hard cap on simultaneously live puffs. A footstep that arrives while this many puffs are
     *  still running is skipped (the stamp and the decal still happen), which is what keeps a
     *  sprint across grass from stacking an unbounded number of Niagara components. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Grass Footstep", meta = (ClampMin = "0", ClampMax = "512"))
    int32 PuffMaxActive = 64;
};

/**
 * Player-side footstep feedback for the GPU grass system (M3, plan section 5).
 *
 * Listens to UAutoFootstepEffectContext::OnFootstepPlayed - the plugin's single footstep exit - and,
 * for contacts on a whitelisted surface, does three bounded things:
 *
 *   1. StampTrample  : a single DrawMaterial on the deform RT (stronger and tighter than the
 *                      subsystem's own 10 Hz movement trail), directed along the travel vector.
 *   2. Niagara puff  : NS_GrassFootstepPuff at the contact, gated by a live-puff counter so the
 *                      number of running systems never exceeds PuffMaxActive.
 *   3. Decal trail   : a pooled UDecalComponent placed on the ground, faded out per-decal through
 *                      its own MID as it ages, oldest-slot-recycled when the pool is exhausted.
 *
 * Cost contract (plan section 7): the event path allocates nothing after the first step (all pools
 * and MIDs are built once, lazily), the per-frame path is one loop over at most DecalPoolSize
 * decals plus one loop over at most PuffMaxActive puff records, and the component ticks only while
 * a decal or a puff is still alive.
 *
 * Single-player presentation only: no replication, no authority checks, and a dedicated server
 * skips it entirely.
 */
UCLASS(ClassGroup = (Grass), meta = (BlueprintSpawnableComponent))
class FPSGAME_API UGrassFootstepFeedbackComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UGrassFootstepFeedbackComponent();

    //~ Begin UActorComponent
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    //~ End UActorComponent

    /**
     * Reset the trail: hides every pooled decal and releases the puff budget. Called automatically
     * on BeginPlay and on a teleport-sized jump; exposed for Blueprint so a respawn can clear the
     * trail the player left behind.
     */
    UFUNCTION(BlueprintCallable, Category = "Grass Footstep")
    void ResetTrail();

    /** Number of decals currently alive (visible, not yet faded out). Never exceeds the pool size;
     *  used by the M3 acceptance check "the trail does not leak". */
    UFUNCTION(BlueprintPure, Category = "Grass Footstep")
    int32 GetActiveDecalCount() const;

    /** Number of puffs the component believes are still running. */
    UFUNCTION(BlueprintPure, Category = "Grass Footstep")
    int32 GetActivePuffCount() const { return ActivePuffs; }

    // ---------------------------------------------------------------------------------------
    // M3 tuning. These live here (not in GrassDeformTuning.h, which M1/M2 own) so the whole
    // footstep budget is visible in one place. They are compile-time constants on purpose: the
    // designer-facing knobs are on UGrassFootstepFeedbackConfig instead.
    // ---------------------------------------------------------------------------------------

    /** Authoring asset. Leave empty in a Blueprint to run with the built-in defaults (a hard-coded
     *  soft path to DA_GrassFootstepFeedback is used instead). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Grass Footstep")
    TSoftObjectPtr<UGrassFootstepFeedbackConfig> Config;

    /** Surfaced for the debug HUD / Blueprint: true once the component has a usable config. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Grass Footstep")
    bool bReady = false;

private:
    // ---------------------------------------------------------------------------------------
    // Tuning constants (all M3 numbers; see the class comment for why they are here)
    // ---------------------------------------------------------------------------------------

    /** Radius of the single-foot flatten splat, cm. Smaller and stronger than the subsystem's
     *  10 Hz movement trail, so each step reads as a distinct footprint. */
    static constexpr float StepRadiusCm = 26.f;

    /** Flatten strength written by a footstep. Clamped to 1 by the subsystem anyway. */
    static constexpr float StepStrength = 0.85f;

    /** How much of the player's horizontal velocity is folded into the stamp's bend direction.
     *  Below this speed the stamp is direction-less (bend vector left neutral), which reads as
     *  "stepped straight down" rather than smearing a direction out of jitter. */
    static constexpr float StepDirectionMinSpeed = 40.f;

    /** Minimum seconds between two accepted footsteps. The character can report a landing and a
     *  stride contact in the same frame; this collapses them into one stamp. */
    static constexpr float StepCooldownSeconds = 0.08f;

    /** A horizontal jump longer than this (cm) between two contacts is treated as a teleport or a
     *  respawn: the trail is reset instead of being stretched across the map. */
    static constexpr float TeleportDistanceCm = 500.f;

    /** The contact point is pushed this far along the surface normal before the decal is placed,
     *  so the decal volume starts just above the ground instead of z-fighting with it. */
    static constexpr float DecalGroundOffsetCm = 2.f;

    /** Decal half-extent along the projection axis (local X), cm. UE decals project along local X,
     *  so this is the depth of the volume into the terrain. */
    static constexpr float DecalProjectionDepthCm = 32.f;

    /** Decal centre-to-edge extent on the ground plane (local Y/Z), cm. */
    static constexpr float DecalRadiusCm = 30.f;

    /** Puff spawn offset above the contact, cm, to keep the sprite out of the ground. */
    static constexpr float PuffHeightOffsetCm = 6.f;

    /** Scale applied to the puff system. */
    static constexpr float PuffScale = 1.f;

    /** Puff lifetime assumed when the Niagara system has not reported back yet. The component
     *  releases its puff slot either through the system's finish delegate or through this timer,
     *  whichever comes first, so a system that fails to finish can never leak the budget. */
    static constexpr float PuffFallbackLifeSeconds = 2.5f;

    /** Hard cap on live puff records; matches the documented PuffMaxActive ceiling so the fixed
     *  array below is never reallocated. */
    static constexpr int32 MaxPuffRecords = 512;

    // The remaining defaults (fallback asset paths and the decal fade parameter name) are
    // namespace-scope constants in GrassFootstepFeedbackComponent.cpp: they are strings, which
    // cannot be declared as in-class constant expressions portably.

    // ---------------------------------------------------------------------------------------
    // Pool records
    // ---------------------------------------------------------------------------------------

    /** One live puff. Kept as a record rather than as an array entry so the finish callback can
     *  identify its own slot without holding a component pointer into a pooled object. */
    struct FPuffRecord
    {
        TWeakObjectPtr<UNiagaraComponent> Component;
        float Remaining = 0.f;
        bool bInUse = false;
    };

    // ---------------------------------------------------------------------------------------
    // Internals
    // ---------------------------------------------------------------------------------------

    /** Subscribe to the plugin delegate under this component's name (idempotent). */
    void Subscribe();
    /** Drop the subscription. Safe to call when not subscribed. */
    void Unsubscribe();

    /** Handle one broadcast. Filters the surface whitelist, throttles and drives all three effects. */
    void HandleFootstep(EPhysicalSurface Surface, const FVector& Location, const FRotator& Rotation);

    /** Resolve the config and both soft assets once. Returns false while they are unavailable. */
    bool ResolveAssets();

    /** True when the surface is in the config whitelist. */
    bool IsSurfaceAccepted(EPhysicalSurface Surface) const;

    /** Push one trample stamp into the grass deform subsystem. */
    void StampGround(const FVector& Location);
    /** Spawn a puff if the live-puff budget allows it. */
    void SpawnPuff(const FVector& Location, const FVector& Normal);
    /** Place (or recycle) one decal from the trail pool. */
    void PlaceDecal(const FVector& Location, const FVector& Normal, const FVector& TravelDir);

    /** Build the decal pool on first use. Allocation-free afterwards. */
    void EnsureDecalPool();
    /** Release one puff slot by index. */
    void ReleasePuff(int32 Index);

    /** Niagara finish callback: releases the puff slot the system occupied. */
    UFUNCTION()
    void OnPuffFinished(UNiagaraComponent* FinishedComponent);

    /** Count of puffs the component believes are still alive. */
    int32 ActivePuffs = 0;

    /** Remaining cooldown before another footstep is accepted. */
    float Cooldown = 0.f;

    /** Last accepted contact, for the teleport test. */
    FVector LastContact = FVector::ZeroVector;
    bool bHasLastContact = false;

    /** Resolved config + assets. */
    UPROPERTY(Transient)
    TObjectPtr<UGrassFootstepFeedbackConfig> ResolvedConfig;

    UPROPERTY(Transient)
    TObjectPtr<UNiagaraSystem> PuffSystemAsset;

    UPROPERTY(Transient)
    TObjectPtr<UMaterialInterface> DecalMaterialAsset;

    /** Trail pool. Fixed size, built lazily on the first accepted footstep. */
    UPROPERTY(Transient)
    TArray<FGrassFootstepDecalSlot> DecalSlots;

    /** Live puffs. Reused slots; the array never grows past MaxPuffRecords. Holds only weak
     *  pointers to pooled Niagara components, so it needs no reflection. */
    TArray<FPuffRecord> PuffRecords;

    /** Delegate handle, so EndPlay can unsubscribe without touching the static delegate globally. */
    FDelegateHandle FootstepHandle;

    /** Set once assets have been resolved, so a world without the content logs exactly once. */
    bool bMissingAssetsLogged = false;
    bool bSubscribed = false;
};