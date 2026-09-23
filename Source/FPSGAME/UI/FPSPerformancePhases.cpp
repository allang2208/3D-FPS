#include "FPSPerformanceMetrics.h"

#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "Debugging/SlateDebugging.h"
#include "Rendering/DrawElements.h"
#include "Widgets/SWindow.h"
#include "Misc/CoreDelegates.h"
#include "UObject/UObjectGlobals.h"

void UFPSPerformanceMetricsSubsystem::BindPhaseDelegates()
{
    if (FSlateApplication::IsInitialized())
    {
        SlatePreHandle = FSlateApplication::Get().OnPreTick().AddUObject(this, &ThisClass::BeginSlateWidgets);
        SlatePostHandle = FSlateApplication::Get().OnPostTick().AddUObject(this, &ThisClass::EndSlateWidgets);
    }
    CoreTickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &ThisClass::MarkCoreTicker));
#if WITH_SLATE_DEBUGGING
    WindowBeginHandle = FSlateDebugging::BeginWindow.AddUObject(this, &ThisClass::BeginWindowPaint);
    WindowEndHandle = FSlateDebugging::EndWindow.AddUObject(this, &ThisClass::EndWindowPaint);
#endif
    GcBeginHandle = FCoreUObjectDelegates::GetPreGarbageCollectDelegate().AddUObject(this, &ThisClass::BeginGarbageCollection);
    GcEndHandle = FCoreUObjectDelegates::GetPostGarbageCollect().AddUObject(this, &ThisClass::EndGarbageCollection);
    SyncLoadHandle = FCoreDelegates::OnSyncLoadPackage.AddUObject(this, &ThisClass::MarkSyncLoad);
    AsyncFlushHandle = FCoreDelegates::OnAsyncLoadingFlush.AddUObject(this, &ThisClass::MarkAsyncLoadingFlush);
}

void UFPSPerformanceMetricsSubsystem::UnbindPhaseDelegates()
{
    if (FSlateApplication::IsInitialized())
    {
        FSlateApplication::Get().OnPreTick().Remove(SlatePreHandle);
        FSlateApplication::Get().OnPostTick().Remove(SlatePostHandle);
    }
    FTSTicker::RemoveTicker(CoreTickerHandle);
#if WITH_SLATE_DEBUGGING
    FSlateDebugging::BeginWindow.Remove(WindowBeginHandle);
    FSlateDebugging::EndWindow.Remove(WindowEndHandle);
#endif
    FCoreUObjectDelegates::GetPreGarbageCollectDelegate().Remove(GcBeginHandle);
    FCoreUObjectDelegates::GetPostGarbageCollect().Remove(GcEndHandle);
    FCoreDelegates::OnSyncLoadPackage.Remove(SyncLoadHandle);
    FCoreDelegates::OnAsyncLoadingFlush.Remove(AsyncFlushHandle);
    if (auto* Viewport = ObservedViewport.Get())
    {
        Viewport->OnBeginDraw().Remove(ViewportBeginHandle);
        Viewport->OnEndDraw().Remove(ViewportEndHandle);
    }
    ObservedViewport.Reset();
    SlateEventStack.Reset();
    WindowEventStack.Reset();
}

void UFPSPerformanceMetricsSubsystem::BindGameViewport()
{
    auto* Viewport = GetWorld()->GetGameViewport();
    if (ObservedViewport.Get() == Viewport) return;
    if (auto* Previous = ObservedViewport.Get())
    {
        Previous->OnBeginDraw().Remove(ViewportBeginHandle);
        Previous->OnEndDraw().Remove(ViewportEndHandle);
    }
    ObservedViewport = Viewport;
    ViewportEventId = 0;
    if (Viewport)
    {
        ViewportBeginHandle = Viewport->OnBeginDraw().AddUObject(this, &ThisClass::BeginViewportDraw);
        ViewportEndHandle = Viewport->OnEndDraw().AddUObject(this, &ThisClass::EndViewportDraw);
    }
}

void UFPSPerformanceMetricsSubsystem::BeginViewportDraw()
{
    if (!IsInGameThread() || !GetWorld() || !GetWorld()->HasBegunPlay()) return;
    ViewportEventEpoch = EventEpoch;
    ViewportEventId = BeginEvent(TEXT("Viewport.Draw"), FString());
}

void UFPSPerformanceMetricsSubsystem::EndViewportDraw()
{
    if (!IsInGameThread() || !ViewportEventId) return;
    EndEvent(ViewportEventId, ViewportEventEpoch);
    ViewportEventId = 0;
}

void UFPSPerformanceMetricsSubsystem::BeginSlateWidgets(float)
{
    if (!IsInGameThread()) return;
    // Keep pairing through clear/stop and nested modal ticks, even when recording is off.
    const bool bStarted = GetWorld() && GetWorld()->HasBegunPlay();
    const uint64 Id = bStarted ? BeginEvent(TEXT("Slate.TickAndDrawWidgets"), FString()) : 0;
    SlateEventStack.Emplace(Id, EventEpoch);
}

void UFPSPerformanceMetricsSubsystem::EndSlateWidgets(float)
{
    if (!IsInGameThread() || SlateEventStack.IsEmpty()) return;
    const auto Entry = SlateEventStack.Pop(EAllowShrinking::No);
    if (Entry.Key) EndEvent(Entry.Key, Entry.Value);
}

bool UFPSPerformanceMetricsSubsystem::MarkCoreTicker(float)
{
    if (IsInGameThread() && GetWorld() && GetWorld()->HasBegunPlay())
        RecordMarker(this, TEXT("Engine.CoreTickerBoundary"));
    return true;
}

void UFPSPerformanceMetricsSubsystem::BeginWindowPaint(const FSlateWindowElementList& Elements)
{
    if (!IsInGameThread()) return;
    const auto* Window = Elements.GetPaintWindow();
    const bool bStarted = GetWorld() && GetWorld()->HasBegunPlay();
    const uint64 Id = bStarted ? BeginEvent(TEXT("Slate.WindowPaint"), Window ? Window->GetTitle().ToString().Left(128) : FString()) : 0;
    WindowEventStack.Emplace(Id, EventEpoch);
}

void UFPSPerformanceMetricsSubsystem::EndWindowPaint(const FSlateWindowElementList&)
{
    if (!IsInGameThread() || WindowEventStack.IsEmpty()) return;
    const auto Entry = WindowEventStack.Pop(EAllowShrinking::No);
    if (Entry.Key) EndEvent(Entry.Key, Entry.Value);
}

void UFPSPerformanceMetricsSubsystem::BeginGarbageCollection()
{
    if (!IsInGameThread() || !GetWorld() || !GetWorld()->HasBegunPlay()) return;
    GcEventEpoch = EventEpoch;
    GcEventId = BeginEvent(TEXT("Engine.GarbageCollection"), FString());
}

void UFPSPerformanceMetricsSubsystem::EndGarbageCollection()
{
    if (!IsInGameThread() || !GcEventId) return;
    EndEvent(GcEventId, GcEventEpoch);
    GcEventId = 0;
}

void UFPSPerformanceMetricsSubsystem::MarkSyncLoad(const FString& Package)
{
    if (IsInGameThread() && GetWorld() && GetWorld()->HasBegunPlay())
        RecordMarker(this, TEXT("Engine.SyncLoadPackageStart"), Package);
}

void UFPSPerformanceMetricsSubsystem::MarkAsyncLoadingFlush()
{
    if (IsInGameThread() && GetWorld() && GetWorld()->HasBegunPlay())
        RecordMarker(this, TEXT("Engine.AsyncLoadingFlushStart"));
}
