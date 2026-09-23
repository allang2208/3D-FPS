#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Containers/Ticker.h"
#include "FPSPerformanceMetrics.generated.h"

class UActorComponent;
class APlayerController;
class UGameViewportClient;
class ULightComponent;
class FSlateWindowElementList;
struct FConvexVolume;

/** Valid observations only. Percentile = sorted[ceil(p * n) - 1]; empty means unknown. */
struct FFPSMetricDistribution
{
    int32 Count = 0;
    float Average = 0.f;
    float P50 = 0.f;
    float P95 = 0.f;
    float P99 = 0.f;
    float Peak = 0.f;
};

/** Source geometry, never submitted geometry or measured component time. */
USTRUCT()
struct FFPSComponentCost
{
    GENERATED_BODY()
    UPROPERTY() TWeakObjectPtr<AActor> Owner;
    UPROPERTY() TWeakObjectPtr<UActorComponent> Component;
    UPROPERTY() FString Label;
    UPROPERTY() FString ObjectPath;
    UPROPERTY() FString ClassName;
    UPROPERTY() FString Kind;
    UPROPERTY() FString Detail;
    UPROPERTY() TArray<int64> LODTriangles;
    UPROPERTY() int64 Triangles = 0;
    UPROPERTY() int64 Vertices = 0;
    UPROPERTY() int32 MaterialSlots = 0;
    UPROPERTY() int32 Instances = 1;
    // Component configuration only: 0 = automatic, 1 = LOD0, 2 = LOD1.
    UPROPERTY() int32 ForcedLodModel = -1;
    UPROPERTY() int32 ComponentMinLod = -1;
    UPROPERTY() bool bOverrideMinLod = false;
    UPROPERTY() bool bInstanced = false;
    UPROPERTY() bool bDynamicGeometry = false;
    UPROPERTY() bool bHasNaniteData = false;
    UPROPERTY() bool bHasGeometry = false;
    UPROPERTY() bool bRegistered = false;
    UPROPERTY() bool bVisible = false;
    UPROPERTY() bool bViewVisibilityKnown = false;
    UPROPERTY() bool bVisibleToView = false;
    UPROPERTY() bool bHasFrustum = false;
    UPROPERTY() bool bOnScreen = false;
    UPROPERTY() bool bCastsShadow = false;
    UPROPERTY() bool bHiddenShadowEligible = false;
    UPROPERTY() float DistanceMeters = 0.f;
    UPROPERTY() float Rank = 0.f;
    UPROPERTY() float ShareOfTop = 0.f;
    UPROPERTY() float ShareOfAll = 0.f;
};

struct FFPSMeshAssetSummary
{
    FString Asset;
    int32 Components = 0, ViewEligibleComponents = 0, FrustumCandidates = 0;
    int64 Instances = 0, SourceLod0Triangles = 0;
    double SourceComplexity = 0.0;
};

/** Observation settings at one instant, not assumed constant throughout the window. */
struct FFPSObserverContext
{
    bool bKnown = false, bPanelOpen = false, bFrozen = false;
    int32 Page = -1;
    float RefreshMs = 0.f, BlurStrength = 0.f;
    int32 BlurRadius = 0;
};

/** Instrumented project events, not engine-wide work or render recreates. */
struct FFPSPerformanceActions
{
    uint64 VisibilityFlagChanges = 0;
    uint64 EquipmentRebuilds = 0;
    uint64 OutfitRebuilds = 0;
    uint64 EquipmentCaptures = 0;
    uint64 VisibilityUpdates = 0;
    uint64 WorldVisibilityUpdates = 0;
    FFPSPerformanceActions operator-(const FFPSPerformanceActions& Other) const;
    FFPSPerformanceActions& operator+=(const FFPSPerformanceActions& Other);
};

enum class EFPSIconAction : uint8 { Request, CacheHit, PendingHit, FailedHit, Queued, Completed, Failed, Deferred, Count };

struct FFPSIconActions
{
    uint64 Values[static_cast<int32>(EFPSIconAction::Count)] = {};
    FFPSIconActions operator-(const FFPSIconActions& Other) const;
    FFPSIconActions& operator+=(const FFPSIconActions& Other);
};

/** Values read at one OnEndFrame boundary. Thread/GPU values are independently published. */
struct FFPSRecordedFrame
{
    double Seconds = 0.0, StartSeconds = 0.0;
    uint64 FrameId = 0;
    float FrameMs = 0.f, GameMs = 0.f, DrawMs = 0.f, RhiMs = 0.f, GpuMs = 0.f;
    float GameWaitMs = 0.f, DrawWaitMs = 0.f, GameCriticalMs = 0.f, DrawCriticalMs = 0.f;
    bool bPaused = false, bBackground = false;
    FFPSPerformanceActions Actions;
    FFPSIconActions Icons;
};

/** Completed synchronous game-thread scopes; duration includes nested work and waits. */
struct FFPSPerformanceEvent
{
    uint64 Id = 0, ParentId = 0, StartFrame = 0, EndFrame = 0;
    double StartSeconds = 0.0, EndSeconds = 0.0;
    FName Stage;
    FString Key;
    bool bMarker = false;
    bool bCrossesWindowStart = false, bCrossesWindowEnd = false;
    bool bParentMissing = false;
};

/** Bounded diagnostic history; context includes up to two frames on either side. */
struct FFPSHitchRecord
{
    uint64 PeakFrameId = 0;
    float PeakMs = 0.f;
    TArray<FFPSRecordedFrame> Frames;
    TArray<FFPSPerformanceEvent> Events;
    int32 ActiveScopesAtContextEnd = 0;
    bool bEventsCapacityLimited = false;
};

struct FFPSIconFailure
{
    FString Recipe, Resource, Reason, OccurredAtUtc;
    FName Stage;
    uint64 FrameId = 0;
    double Seconds = 0.0;
    bool bReasonTruncated = false;
};

/** Current subsystem state at snapshot time, not a total over the frame window. */
struct FFPSIconTaskState
{
    bool bAvailable = false;
    int32 Queued = 0, Cached = 0, FailedRecipes = 0, Stage = 0;
    FString Key;
    double ObservedSeconds = 0.0, RequestAgeSeconds = 0.0, AttemptAgeSeconds = 0.0;
    FName WaitReason;
    FString WaitResource;
    double WaitAgeSeconds = 0.0;
    int32 ReadinessPolls = 0, CaptureSubmissions = 0, DeferredAttempts = 0;
    bool bBoundsCacheHit = false;
    bool bMaterialCheckPending = false;
    int32 CoolingDownRecipes = 0;
    double NextEligibleSeconds = 0.0;
    FString ReadbackState;
    double ReadbackAgeSeconds = 0.0;
    double ReadbackCopyMs = -1.0, ReadbackConversionMs = -1.0;
    TArray<FFPSIconFailure> RecentFailures;
    int32 FailureCapacity = 32;
    bool bFailureDetailsLimited = false;
};

USTRUCT()
struct FFPSFrameBudget
{
    GENERATED_BODY()
    FFPSMetricDistribution Frame, Game, Draw, Rhi, Gpu;
    FFPSMetricDistribution GameWait, DrawWait, GameCritical, DrawCritical;
    FFPSMetricDistribution Scan, UiUpdate;
    float LatestFrameMs = 0.f;
    float Fps = 0.f;
    float OverBudgetFraction = 0.f;
    float SlowFrameFraction = 0.f;
    double DurationSeconds = 0.0;
    double LatestSampleSeconds = 0.0;
    double SampleAgeSeconds = 0.0;
    uint64 FirstFrameId = 0;
    uint64 LastFrameId = 0;
    uint64 PeakFrameId = 0;
    int32 PausedFrames = 0;
    int32 BackgroundFrames = 0;
    bool bRecording = true;
    bool bCapacityLimited = false;
};

/** Configuration and eligibility, not actual animation evaluation counts. */
struct FFPSPerformanceCoverage
{
    int32 SkeletalComponents = 0, SkeletalWithAsset = 0, SkeletalTickEnabled = 0;
    int32 SkeletalLeaderFollowers = 0, TotalAssetBones = 0;
    int32 AlwaysRefreshConfigured = 0, AlwaysPoseConfigured = 0, TickEnabledAlwaysRefresh = 0;
    int32 HiddenShadowEligible = 0;
    int32 InstancedComponents = 0;
    int64 Instances = 0;
    int32 DynamicMeshes = 0;
    int32 Lights = 0, VisibleLights = 0, ShadowLights = 0;
    int32 EnabledLights = 0, EnabledShadowLights = 0;
    int32 PointLights = 0, SpotLights = 0, RectLights = 0, DirectionalLights = 0;
    int32 SkyLights = 0, EnabledSkyLights = 0, RealTimeSkyCaptures = 0;
    int32 LightViewCandidates = 0, ShadowViewCandidates = 0, CameraLightBounds = 0;
    int32 AudioComponents = 0, PlayingAudio = 0;
    int32 NiagaraComponents = 0, ActiveNiagara = 0;
    int32 CascadeComponents = 0;
    int64 CascadeParticles = 0;
    int32 OtherPrimitives = 0;
    int32 GeometryUnavailable = 0;
};

/** Snapshot of component state; sphere/frustum candidates are not renderer visibility or GPU cost. */
struct FFPSLightObservation
{
    FString ObjectPath, Label, Type, Mobility, Module, Role, IntensityUnits;
    FVector Position = FVector::ZeroVector;
    float Intensity = 0.f, RadiusCm = 0.f, DistanceCm = 0.f;
    float MaxDrawDistanceCm = 0.f, EffectiveMaxDrawDistanceCm = 0.f, FadeRangeCm = 0.f;
    float OuterConeDegrees = 0.f, VolumetricScattering = 0.f;
    int32 RayTracedShadowMode = 0;
    bool bLocal = false, bRegistered = false, bVisibleFlag = false, bAffectsWorld = false;
    bool bEnabled = false, bPositiveBrightness = false, bCastShadows = false, bCastVolumetricShadow = false;
    bool bWithinDrawDistance = false, bFrustumCandidate = false, bViewCandidate = false;
    bool bCameraInsideBounds = false;
};

struct FFPSSkyLightObservation
{
    FString ObjectPath, Source;
    float Intensity = 0.f;
    bool bEnabled = false, bRealTimeCapture = false, bCastsShadows = false;
};

USTRUCT()
struct FFPSPerformanceSnapshot
{
    GENERATED_BODY()
    UPROPERTY() FFPSFrameBudget Budget;
    UPROPERTY() TArray<FFPSComponentCost> Costs;
    TArray<FFPSMeshAssetSummary> MeshAssets;
    FFPSObserverContext ObserverAtSnapshot, ObserverAtExport;
    FFPSPerformanceActions Actions;
    FFPSPerformanceCoverage Coverage;
    TArray<FFPSLightObservation> Lights;
    TArray<FFPSSkyLightObservation> SkyLights;
    TMap<FString,FString> LightingCVars;
    TArray<FString> DungeonGenerationReports;
    TArray<FFPSRecordedFrame> Frames;
    TArray<FFPSPerformanceEvent> Events;
    TArray<FFPSRecordedFrame> SlowestFrames;
    TArray<FFPSHitchRecord> RecentHitches;
    TArray<FFPSHitchRecord> WorstHitches;
    int32 OverBudgetFrames = 0, SlowFrames = 0, FramesAtLeast50Ms = 0, FramesAtLeast100Ms = 0;
    int32 HitchHistoryCapacity = 16;
    int32 WorstHitchCapacity = 4, HitchEventCapacity = 128;
    uint64 HitchesOverwritten = 0;
    FFPSIconActions IconActions;
    FFPSIconTaskState IconTask;
    FString SessionId;
    uint64 CaptureGeneration = 0, EventsOverwritten = 0;
    int32 EventsDiscardedAtBoundary = 0, ActiveEventCount = 0;
    bool bEventsCapacityLimited = false;
    double WindowStartSeconds = 0.0, SnapshotSeconds = 0.0;
    FString ExportRequestedAtUtc;
    uint64 ExportSubmittedFrame = 0;
    FString Environment;
    FString CapturedAtUtc;
    bool bHasView = false;
    bool bHasProjection = false;
    int32 ActorCount = 0, ComponentCount = 0, RankedMeshCount = 0;
    double AllRankTotal = 0.0, DisplayedRankTotal = 0.0;
    float ScanMs = 0.f;
    float TargetFps = 60.f;
    float SlowFrameThresholdMs = 33.34f;
    float RequestedWindowSeconds = 10.f;
    float HitchThresholdMs = 50.f;
};

/** Engine-frame sampling is independent of the UI; scene scans are on demand.
 * Thread/GPU observations are process-wide and asynchronously published;
 * project event counters and resource scans are per World. */
UCLASS()
class FPSGAME_API UFPSPerformanceMetricsSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;

    FFPSPerformanceSnapshot BuildSnapshot(int32 MaxEntries, APlayerController* Viewer = nullptr);
    void ClearSamples();
    void SetRecording(bool bEnabled);
    bool IsRecording() const { return bRecording; }
    void RecordUiUpdate(float Milliseconds);
    static bool ExportSnapshot(const FFPSPerformanceSnapshot& Snapshot, FString& OutPath);
    /** Copies only captured values; completion is delivered on the game thread. */
    static void ExportSnapshotAsync(const FFPSPerformanceSnapshot& Snapshot,
        TFunction<void(bool, const FString&, double)> Completion);
    static void CountIconAction(const UObject* Context, EFPSIconAction Action);
    static void RecordMarker(const UObject* Context, FName Stage, const FString& Detail = FString());

    static void CountVisibilityFlagChange(const UObject* Context, int32 ChangedFields = 1);
    static void CountEquipmentRebuild(const UObject* Context);
    static void CountOutfitRebuild(const UObject* Context);
    static void CountEquipmentCapture(const UObject* Context);
    static void CountVisibilityUpdate(const UObject* Context);
    static void CountWorldVisibilityUpdate(const UObject* Context);

    float TargetFps = 60.f;
    float SlowFrameThresholdMs = 33.34f;
    float WindowSeconds = 10.f;
    float HitchThresholdMs = 50.f;

private:
    friend class FFPSPerformanceScope;
    using FFrameSample = FFPSRecordedFrame;
    struct FObserverSample { double Seconds; float Milliseconds; };
    static UFPSPerformanceMetricsSubsystem* Find(const UObject* Context);
    void SampleEngineFrame();
    void ReadWindow(FFPSPerformanceSnapshot& Snapshot, double Now) const;
    uint64 BeginEvent(FName Stage, const FString& Key);
    void EndEvent(uint64 EventId, uint64 Generation);
    void AppendEvent(FFPSPerformanceEvent Event);
    void ReadEvents(FFPSPerformanceSnapshot& Snapshot) const;
    void ReadEventsInRange(double Start, double End, TArray<FFPSPerformanceEvent>& Out, bool& bLimited) const;
    void UpdateHitchHistory(const FFrameSample& Sample);
    void UpdateHitchEvents(const FFPSPerformanceEvent& Event);
    void BeginWorldTick(UWorld* World, ELevelTick TickType, float DeltaSeconds);
    void EndWorldTick(UWorld* World, ELevelTick TickType, float DeltaSeconds);
    void BindPhaseDelegates();
    void UnbindPhaseDelegates();
    void BindGameViewport();
    void BeginViewportDraw();
    void EndViewportDraw();
    void BeginSlateWidgets(float DeltaSeconds);
    void EndSlateWidgets(float DeltaSeconds);
    void BeginWindowPaint(const FSlateWindowElementList& Elements);
    void EndWindowPaint(const FSlateWindowElementList& Elements);
    void BeginGarbageCollection();
    void EndGarbageCollection();
    void MarkSyncLoad(const FString& Package);
    void MarkAsyncLoadingFlush();
    bool MarkCoreTicker(float DeltaSeconds);
    void InvalidateActiveEvents();
    void ScanComponent(UActorComponent* Component, const FVector& ViewLocation,
        const AActor* ViewActor, const FConvexVolume* Frustum, FFPSComponentCost& Out) const;
    void ScanLight(const ULightComponent* Light, const FVector& ViewLocation,
        const FConvexVolume* Frustum, FFPSPerformanceSnapshot& Snapshot) const;
    static void AddObserverSample(TArray<FObserverSample>& Samples, float Milliseconds, double Now);
    static FFPSMetricDistribution ObserverStats(const TArray<FObserverSample>& Samples, double Since);

    FDelegateHandle EndFrameHandle;
    FDelegateHandle WorldTickStartHandle, WorldTickEndHandle;
    FDelegateHandle SlatePreHandle, SlatePostHandle, ViewportBeginHandle, ViewportEndHandle;
    FDelegateHandle WindowBeginHandle, WindowEndHandle, GcBeginHandle, GcEndHandle, SyncLoadHandle, AsyncFlushHandle;
    FTSTicker::FDelegateHandle CoreTickerHandle;
    TWeakObjectPtr<UGameViewportClient> ObservedViewport;
    uint64 ViewportEventId = 0, ViewportEventEpoch = 0;
    TArray<TPair<uint64, uint64>> SlateEventStack;
    TArray<TPair<uint64, uint64>> WindowEventStack;
    uint64 GcEventId = 0, GcEventEpoch = 0;
    uint64 WorldTickEventId = 0, WorldTickEventEpoch = 0;
    TArray<FFrameSample> FrameSamples;
    TArray<FObserverSample> ScanSamples, UiSamples;
    FFPSPerformanceActions TotalActions, PreviousActions;
    FFPSIconActions TotalIconActions, PreviousIconActions;
    TArray<FFPSPerformanceEvent> CompletedEvents, ActiveEvents;
    TArray<FFPSHitchRecord> RecentHitches;
    TArray<FFPSHitchRecord> WorstHitches;
    uint64 HitchesOverwritten = 0;
    FString SessionId;
    uint64 CaptureGeneration = 1, EventEpoch = 1, NextEventId = 0, EventsOverwritten = 0;
    double LastOverwrittenEventEnd = 0.0;
    int32 EventWriteIndex = 0, EventCount = 0, EventsDiscardedAtBoundary = 0;
    int32 WriteIndex = 0, SampleCount = 0;
    double PreviousFrameSeconds = 0.0;
    uint64 LastObservedFrame = MAX_uint64;
    bool bRecording = true;
    static constexpr int32 MaxSamples = 8192;
    static constexpr int32 MaxEvents = 8192;
    static constexpr int32 MaxHitches = 16;
    static constexpr int32 MaxWorstHitches = 4;
    static constexpr int32 MaxHitchEvents = 128;
};

/** Pass the owning GameInstance for preview work; never pass a preview-world actor. */
class FPSGAME_API FFPSPerformanceScope
{
public:
    FFPSPerformanceScope(const UObject* Context, FName Stage, const FString& Key = FString());
    ~FFPSPerformanceScope();
    void Finish();
    FFPSPerformanceScope(const FFPSPerformanceScope&) = delete;
    FFPSPerformanceScope& operator=(const FFPSPerformanceScope&) = delete;
private:
    TWeakObjectPtr<UFPSPerformanceMetricsSubsystem> Metrics;
    uint64 EventId = 0, Generation = 0;
};
