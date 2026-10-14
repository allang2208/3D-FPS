#include "FacilityHallSpawnSubsystem.h"
#include "FacilityHallEncounter.h"
#include "FacilityMonsterGpuWarmup.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

void UFacilityHallSpawnSubsystem::Request(AFacilityHallEncounter* Hall)
{
    if (IsValid(Hall) && Hall->GetWorld() == GetWorld() && Hall->HasAuthority())
        Pending.AddUnique(Hall);
}

void UFacilityHallSpawnSubsystem::Cancel(AFacilityHallEncounter* Hall)
{
    Pending.RemoveAll([Hall](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Hall; });
    PreparationPending.RemoveAll([Hall](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Hall; });
    PreparedHalls.RemoveAll([Hall](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Hall; });
}

void UFacilityHallSpawnSubsystem::RequestPreparation(AFacilityHallEncounter* Hall)
{
    if (IsValid(Hall) && Hall->GetWorld()==GetWorld() && GetWorld()->GetNetMode()==NM_Standalone)
        PreparationPending.AddUnique(Hall);
}

int32 UFacilityHallSpawnSubsystem::PreparedCount() const
{
    int32 Count=0;
    for (const auto& Hall:PreparedHalls) if (Hall.IsValid() && Hall->PreparedMonster.IsValid()) ++Count;
    return Count;
}

bool UFacilityHallSpawnSubsystem::IsTickable() const
{
    return Super::IsTickable() && (!Pending.IsEmpty() || !PreparationPending.IsEmpty() || !PreparedHalls.IsEmpty());
}

TStatId UFacilityHallSpawnSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(UFacilityHallSpawnSubsystem, STATGROUP_Tickables);
}

void UFacilityHallSpawnSubsystem::Tick(float DeltaTime)
{
    UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_Client || LastAttemptFrame == GFrameCounter) return;
    const double Now = World->GetTimeSeconds();
    PreparedHalls.RemoveAll([](const auto& Entry){return !Entry.IsValid() || !Entry->PreparedMonster.IsValid();});
    const auto* Metrics=World->GetSubsystem<UFPSPerformanceMetricsSubsystem>();
    bool bAllowWarmup=!bRenderRegistrationPending && (Pending.IsEmpty() || Now<NextAttemptAt)
        && Metrics && Metrics->HasRecentRenderHeadroom(1024ull*1024ull*1024ull);
    for(const auto& Hall:PreparedHalls)
        if(Hall.IsValid()&&Hall->PreparedGpuWarmup)
        {
            if(Hall->PreparedGpuWarmup->Tick(bAllowWarmup))
                bAllowWarmup=false; // At most one optional capture admission this frame.
        }
    // Poll only: a stalled render thread must not block gameplay or admit another
    // batch of skeletal resources. This is registration completion, not GPU readiness.
    if (bRenderRegistrationPending && !SpawnRenderFence.IsFenceComplete())
    { PreparationDecision=TEXT("render_registration_wait"); return; }
    bRenderRegistrationPending = false;

    Pending.RemoveAll([](const auto& Entry) { return !Entry.IsValid(); });
    if (Pending.IsEmpty() || Now < NextAttemptAt)
    {
        if (Now < NextPreparationAt) return;
        NextPreparationAt=Now+.1;
        PreparationPending.RemoveAll([](const auto& Entry){return !Entry.IsValid();});
        PreparedHalls.RemoveAll([](const auto& Entry){return !Entry.IsValid() || !Entry->PreparedMonster.IsValid();});
        // Never reserve an entire wave. Use the existing passive RHI sample;
        // no query flush, GPU wait or new high-frequency resource scan.
        if (PreparationPending.IsEmpty()) {PreparationDecision=TEXT("no_request");return;}
        if (PreparedCount()>=2) {PreparationDecision=TEXT("prepared_capacity");return;}
        if (!Metrics || !Metrics->HasRecentRenderHeadroom(1024ull*1024ull*1024ull))
        {PreparationDecision=TEXT("budget_unknown_or_below_reserve");return;}
        const auto Hall=PreparationPending[0]; PreparationPending.RemoveAt(0);
        LastAttemptFrame=GFrameCounter;
        if (Hall.IsValid() && Hall->PrepareNextSlot())
        {PreparedHalls.AddUnique(Hall);PreparationDecision=TEXT("prepared");}
        else PreparationDecision=TEXT("no_eligible_slot");
        return;
    }
    const TWeakObjectPtr<AFacilityHallEncounter> Hall = Pending[0];
    Pending.RemoveAt(0);
    LastAttemptFrame = GFrameCounter;
    NextAttemptAt = Now + .05;
    PreparationDecision=TEXT("due_spawn_priority");
    TRACE_CPUPROFILER_EVENT_SCOPE(FacilityHallSpawn_Admission);
    // Consume one request before calling into the actor; its lifecycle callbacks
    // may cancel other queued entries. Each hall retains its 200 ms request rate.
    if (Hall.IsValid() && Hall->TrySpawnPendingSlot())
    {
        SpawnRenderFence.BeginFence();
        bRenderRegistrationPending = true;
    }
}

void UFacilityHallSpawnSubsystem::Deinitialize()
{
    for (const auto& Hall:PreparedHalls) if (Hall.IsValid()) Hall->DiscardPreparedMonster();
    PreparedHalls.Reset(); PreparationPending.Reset();
    Pending.Reset();
    Super::Deinitialize();
}
