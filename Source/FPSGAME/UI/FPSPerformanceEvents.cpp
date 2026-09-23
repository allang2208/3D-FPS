#include "FPSPerformanceMetrics.h"

FFPSIconActions FFPSIconActions::operator-(const FFPSIconActions& Other) const
{
    FFPSIconActions Result;
    for (int32 Index = 0; Index < static_cast<int32>(EFPSIconAction::Count); ++Index)
        Result.Values[Index] = Values[Index] - Other.Values[Index];
    return Result;
}

FFPSIconActions& FFPSIconActions::operator+=(const FFPSIconActions& Other)
{
    for (int32 Index = 0; Index < static_cast<int32>(EFPSIconAction::Count); ++Index)
        Values[Index] += Other.Values[Index];
    return *this;
}

void UFPSPerformanceMetricsSubsystem::CountIconAction(const UObject* Context, EFPSIconAction Action)
{
    const int32 Index = static_cast<int32>(Action);
    if (Index >= static_cast<int32>(EFPSIconAction::Count)) return;
    if (auto* Metrics = Find(Context)) ++Metrics->TotalIconActions.Values[Index];
}

uint64 UFPSPerformanceMetricsSubsystem::BeginEvent(FName Stage, const FString& Key)
{
    if (!bRecording) return 0;
    FFPSPerformanceEvent Event;
    Event.Id = ++NextEventId;
    Event.Stage = Stage;
    Event.StartFrame = GFrameCounter;
    Event.StartSeconds = FPlatformTime::Seconds();
    Event.ParentId = ActiveEvents.IsEmpty() ? 0 : ActiveEvents.Last().Id;
    Event.Key = Key.IsEmpty() && !ActiveEvents.IsEmpty() ? ActiveEvents.Last().Key : Key;
    ActiveEvents.Add(MoveTemp(Event));
    return NextEventId;
}

void UFPSPerformanceMetricsSubsystem::EndEvent(uint64 EventId, uint64 Generation)
{
    if (!bRecording || Generation != EventEpoch) return;
    const int32 Index = ActiveEvents.IndexOfByPredicate(
        [EventId](const FFPSPerformanceEvent& Event) { return Event.Id == EventId; });
    if (Index == INDEX_NONE) return;
    FFPSPerformanceEvent Event = MoveTemp(ActiveEvents[Index]);
    ActiveEvents.RemoveAt(Index, 1, EAllowShrinking::No);
    Event.EndSeconds = FPlatformTime::Seconds();
    Event.EndFrame = GFrameCounter;
    AppendEvent(MoveTemp(Event));
}

void UFPSPerformanceMetricsSubsystem::AppendEvent(FFPSPerformanceEvent Event)
{
    if (CompletedEvents.IsEmpty()) return;
    if (EventCount == MaxEvents)
    {
        ++EventsOverwritten;
        LastOverwrittenEventEnd = FMath::Max(LastOverwrittenEventEnd, CompletedEvents[EventWriteIndex].EndSeconds);
    }
    CompletedEvents[EventWriteIndex] = MoveTemp(Event);
    UpdateHitchEvents(CompletedEvents[EventWriteIndex]);
    EventWriteIndex = (EventWriteIndex + 1) % MaxEvents;
    EventCount = FMath::Min(EventCount + 1, MaxEvents);
}

void UFPSPerformanceMetricsSubsystem::InvalidateActiveEvents()
{
    ++EventEpoch;
    EventsDiscardedAtBoundary += ActiveEvents.Num();
    ActiveEvents.Reset();
}

void UFPSPerformanceMetricsSubsystem::RecordMarker(const UObject* Context, FName Stage, const FString& Detail)
{
    auto* Metrics = Find(Context);
    if (!Metrics || !Metrics->bRecording) return;
    FFPSPerformanceEvent Event;
    Event.Id = ++Metrics->NextEventId;
    Event.Stage = Stage;
    Event.Key = Detail;
    Event.bMarker = true;
    Event.StartFrame = Event.EndFrame = GFrameCounter;
    Event.StartSeconds = Event.EndSeconds = FPlatformTime::Seconds();
    Metrics->AppendEvent(MoveTemp(Event));
}

void UFPSPerformanceMetricsSubsystem::ReadEvents(FFPSPerformanceSnapshot& Snapshot) const
{
    const double Start = Snapshot.WindowStartSeconds, End = Snapshot.Budget.LatestSampleSeconds;
    ReadEventsInRange(Start, End, Snapshot.Events, Snapshot.bEventsCapacityLimited);
}

void UFPSPerformanceMetricsSubsystem::ReadEventsInRange(double Start, double End,
    TArray<FFPSPerformanceEvent>& Out, bool& bLimited) const
{
    bLimited = EventsOverwritten > 0 && LastOverwrittenEventEnd >= Start;
    const int32 First = (EventWriteIndex - EventCount + MaxEvents) % MaxEvents;
    // Completion times are monotonic: all events are appended synchronously on the game thread.
    // Find the first possible intersection instead of scanning the entire retained ring for every hitch context.
    int32 Low = 0, High = EventCount;
    while (Low < High)
    {
        const int32 Middle = Low + (High - Low) / 2;
        if (CompletedEvents[(First + Middle) % MaxEvents].EndSeconds < Start) Low = Middle + 1;
        else High = Middle;
    }
    TSet<uint64> IncludedIds;
    for (int32 Offset = Low; Offset < EventCount; ++Offset)
    {
        const auto& Event = CompletedEvents[(First + Offset) % MaxEvents];
        if (Event.EndSeconds < Start || Event.StartSeconds > End) continue;
        auto& Copy = Out.Add_GetRef(Event);
        Copy.bCrossesWindowStart = Event.StartSeconds < Start;
        Copy.bCrossesWindowEnd = Event.EndSeconds > End;
        IncludedIds.Add(Event.Id);
    }
    for (auto& Event : Out)
        Event.bParentMissing = Event.ParentId != 0 && !IncludedIds.Contains(Event.ParentId);
}

void UFPSPerformanceMetricsSubsystem::BeginWorldTick(UWorld* World, ELevelTick, float)
{
    if (World != GetWorld() || !World->HasBegunPlay()) return;
    BindGameViewport();
    WorldTickEventEpoch = EventEpoch;
    WorldTickEventId = BeginEvent(TEXT("World.Tick"), FString());
}

void UFPSPerformanceMetricsSubsystem::EndWorldTick(UWorld* World, ELevelTick, float)
{
    if (World != GetWorld() || !WorldTickEventId) return;
    EndEvent(WorldTickEventId, WorldTickEventEpoch);
    WorldTickEventId = 0;
}

FFPSPerformanceScope::FFPSPerformanceScope(const UObject* Context, FName Stage, const FString& Key)
{
    if (auto* Owner = UFPSPerformanceMetricsSubsystem::Find(Context))
    {
        Metrics = Owner;
        Generation = Owner->EventEpoch;
        EventId = Owner->BeginEvent(Stage, Key);
    }
}

FFPSPerformanceScope::~FFPSPerformanceScope() { Finish(); }

void FFPSPerformanceScope::Finish()
{
    if (!EventId) return;
    if (auto* Owner = Metrics.Get()) Owner->EndEvent(EventId, Generation);
    EventId = 0;
}
