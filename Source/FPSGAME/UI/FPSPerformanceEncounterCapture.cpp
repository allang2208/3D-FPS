#include "FPSPerformanceMetrics.h"
#include "HAL/IConsoleManager.h"
#include "Dom/JsonObject.h"

namespace
{
TAutoConsoleVariable<int32> GpuInventoryMode(TEXT("fps.Perf.GpuResourceInventory"),0,
    TEXT("Opt-in event-triggered tracked RHI inventory. Enumeration may stall resource allocation; its interval/cost is exported."));
}

bool UFPSPerformanceMetricsSubsystem::IsGpuInventoryEnabled() { return GpuInventoryMode.GetValueOnGameThread()!=0; }
void UFPSPerformanceMetricsSubsystem::SetGpuInventoryEnabled(bool bEnabled)
{ GpuInventoryMode->Set(bEnabled?1:0,ECVF_SetByConsole); }

void UFPSPerformanceMetricsSubsystem::ResetEncounterDiagnostics()
{
    ActiveCombatWindow.Reset(); CombatWindows.Reset(); EncounterEvents.Reset(); GpuResourceInventories.Reset();
    GpuInventoryRequests.Reset(); bGpuInventoryPending=false; NextGpuInventorySeconds=0.;
    CombatWindowsOverwritten=EncounterEventsOverwritten=GpuInventoriesOverwritten=0;
}

void UFPSPerformanceMetricsSubsystem::StartCombatWindow(const UObject* Context, const FString& Reason)
{
    auto* Self=Find(Context);
    if(!Self || !Self->bRecording)return;
    const double Now=FPlatformTime::Seconds();
    if(Self->ActiveCombatWindow && Now>Self->ActiveCombatWindow->RequestedEndSeconds) Self->ArchiveCombatWindow(true);
    if(!Self->ActiveCombatWindow)
    {
        Self->ActiveCombatWindow=MakeUnique<FFPSCombatWindow>();
        auto& Window=*Self->ActiveCombatWindow;
        Window.Trigger=Reason; Window.TriggerSeconds=Now; Window.RequestedEndSeconds=Now+20.;
        const int32 First=(Self->WriteIndex-Self->SampleCount+MaxSamples)%MaxSamples;
        for(int32 I=0;I<Self->SampleCount;++I)
        {
            const auto& Frame=Self->FrameSamples[(First+I)%MaxSamples];
            if(Frame.Seconds<Now-3.)continue;
            if(Window.Frames.Num()<MaxCombatFrames)Window.Frames.Add(Frame);
            else Window.bFrameCapacityLimited=true;
        }
        for(const auto& Event:Self->EncounterEvents)
            if(Event.EndSeconds>=Now-3.)Window.Events.Add(Event);
        RequestGpuResourceInventory(Context,Reason+TEXT(" / wave-start"));
        RequestGpuResourceInventory(Context,Reason+TEXT(" / wave+10s"),10.);
    }
    else
    {
        // Two halls often start together. Keep one window; additional triggers
        // can extend it, but never retain an unbounded session of per-frame data.
        auto& Window=*Self->ActiveCombatWindow;
        Window.RequestedEndSeconds=FMath::Min(Window.TriggerSeconds+30.,FMath::Max(Window.RequestedEndSeconds,Now+20.));
    }
    RecordMarker(Context,TEXT("Hall.CaptureTrigger"),Reason,true);
}

void UFPSPerformanceMetricsSubsystem::ArchiveCombatWindow(bool bComplete)
{
    if(!ActiveCombatWindow)return;
    CopyResourcesForWindow(*ActiveCombatWindow);
    ActiveCombatWindow->bComplete=bComplete && !ActiveCombatWindow->bFrameCapacityLimited
        && !ActiveCombatWindow->Frames.IsEmpty()
        && ActiveCombatWindow->Frames.Last().Seconds>=ActiveCombatWindow->RequestedEndSeconds;
    if(CombatWindows.Num()>=MaxCombatWindows){CombatWindows.RemoveAt(0);++CombatWindowsOverwritten;}
    CombatWindows.Add(MakeShared<FFPSCombatWindow>(MoveTemp(*ActiveCombatWindow)));
    ActiveCombatWindow.Reset();
}

void UFPSPerformanceMetricsSubsystem::CopyResourcesForWindow(FFPSCombatWindow& Window) const
{
    Window.ResourceSamples.Reset();
    const int32 First=RenderResourceSamples.Num()==MaxRenderResourceSamples?RenderResourceWriteIndex:0;
    for(int32 I=0;I<RenderResourceSamples.Num();++I)
    {
        const auto& Row=RenderResourceSamples[(First+I)%RenderResourceSamples.Num()];
        const double Seconds=Row->GetNumberField(TEXT("game_seconds"));
        if(Seconds>=Window.TriggerSeconds-3. && Seconds<=Window.RequestedEndSeconds)Window.ResourceSamples.Add(Row);
    }
}

void UFPSPerformanceMetricsSubsystem::UpdateEncounterCapture(const FFPSRecordedFrame& Frame)
{
    if(ActiveCombatWindow)
    {
        auto& Window=*ActiveCombatWindow;
        if(Window.Frames.IsEmpty() || Window.Frames.Last().FrameId!=Frame.FrameId)
        {
            if(Window.Frames.Num()<MaxCombatFrames)Window.Frames.Add(Frame);
            else Window.bFrameCapacityLimited=true;
        }
        if(Frame.Seconds>=Window.RequestedEndSeconds)ArchiveCombatWindow(true);
    }
    PumpGpuResourceInventory(Frame.Seconds);
}

void UFPSPerformanceMetricsSubsystem::KeepEncounterEvent(const FFPSPerformanceEvent& Event)
{
    if(Event.bRetainForEncounter)
    {
        if(EncounterEvents.Num()>=MaxEncounterEvents){EncounterEvents.RemoveAt(0);++EncounterEventsOverwritten;}
        EncounterEvents.Add(Event);
    }
    if(ActiveCombatWindow && (Event.bRetainForEncounter || Event.Stage==TEXT("Engine.GarbageCollection")
        || Event.Stage==TEXT("Engine.SyncLoadPackageStart") || Event.Stage==TEXT("Engine.AsyncLoadingFlushStart")))
    {
        auto& Window=*ActiveCombatWindow;
        if(Window.Events.Num()<MaxEncounterEvents)Window.Events.Add(Event);
        else ++Window.EventsDiscarded;
    }
}

void UFPSPerformanceMetricsSubsystem::ReadEncounterDiagnostics(FFPSPerformanceSnapshot& Snapshot) const
{
    Snapshot.CombatWindows=CombatWindows;
    if(ActiveCombatWindow)
    {
        auto Copy=MakeShared<FFPSCombatWindow>(*ActiveCombatWindow);
        CopyResourcesForWindow(*Copy);Snapshot.CombatWindows.Add(Copy);
    }
    Snapshot.EncounterEvents=EncounterEvents;
    Snapshot.GpuResourceInventories=GpuResourceInventories;
    Snapshot.CombatWindowsOverwritten=CombatWindowsOverwritten;
    Snapshot.EncounterEventsOverwritten=EncounterEventsOverwritten;
    Snapshot.GpuInventoriesOverwritten=GpuInventoriesOverwritten;
    Snapshot.bGpuInventoryEnabled=IsGpuInventoryEnabled();
    Snapshot.bGpuInventoryPending=bGpuInventoryPending;
    Snapshot.GpuInventoryQueued=GpuInventoryRequests.Num();
}

void UFPSPerformanceMetricsSubsystem::RequestGpuResourceInventory(const UObject* Context,const FString& Reason,double DelaySeconds)
{
    auto* Self=Find(Context);
    if(!Self || !Self->bRecording || !IsGpuInventoryEnabled())return;
    const double Now=FPlatformTime::Seconds(), Due=Now+FMath::Max(0.,DelaySeconds);
    for(auto& Request:Self->GpuInventoryRequests)
        if(FMath::Abs(Request.Due-Due)<1.)
        { Request.Reason=(Request.Reason+TEXT("; ")+Reason).Left(512);return; }
    // Preserve a requested future sample; coalesce excess reasons into the last
    // request rather than creating a scan for every monster in a wave.
    if(Self->GpuInventoryRequests.Num()>=4)
    {
        auto& Last=Self->GpuInventoryRequests.Last();
        Last.Reason=(Last.Reason+TEXT("; coalesced: ")+Reason).Left(512);return;
    }
    Self->GpuInventoryRequests.Add({Reason,Due,Now,GFrameCounter});
    Self->GpuInventoryRequests.Sort([](const auto& A,const auto& B){return A.Due<B.Due;});
}
