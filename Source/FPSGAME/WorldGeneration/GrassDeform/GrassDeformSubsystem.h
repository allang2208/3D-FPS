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
class UGrassDeformSettings;

/** GPU grass presentation for one Game/PIE world (no replication or dedicated-server work).
 * Mask peak/direction: RGBA16F A/B; last contact: R32F A/B. Both pairs are persistent
 * assets bound by the material function; ReadIsB promotes them together after two draws.
 * Continuous body contact uses two changed-only MPC vectors. Persistent contacts write
 * at 10 Hz; recovery is evaluated per frame in the material, without a fade render pass.
 * No per-blade loops, traces, instance transforms or runtime GPU readback.
 * Enabled only when r.GrassDeform, foliage quality, user gate and all v12 assets agree.
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

    /** Footstep direction is shared with body contact instead of making radial rosettes. */
    void StampDirectionalTrample(FVector WorldPos, float Radius, float Strength, FVector TravelDirection);

    /**
     * One-shot radial impact: persistent flatten plus the most recent wavefront in the MPC.
     * RT RGB stores flatten and radial bend direction; Alpha is not used.
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
        // Keep world coordinates until the queue is drained, after the window follows the player.
        FVector2D CenterXY = FVector2D::ZeroVector;
        FVector2D StartXY = FVector2D::ZeroVector;
        float Radius = 0.f;
        float Strength = 0.f;
        float WaveSpeed = 0.f;
        float Timestamp = 0.f;
        bool bImpulse = false;
        bool bSweep = false;
        FVector2D Direction = FVector2D(1.f, 0.f);
        float CoreFraction = 0.f;
        float PressDistance = 0.f;
        float DirectionBias = 0.f;
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
    /** CPU-only lifetime bookkeeping; shader evaluates recovery continuously. */
    void UpdateFade(float DeltaTime);
    /** Read / write sides of the ping-pong pair. A pass never samples the target it writes. */
    UTextureRenderTarget2D* GetReadTarget() const;
    UTextureRenderTarget2D* GetWriteTarget() const;
    /** Swap the ping-pong sides and mark the ReadIsB scalar for republication. */
    void FlipReadSide();
    /** Continuous body field and 10 Hz retained contacts. Projection maths only. */
    void UpdateTrampleSource(float DeltaTime);
    /** Publish time plus changed-only body vectors and configuration/window parameters. */
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
    // GrassDeformAudit (development only). Self-driven -game fixture for Backlog G1: it stages
    // Status / Stamp / DumpRT / screenshots / a simulated walk against a live world and writes
    // Saved/GrassDeform/audit_report.txt, so "the grass does not react" can be bisected (mask
    // empty = pass side; mask present but pixels unchanged = material side) without a human at
    // the keyboard. Launched with: UnrealEditor.exe FPSGAME.uproject <map> -game -GrassDeformAudit.
    // ---------------------------------------------------------------------------------------
#if !UE_BUILD_SHIPPING
    void RunGrassResponseAudit(float DeltaTime);
    void RunGrassFunctionalAudit(float DeltaTime);
    void RunGrassDeformAudit(float DeltaTime);
    /** Blocking readback of one side of the RT pair (8-bit quantised; the mask is 0..1 so this is
     *  exact enough for presence/extent checks). */
    static bool AuditReadRenderTarget(UTextureRenderTarget2D* RT, TArray<FColor>& OutPixels);
    void AuditLogRenderTargetStats(const TCHAR* Side, UTextureRenderTarget2D* RT, int64& OutMaskedTexels);

    int32 AuditStage = -2;        // -2 = flag not evaluated yet, -1 = armed, then 0..N stages
    double AuditNextAction = 0.0;
    FVector AuditTarget = FVector::ZeroVector;
    FVector AuditWalkDir = FVector::ZeroVector;
    int32 AuditWalkTicks = 0;
    int32 AuditFindRetries = 0;
    int32 AuditPngCounter = 0;
    int64 AuditMaskedTexelsBeforeWalk = 0;
#endif

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
    /** Actual game time since the previous fade, independent of stamp arrivals and frame rate. */
    float FadeElapsed = 0.f;

    /** Conservative flag for unexpired contacts; no fade pass is scheduled. */
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
    /** World XY of the last impulse origin handed to the MPC (invalid until the first impulse). */
    FLinearColor LastPublishedWaveOrigin = FLinearColor(TNumericLimits<float>::Max(), TNumericLimits<float>::Max(), 0.f, 0.f);
    int32 LastPublishedEnabled = -1;
    /** Read side (0 = RT_GrassDeformA, 1 = RT_GrassDeformB) last published to the MPC. */
    int32 LastPublishedReadIsB = -1;

    /** World time of the last publish, used to keep WorldTime monotonic across pauses. */
    double PublishedWorldTime = -1.0;

    /** The debug console commands (DumpRT / Status) read internal state, so they are friends. */
    friend class FGrassDeformConsoleCommands;

    // v12: mask peak/direction and R32F last-contact time always swap as one pair.
    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> ContactTimeTargets[2];
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> StampTimeMaterialAsset;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> RecenterTimeMaterialAsset;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> StampTimeMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RecenterTimeMaterial;
    const UGrassDeformSettings* Response = nullptr; // Engine-rooted CDO, stable for the world lifetime.
    FVector2D BodyDirection = FVector2D(1.f, 0.f);
    FVector2D PreviousBodyPosition = FVector2D::ZeroVector;
    FLinearColor BodyContact = FLinearColor::Black;
    FLinearColor BodyMotion = FLinearColor(1.f, 0.f, 0.f, 0.f);
    FLinearColor PublishedBodyContact = FLinearColor(-1.f, -1.f, -1.f, -1.f);
    FLinearColor PublishedBodyMotion = FLinearColor(-1.f, -1.f, -1.f, -1.f);
    float BodyContactAge = 0.f;
    bool bBodyGrounded = false;
    bool bResponsePublished = false;
};
