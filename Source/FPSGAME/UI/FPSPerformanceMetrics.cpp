#include "FPSPerformanceMetrics.h"

#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Framework/Application/SlateApplication.h"
#include "Misc/CoreDelegates.h"
#include "RenderTimer.h"
#include "DynamicRHI.h"
#include "Misc/Guid.h"

namespace FPSPerformance
{
FFPSMetricDistribution Distribution(TArray<float> Values)
{
    FFPSMetricDistribution Result;
    Values.RemoveAll([](float Value) { return !FMath::IsFinite(Value) || Value < 0.f; });
    if (Values.IsEmpty()) return Result;
    Values.Sort();
    Result.Count = Values.Num();
    double Sum = 0.0;
    for (float Value : Values) Sum += Value;
    Result.Average = static_cast<float>(Sum / Values.Num());
    const auto Percentile = [&Values](float P)
    {
        return Values[FMath::Clamp(FMath::CeilToInt(P * Values.Num()) - 1, 0, Values.Num() - 1)];
    };
    Result.P50 = Percentile(.5f);
    Result.P95 = Percentile(.95f);
    Result.P99 = Percentile(.99f);
    Result.Peak = Values.Last();
    return Result;
}
float Milliseconds(uint32 Cycles) { return static_cast<float>(FPlatformTime::ToMilliseconds(Cycles)); }
}

FFPSPerformanceActions FFPSPerformanceActions::operator-(const FFPSPerformanceActions& Other) const
{
    return {VisibilityFlagChanges - Other.VisibilityFlagChanges, EquipmentRebuilds - Other.EquipmentRebuilds,
        OutfitRebuilds - Other.OutfitRebuilds, EquipmentCaptures - Other.EquipmentCaptures,
        VisibilityUpdates - Other.VisibilityUpdates, WorldVisibilityUpdates - Other.WorldVisibilityUpdates};
}

FFPSPerformanceActions& FFPSPerformanceActions::operator+=(const FFPSPerformanceActions& Other)
{
    VisibilityFlagChanges += Other.VisibilityFlagChanges;
    EquipmentRebuilds += Other.EquipmentRebuilds;
    OutfitRebuilds += Other.OutfitRebuilds;
    EquipmentCaptures += Other.EquipmentCaptures;
    VisibilityUpdates += Other.VisibilityUpdates;
    WorldVisibilityUpdates += Other.WorldVisibilityUpdates;
    return *this;
}

bool UFPSPerformanceMetricsSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
    return Type == EWorldType::Game || Type == EWorldType::PIE;
}

void UFPSPerformanceMetricsSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    FrameSamples.SetNum(MaxSamples);
    CompletedEvents.SetNum(MaxEvents);
    ActiveEvents.Reserve(16);
    RecentHitches.Reserve(MaxHitches);
    WorstHitches.Reserve(MaxWorstHitches);
    SessionId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
    EndFrameHandle = FCoreDelegates::OnEndFrame.AddUObject(this, &ThisClass::SampleEngineFrame);
    WorldTickStartHandle = FWorldDelegates::OnWorldTickStart.AddUObject(this, &ThisClass::BeginWorldTick);
    WorldTickEndHandle = FWorldDelegates::OnWorldTickEnd.AddUObject(this, &ThisClass::EndWorldTick);
    BindPhaseDelegates();
}

void UFPSPerformanceMetricsSubsystem::Deinitialize()
{
    FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
    FWorldDelegates::OnWorldTickStart.Remove(WorldTickStartHandle);
    FWorldDelegates::OnWorldTickEnd.Remove(WorldTickEndHandle);
    UnbindPhaseDelegates();
    bRecording = false;
    InvalidateActiveEvents();
    CompletedEvents.Empty();
    FrameSamples.Empty();
    ScanSamples.Empty();
    UiSamples.Empty();
    RecentHitches.Empty();
    WorstHitches.Empty();
    Super::Deinitialize();
}

void UFPSPerformanceMetricsSubsystem::ClearSamples()
{
    ++CaptureGeneration;
    EventsDiscardedAtBoundary = 0;
    InvalidateActiveEvents();
    EventCount = EventWriteIndex = 0;
    EventsOverwritten = 0;
    LastOverwrittenEventEnd = 0.0;
    RecentHitches.Reset();
    WorstHitches.Reset();
    HitchesOverwritten = 0;
    WorldTickEventId = 0;
    SampleCount = 0;
    WriteIndex = 0;
    PreviousFrameSeconds = 0.0;
    PreviousActions = TotalActions;
    PreviousIconActions = TotalIconActions;
    ScanSamples.Reset();
    UiSamples.Reset();
}

void UFPSPerformanceMetricsSubsystem::SetRecording(bool bEnabled)
{
    if (bRecording == bEnabled) return;
    bRecording = bEnabled;
    PreviousFrameSeconds = 0.0;
    PreviousActions = TotalActions;
    PreviousIconActions = TotalIconActions;
    if (bEnabled) ClearSamples();
    else InvalidateActiveEvents();
}

void UFPSPerformanceMetricsSubsystem::SampleEngineFrame()
{
    UWorld* World = GetWorld();
    if (!bRecording || !World || !World->HasBegunPlay())
    {
        PreviousFrameSeconds = 0.0;
        PreviousActions = TotalActions;
        PreviousIconActions = TotalIconActions;
        return;
    }
    if (LastObservedFrame == GFrameCounter) return;
    LastObservedFrame = GFrameCounter;
    const double Now = FPlatformTime::Seconds();
    if (PreviousFrameSeconds <= 0.0)
    {
        PreviousFrameSeconds = Now;
        PreviousActions = TotalActions;
        PreviousIconActions = TotalIconActions;
        return;
    }
    const double FrameStart = PreviousFrameSeconds;
    const double Elapsed = Now - FrameStart;
    PreviousFrameSeconds = Now;
    if (!FMath::IsFinite(Elapsed) || Elapsed <= 0.0) return;

    FFrameSample& Sample = FrameSamples[WriteIndex];
    Sample.Seconds = Now;
    Sample.StartSeconds = FrameStart;
    Sample.FrameId = GFrameCounter;
    // Wall-clock interval at one engine boundary. Never use Slate/world delta or cap hitches.
    Sample.FrameMs = static_cast<float>(Elapsed * 1000.0);
    Sample.GameMs = FPSPerformance::Milliseconds(GGameThreadTime);
    Sample.DrawMs = FPSPerformance::Milliseconds(GRenderThreadTime);
    Sample.RhiMs = FPSPerformance::Milliseconds(GRHIThreadTime);
    Sample.GpuMs = FPSPerformance::Milliseconds(RHIGetGPUFrameCycles(0));
    Sample.GameWaitMs = FPSPerformance::Milliseconds(GGameThreadWaitTime);
    Sample.DrawWaitMs = FPSPerformance::Milliseconds(GRenderThreadWaitTime);
    Sample.GameCriticalMs = FPSPerformance::Milliseconds(GGameThreadTimeCriticalPath);
    Sample.DrawCriticalMs = FPSPerformance::Milliseconds(GRenderThreadTimeCriticalPath);
    Sample.bPaused = World->IsPaused();
    Sample.bBackground = FSlateApplication::IsInitialized() && !FSlateApplication::Get().IsActive();
    Sample.Actions = TotalActions - PreviousActions;
    Sample.Icons = TotalIconActions - PreviousIconActions;
    PreviousActions = TotalActions;
    PreviousIconActions = TotalIconActions;
    WriteIndex = (WriteIndex + 1) % MaxSamples;
    SampleCount = FMath::Min(SampleCount + 1, MaxSamples);
    UpdateHitchHistory(Sample);
    const double Cutoff = Now - FMath::Max(.1f, WindowSeconds);
    // Keep the frame crossing the window boundary, including an arbitrarily long hitch.
    while (SampleCount > 1)
    {
        const int32 First = (WriteIndex - SampleCount + MaxSamples) % MaxSamples;
        if (FrameSamples[First].Seconds > Cutoff) break;
        --SampleCount;
    }
}

UFPSPerformanceMetricsSubsystem* UFPSPerformanceMetricsSubsystem::Find(const UObject* Context)
{
    if (!Context || !IsInGameThread()) return nullptr;
    UWorld* World = Context->GetWorld();
    return World ? World->GetSubsystem<UFPSPerformanceMetricsSubsystem>() : nullptr;
}

void UFPSPerformanceMetricsSubsystem::CountVisibilityFlagChange(const UObject* Context, int32 ChangedFields)
{
    if (auto* Metrics = Find(Context))
        Metrics->TotalActions.VisibilityFlagChanges += FMath::Max(ChangedFields, 0);
}
void UFPSPerformanceMetricsSubsystem::CountEquipmentRebuild(const UObject* Context)
{
    if (auto* Metrics = Find(Context)) ++Metrics->TotalActions.EquipmentRebuilds;
}
void UFPSPerformanceMetricsSubsystem::CountOutfitRebuild(const UObject* Context)
{
    if (auto* Metrics = Find(Context)) ++Metrics->TotalActions.OutfitRebuilds;
}
void UFPSPerformanceMetricsSubsystem::CountEquipmentCapture(const UObject* Context)
{
    if (auto* Metrics = Find(Context)) ++Metrics->TotalActions.EquipmentCaptures;
}
void UFPSPerformanceMetricsSubsystem::CountVisibilityUpdate(const UObject* Context)
{
    if (auto* Metrics = Find(Context)) ++Metrics->TotalActions.VisibilityUpdates;
}
void UFPSPerformanceMetricsSubsystem::CountWorldVisibilityUpdate(const UObject* Context)
{
    if (auto* Metrics = Find(Context)) ++Metrics->TotalActions.WorldVisibilityUpdates;
}

void UFPSPerformanceMetricsSubsystem::ReadWindow(FFPSPerformanceSnapshot& Snapshot, double Now) const
{
    FFPSFrameBudget& Budget = Snapshot.Budget;
    Budget.bRecording = bRecording;
    Snapshot.TargetFps = TargetFps > 0.f ? TargetFps : 60.f;
    Snapshot.SlowFrameThresholdMs = SlowFrameThresholdMs;
    Snapshot.RequestedWindowSeconds = WindowSeconds;
    Snapshot.HitchThresholdMs = HitchThresholdMs;
    Snapshot.SessionId = SessionId;
    Snapshot.CaptureGeneration = CaptureGeneration;
    Snapshot.SnapshotSeconds = Now;
    Snapshot.EventsOverwritten = EventsOverwritten;
    Snapshot.EventsDiscardedAtBoundary = EventsDiscardedAtBoundary;
    Snapshot.ActiveEventCount = ActiveEvents.Num();
    Snapshot.RecentHitches = RecentHitches;
    Snapshot.WorstHitches = WorstHitches;
    Snapshot.HitchHistoryCapacity = MaxHitches;
    Snapshot.WorstHitchCapacity = MaxWorstHitches;
    Snapshot.HitchEventCapacity = MaxHitchEvents;
    Snapshot.HitchesOverwritten = HitchesOverwritten;
    if (SampleCount == 0) return;

    TArray<float> Frame, Game, Draw, Rhi, Gpu, GameWait, DrawWait, GameCritical, DrawCritical;
    Frame.Reserve(SampleCount);
    const int32 First = (WriteIndex - SampleCount + MaxSamples) % MaxSamples;
    const FFrameSample& FirstSample = FrameSamples[First];
    const FFrameSample& Last = FrameSamples[(WriteIndex + MaxSamples - 1) % MaxSamples];
    Budget.FirstFrameId = FirstSample.FrameId;
    Budget.LastFrameId = Last.FrameId;
    Budget.LatestSampleSeconds = Last.Seconds;
    Budget.SampleAgeSeconds = FMath::Max(0.0, Now - Last.Seconds);
    Snapshot.WindowStartSeconds = FirstSample.StartSeconds;
    Budget.DurationSeconds = Last.Seconds - FirstSample.StartSeconds;
    Budget.LatestFrameMs = Last.FrameMs;
    Budget.bCapacityLimited = SampleCount == MaxSamples && Budget.DurationSeconds < WindowSeconds;
    int32 OverBudget = 0, Slow = 0;
    float PeakMs = -1.f;
    Snapshot.Frames.Reserve(SampleCount);
    for (int32 Offset = 0; Offset < SampleCount; ++Offset)
    {
        const FFrameSample& Sample = FrameSamples[(First + Offset) % MaxSamples];
        Snapshot.Frames.Add(Sample);
        int32 SlowestIndex = 0;
        while (SlowestIndex < Snapshot.SlowestFrames.Num() && Snapshot.SlowestFrames[SlowestIndex].FrameMs >= Sample.FrameMs) ++SlowestIndex;
        if (SlowestIndex < 3)
        {
            Snapshot.SlowestFrames.Insert(Sample, SlowestIndex);
            if (Snapshot.SlowestFrames.Num() > 3) Snapshot.SlowestFrames.Pop(EAllowShrinking::No);
        }
        if (Sample.FrameMs > PeakMs) { PeakMs = Sample.FrameMs; Budget.PeakFrameId = Sample.FrameId; }
        Frame.Add(Sample.FrameMs);
        // A zero thread/GPU timer can mean not supported, not running or not yet published.
        if (Sample.GameMs > 0.f)
        {
            Game.Add(Sample.GameMs);
            GameWait.Add(Sample.GameWaitMs);
            if (Sample.GameCriticalMs > 0.f) GameCritical.Add(Sample.GameCriticalMs);
        }
        if (Sample.DrawMs > 0.f)
        {
            Draw.Add(Sample.DrawMs);
            DrawWait.Add(Sample.DrawWaitMs);
            if (Sample.DrawCriticalMs > 0.f) DrawCritical.Add(Sample.DrawCriticalMs);
        }
        if (Sample.RhiMs > 0.f) Rhi.Add(Sample.RhiMs);
        if (Sample.GpuMs > 0.f) Gpu.Add(Sample.GpuMs);
        if (Sample.FrameMs > 1000.f / Snapshot.TargetFps) ++OverBudget;
        if (Sample.FrameMs > Snapshot.SlowFrameThresholdMs) ++Slow;
        if (Sample.FrameMs >= 50.f) ++Snapshot.FramesAtLeast50Ms;
        if (Sample.FrameMs >= 100.f) ++Snapshot.FramesAtLeast100Ms;
        if (Sample.bPaused) ++Budget.PausedFrames;
        if (Sample.bBackground) ++Budget.BackgroundFrames;
        Snapshot.Actions += Sample.Actions;
        Snapshot.IconActions += Sample.Icons;
    }
    Budget.Frame = FPSPerformance::Distribution(MoveTemp(Frame));
    Budget.Game = FPSPerformance::Distribution(MoveTemp(Game));
    Budget.Draw = FPSPerformance::Distribution(MoveTemp(Draw));
    Budget.Rhi = FPSPerformance::Distribution(MoveTemp(Rhi));
    Budget.Gpu = FPSPerformance::Distribution(MoveTemp(Gpu));
    Budget.GameWait = FPSPerformance::Distribution(MoveTemp(GameWait));
    Budget.DrawWait = FPSPerformance::Distribution(MoveTemp(DrawWait));
    Budget.GameCritical = FPSPerformance::Distribution(MoveTemp(GameCritical));
    Budget.DrawCritical = FPSPerformance::Distribution(MoveTemp(DrawCritical));
    Budget.Fps = Budget.Frame.Average > 0.f ? 1000.f / Budget.Frame.Average : 0.f;
    Budget.OverBudgetFraction = static_cast<float>(OverBudget) / SampleCount;
    Budget.SlowFrameFraction = static_cast<float>(Slow) / SampleCount;
    Snapshot.OverBudgetFrames = OverBudget;
    Snapshot.SlowFrames = Slow;
    ReadEvents(Snapshot);
}

void UFPSPerformanceMetricsSubsystem::AddObserverSample(TArray<FObserverSample>& Samples, float Ms, double Now)
{
    if (!FMath::IsFinite(Ms) || Ms < 0.f) return;
    Samples.Add({Now, Ms});
    if (Samples.Num() > 256) Samples.RemoveAt(0, Samples.Num() - 256, EAllowShrinking::No);
}

FFPSMetricDistribution UFPSPerformanceMetricsSubsystem::ObserverStats(
    const TArray<FObserverSample>& Samples, double Since)
{
    TArray<float> Values;
    for (const FObserverSample& Sample : Samples)
        if (Sample.Seconds >= Since) Values.Add(Sample.Milliseconds);
    return FPSPerformance::Distribution(MoveTemp(Values));
}

void UFPSPerformanceMetricsSubsystem::RecordUiUpdate(float Ms)
{
    AddObserverSample(UiSamples, Ms, FPlatformTime::Seconds());
}
