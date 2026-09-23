#include "FPSPerformanceMetrics.h"

void UFPSPerformanceMetricsSubsystem::UpdateHitchHistory(const FFrameSample& Sample)
{
    // Read this frame's completed scopes once, even when recent/worst records overlap.
    TArray<FFPSPerformanceEvent> FrameEvents;
    bool bFrameEventsLimited = false;
    const auto NeedsFollowingFrame = [&Sample](const FFPSHitchRecord& Hitch)
    {
        return Sample.FrameId > Hitch.PeakFrameId && Sample.FrameId - Hitch.PeakFrameId <= 2;
    };
    if (RecentHitches.ContainsByPredicate(NeedsFollowingFrame) || WorstHitches.ContainsByPredicate(NeedsFollowingFrame))
        ReadEventsInRange(Sample.StartSeconds, Sample.Seconds, FrameEvents, bFrameEventsLimited);
    for (auto* History : {&RecentHitches, &WorstHitches})
    {
        for (auto& Hitch : *History)
        {
            if (!NeedsFollowingFrame(Hitch)) continue;
            Hitch.Frames.Add(Sample);
            Hitch.bEventsCapacityLimited |= bFrameEventsLimited;
            for (const auto& Event : FrameEvents)
            {
                if (Hitch.Events.ContainsByPredicate([&Event](const auto& Existing) { return Existing.Id == Event.Id; })) continue;
                if (Hitch.Events.Num() < MaxHitchEvents) Hitch.Events.Add(Event);
                else Hitch.bEventsCapacityLimited = true;
            }
            Hitch.ActiveScopesAtContextEnd = ActiveEvents.Num();
        }
    }
    if (Sample.FrameMs < 50.f) return;
    if (RecentHitches.Num() == MaxHitches)
    {
        RecentHitches.RemoveAt(0, 1, EAllowShrinking::No);
        ++HitchesOverwritten;
    }
    auto& Hitch = RecentHitches.AddDefaulted_GetRef();
    Hitch.PeakFrameId = Sample.FrameId;
    Hitch.PeakMs = Sample.FrameMs;
    const int32 ContextCount = FMath::Min(3, SampleCount);
    for (int32 Offset = ContextCount; Offset > 0; --Offset)
        Hitch.Frames.Add(FrameSamples[(WriteIndex - Offset + MaxSamples) % MaxSamples]);
    ReadEventsInRange(Hitch.Frames[0].StartSeconds, Sample.Seconds, Hitch.Events, Hitch.bEventsCapacityLimited);
    if (Hitch.Events.Num() > MaxHitchEvents)
    {
        Hitch.Events.SetNum(MaxHitchEvents, EAllowShrinking::No);
        Hitch.bEventsCapacityLimited = true;
    }
    Hitch.ActiveScopesAtContextEnd = ActiveEvents.Num();
    int32 WorstIndex = 0;
    while (WorstIndex < WorstHitches.Num() && WorstHitches[WorstIndex].PeakMs >= Sample.FrameMs) ++WorstIndex;
    if (WorstIndex < MaxWorstHitches)
    {
        WorstHitches.Insert(Hitch, WorstIndex);
        if (WorstHitches.Num() > MaxWorstHitches) WorstHitches.SetNum(MaxWorstHitches, EAllowShrinking::No);
    }
}

void UFPSPerformanceMetricsSubsystem::UpdateHitchEvents(const FFPSPerformanceEvent& Event)
{
    // A scope can finish after the engine boundary; retain it when it intersects saved context.
    for (auto* History : {&RecentHitches, &WorstHitches})
    {
        for (auto& Hitch : *History)
        {
            if (Event.EndSeconds < Hitch.Frames[0].StartSeconds || Event.StartSeconds > Hitch.Frames.Last().Seconds) continue;
            if (Hitch.Events.ContainsByPredicate([&Event](const auto& Existing) { return Existing.Id == Event.Id; })) continue;
            if (Hitch.Events.Num() < MaxHitchEvents) Hitch.Events.Add(Event);
            else Hitch.bEventsCapacityLimited = true;
        }
    }
}
