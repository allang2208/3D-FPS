#pragma once

#include "CoreMinimal.h"
#include "HAL/IConsoleManager.h"
#include "Subsystems/WorldSubsystem.h"
#include "UObject/SoftObjectPath.h"
#include "GrassDeformTuning.h"
#include "GrassDeformSubsystem.generated.h"

class ACharacter;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UMaterialParameterCollection;
class UMaterialParameterCollectionInstance;
class UTextureRenderTarget2D;

/**
 * GPU grass interaction state for one world (M1: trample / flatten, plan section 3.1).
 *
 * All interaction state lives in one ping-pong pair of persistent RGBA16F render target ASSETS
 * (RT_GrassDeformA/B) forming a window centred on the player. The grass materials sample them
 * through texture-parameter defaults wired into MF_GrassDeform; MPC_GrassDeform carries the
 * window contract plus the ReadIsB scalar that picks the current read side. Nothing is stored per
 * actor, per foliage instance or per World Partition cell, so the system keeps working with Nanite
 * foliage and streaming levels.
 *
 * Cost contract (plan section 7):
 *   - one DrawMaterial per stamp event,
 *   - one MPC scalar write per frame (WorldTime),
 *   - a throttled, dirty-only fade pass,
 *   - a 10 Hz trample check that uses capsule projection maths only and never traces.
 *
 * The subsystem disables itself gracefully when the three pass materials or the MPC are not in
 * the content yet (they are authored by Tools/GrassDeform/setup_assets_m1.py), logging once.
 *
 * Enable contract (three independent gates, all must agree):
 *   enabled = r.GrassDeform != 0 && sg.FoliageQuality > 0 && assets resolved.
 * The scalability group is consumed through a console variable sink, so a quality change is
 * handled the moment the engine flushes its sinks instead of one tick later; the sink only
 * latches a value and does no work of its own (M4, plan section 9).
 *
 * Single-player presentation only: no replication, no authority checks. A dedicated server skips
 * the whole subsystem.
 */
UCLASS()
class FPSGAME_API UGrassDeformSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()

public:
    //~ Begin USubsystem
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    //~ End USubsystem

    //~ Begin FTickableGameObject
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual bool IsTickable() const override { return bTickEnabled; }
    //~ End FTickableGameObject

    /**
     * Persistent flatten from a footfall or a standing body.
     * WorldPos is any world-space point in the footprint; only XY is used.
     * Strength is clamped to 0..1 and drives channel R.
     */
    UFUNCTION(BlueprintCallable, Category = "Grass Deform")
    void StampTrample(FVector WorldPos, float Radius, float Strength);

    /**
     * One-shot radial impact: the persistent flatten of StampTrample plus a wavefront stored in
     * channel A that the shader sweeps outward at WaveSpeed.
     */
    UFUNCTION(BlueprintCallable, Category = "Grass Deform")
    void AddImpulse(FVector WorldPos, float Radius, float Strength, float WaveSpeed);

    /** Master switch. Turning it off stops all passes and publishes bEnabled=0 to the MPC. */
    UFUNCTION(BlueprintCallable, Category = "Grass Deform")
    void SetEnabled(bool bInEnabled);

    /** True when the subsystem is actually driving passes: r.GrassDeform is on, sg.FoliageQuality
     *  is above 0 and the assets resolved. */
    UFUNCTION(BlueprintPure, Category = "Grass Deform")
    bool IsEnabled() const;

protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;

private:
    /** A finished interaction request, queued by the public API and drained in Tick.
     *  Fixed size, so no allocation happens on the event path. */
    struct FPendingStamp
    {
        FVector2D CenterXY = FVector2D::ZeroVector;
        float Radius = 0.f;
        float Strength = 0.f;
        float WaveSpeed = 0.f;
        float Timestamp = 0.f;
        bool bImpulse = false;
    };

    /** Player trample accumulator (10 Hz). */
    struct FTrampleTracker
    {
        TWeakObjectPtr<ACharacter> Character;
        FVector2D LastProjection = FVector2D::ZeroVector;
        bool bHasProjection = false;
        bool bInitialized = false;
    };

    /** Resolve the soft assets once. Sets bAssetsReady and logs once when something is missing. */
    void ResolveAssets();
    /** Bind the persistent RT asset pair (RT_GrassDeformA/B), clear them and reset window state. */
    void RecreateRenderTargets();
    /** Unbind the RT pointers. The RT assets and the pass MIDs stay alive (see the .cpp). */
    void ReleaseRenderTargets();

    /** Queue one event. Returns false (and drops) when the subsystem is not usable. */
    bool EnqueueStamp(const FVector& WorldPos, float Radius, float Strength, float WaveSpeed, bool bImpulse);

    /** Move the window to the requested centre when the 4 m snap cell changed. */
    void RecenterWindow(const FVector& GroundPosition);
    /** Flush everything queued since the last tick into the current read RT. */
    void DrainPendingStamps();
    /** Throttled, dirty-only regrowth pass. */
    void UpdateFade(float DeltaTime);
    /** Read / write sides of the ping-pong pair. A pass never samples the target it writes. */
    UTextureRenderTarget2D* GetReadTarget() const;
    UTextureRenderTarget2D* GetWriteTarget() const;
    /** Swap the ping-pong sides and mark the ReadIsB scalar for republication. */
    void FlipReadSide();
    /** 10 Hz player trample source. Pure projection maths, no traces. */
    void UpdateTrampleSource(float DeltaTime);
    /** Publish the MPC parameters the grass materials read. One scalar per frame from here. */
    void PublishParameters();
    /** True when any pass still needs to run (flatten present or a wavefront is young). */
    bool HasLiveContent() const;

    // ---------------------------------------------------------------------------------------
    // Scalability gating (M4). sg.FoliageQuality level 0 (Low) hides the foliage system, so the
    // deform is forced off and behaves exactly like r.GrassDeform 0: no pass runs and bEnabled=0
    // is published. Level 1 and above restore the cvar-driven state.
    // ---------------------------------------------------------------------------------------

    /** Current sg.FoliageQuality, latched by the console variable sink. A plain int read. */
    int32 GetFoliageQualityLevel() const { return FoliageQualityLevel; }
    /** True when the foliage scalability group allows the deform (level > 0). */
    bool IsFoliageQualityAllowed() const { return FoliageQualityLevel > GrassDeformTuning::DisabledFoliageQualityLevel; }
    /** Read sg.FoliageQuality once. The variable is looked up read-only (the engine owns it), so
     *  this is called from Init / Tick / the sink and never registers a cvar of its own. */
    void RefreshFoliageQualityLevel();
    /** Console variable sink body: latch the level and drop the interaction state on Low. */
    void HandleScalabilityChanged();
    /** Register the sink. Called from Tick, because Initialize runs while the console manager is
     *  still being set up in some world bootstraps. Allocation-free and once per world. */
    void RegisterScalabilitySink();
    /** Drop everything queued or pending so a disabled system leaves no stale mask behind. */
    void DiscardInteractionState();

    /** CPU-side dirty flags. The RT is never read back, so this is the only source of truth. */
    void MarkDirty();

    UMaterialInstanceDynamic* GetPassMaterial(bool bImpulse) const;

    // ---------------------------------------------------------------------------------------
    // Assets. Soft paths only: nothing is loaded during module startup, and a missing asset
    // leaves the subsystem inert instead of failing the world.
    // ---------------------------------------------------------------------------------------

    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> StampMaterialAsset;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> FadeMaterialAsset;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> RecenterMaterialAsset;
    UPROPERTY(Transient) TObjectPtr<UMaterialParameterCollection> CollectionAsset;

    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> StampMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FadeMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RecenterMaterial;

    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> RenderTargets[2];

    /** Persistent RT asset pair (RT_GrassDeformA/B). The grass shader samples these through
     *  TextureObjectParameter defaults wired into MF_GrassDeform; the subsystem only draws into
     *  them and publishes which side is the read side (MPC scalar ReadIsB). */
    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> RenderTargetAssets[2];
    /** One-shot warning that r.GrassDeform.RTSize is retired (the assets define the size). */
    bool bRTSizeWarningLogged = false;

    // ---------------------------------------------------------------------------------------
    // Runtime state
    // ---------------------------------------------------------------------------------------

    /** Read side of the ping-pong pair: the RT the shaders sample and the next pass writes into. */
    int32 ReadIndex = 0;

    /** Centre of the world window (XY), snapped to SnapGridCm. */
    FVector2D WindowCenter = FVector2D::ZeroVector;
    bool bWindowInitialized = false;

    /** RT edge requested when the pair was created; a cvar change triggers a rebuild. */
    int32 ActiveRTSize = 0;

    FTrampleTracker Trample;
    float TrampleClock = 0.f;

    /** Seconds until the fade pass may run again. */
    float FadeCooldown = 0.f;

    /** Dirty flag: a stamp landed, so the regrowth pass must run. */
    bool bDirty = false;
    /** Conservative regrowth timer: the fade pass idles once this reaches zero. The RT is never
     *  read back, so this is the only way the CPU learns that the mask has fully decayed. */
    float FadeSecondsRemaining = 0.f;
    /** Set whenever the read side changes, so the ReadIsB scalar is published once per flip. */
    bool bReadSideDirty = true;

    /** Queue drained at the start of the next tick. */
    TArray<FPendingStamp> Pending;
    static constexpr int32 MaxPendingStamps = 64;

    /** Asset resolution and enable state. */
    bool bAssetsReady = false;
    bool bMissingAssetsLogged = false;
    bool bUserEnabled = true;
    bool bTickEnabled = false;

    /** Latched output of r.GrassDeform at the last tick, so the cvar change is seen exactly once. */
    int32 LastCvarEnabled = 1;
    /** Latched output of sg.FoliageQuality. Written by the console variable sink (game thread) and by
     *  Tick, read by IsEnabled. Starts at -1 so the first latch always registers as a change; both
     *  write paths run during Initialize, so no world ever sees the sentinel. */
    int32 FoliageQualityLevel = -1;
    /** Handle of the console variable sink, valid only while bScalabilitySinkRegistered is true -
     *  that flag is what keeps the default-constructed handle from ever being unregistered. */
    FConsoleVariableSinkHandle ScalabilitySinkHandle;
    bool bScalabilitySinkRegistered = false;

    // ---------------------------------------------------------------------------------------
    // Published-parameter cache. Every one of these is compared before writing, because each
    // MPC/material setter dirties a uniform buffer even when the value did not change.
    // ---------------------------------------------------------------------------------------

    /** Centre of the world window last published to the MPC, so an unmoved window writes nothing. */
    FVector2D LastPublishedCenter = FVector2D(TNumericLimits<float>::Max(), TNumericLimits<float>::Max());
    float LastPublishedWindowSize = -1.f;
    float LastPublishedRegrowth = -1.f;
    float LastPublishedWaveSpeed = -1.f;
    /** Window UV of the last impulse origin handed to the MPC (invalid until the first impulse). */
    FLinearColor LastPublishedWaveOrigin = FLinearColor(TNumericLimits<float>::Max(), TNumericLimits<float>::Max(), 0.f, 0.f);
    int32 LastPublishedEnabled = -1;
    /** Read side (0 = RT_GrassDeformA, 1 = RT_GrassDeformB) last published to the MPC. */
    int32 LastPublishedReadIsB = -1;

    /** World time of the last publish, used to keep WorldTime monotonic across pauses. */
    double PublishedWorldTime = -1.0;

    /** The debug console commands (DumpRT / Status) read internal state, so they are friends. */
    friend class FGrassDeformConsoleCommands;
};