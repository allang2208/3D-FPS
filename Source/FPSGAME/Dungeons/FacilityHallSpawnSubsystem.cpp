#include "FacilityHallSpawnSubsystem.h"
#include "FacilityHallEncounter.h"
#include "Engine/World.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

void UFacilityHallSpawnSubsystem::Request(AFacilityHallEncounter* Hall)
{
    if (IsValid(Hall) && Hall->GetWorld() == GetWorld() && Hall->HasAuthority())
        Pending.AddUnique(Hall);
}

void UFacilityHallSpawnSubsystem::Cancel(AFacilityHallEncounter* Hall)
{
    Pending.RemoveAll([Hall](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Hall; });
}

bool UFacilityHallSpawnSubsystem::IsTickable() const
{
    return Super::IsTickable() && !Pending.IsEmpty();
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
    if (Now < NextAttemptAt) return;
    // Poll only: a stalled render thread must not block gameplay or admit another
    // batch of skeletal resources. This is registration completion, not GPU readiness.
    if (bRenderRegistrationPending && !SpawnRenderFence.IsFenceComplete()) return;
    bRenderRegistrationPending = false;

    Pending.RemoveAll([](const auto& Entry) { return !Entry.IsValid(); });
    if (Pending.IsEmpty()) return;
    const TWeakObjectPtr<AFacilityHallEncounter> Hall = Pending[0];
    Pending.RemoveAt(0);
    LastAttemptFrame = GFrameCounter;
    NextAttemptAt = Now + .05;
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
    Pending.Reset();
    Super::Deinitialize();
}
