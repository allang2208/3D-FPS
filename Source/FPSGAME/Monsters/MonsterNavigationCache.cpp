#include "MonsterNavigationCache.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "CoreGlobals.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

bool UMonsterNavigationCache::Project(UNavigationSystemV1* Nav, const ANavigationData* Data,
    const FVector& Position, const FVector& Extent, FNavLocation& Result)
{
    if (!Nav || !Data) return false;
    TRACE_CPUPROFILER_EVENT_SCOPE(MonsterNavigation_ProjectGoal);
    if (Frame!=GFrameCounter) { Frame=GFrameCounter; Projections.Reset(); }
    // Dynamic navigation updates must never reuse a previous projection.
    if (UNavigationSystemV1::IsNavigationBeingBuiltOrLocked(this))
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(MonsterNavigation_UncachedWhileBuilding);
        Projections.Reset();
        return Nav->ProjectPointToNavigation(Position,Result,Extent,Data);
    }
    for (const auto& Entry:Projections)
        if (Entry.Data.Get()==Data && Entry.Position==Position && Entry.Extent==Extent)
        { TRACE_CPUPROFILER_EVENT_SCOPE(MonsterNavigation_ProjectionCacheHit); Result=Entry.Result; return Entry.bFound; }
    TRACE_CPUPROFILER_EVENT_SCOPE(MonsterNavigation_ProjectionCacheMiss);
    const bool bFound=Nav->ProjectPointToNavigation(Position,Result,Extent,Data);
    // Exact coordinates, nav data/agent and extents; no rounded goals or shared
    // paths between different start points, and no scheduling delay.
    if (Projections.Num()<64)
    {
        auto& Entry=Projections.AddDefaulted_GetRef();
        Entry.Data=Data; Entry.Position=Position; Entry.Extent=Extent;
        Entry.Result=Result; Entry.bFound=bFound;
    }
    return bFound;
}
