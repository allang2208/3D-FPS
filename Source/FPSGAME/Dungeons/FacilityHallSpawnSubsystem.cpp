#include "FacilityHallSpawnSubsystem.h"
#include "FacilityHallEncounter.h"
#include "../Diagnostics/FPSResourceLifecycle.h"
#include "FacilityHallPreparationBudget.h"
#include "FacilityMonsterGpuWarmup.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformMemory.h"
#include "Misc/App.h"
#include "PSOPrecache.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

void UFacilityHallSpawnSubsystem::Request(AFacilityHallEncounter* Hall)
{
    if (IsValid(Hall) && Hall->GetWorld() == GetWorld() && Hall->HasAuthority() && Hall->SpawnPriority()!=INDEX_NONE) Pending.AddUnique(Hall);
}

void UFacilityHallSpawnSubsystem::Cancel(AFacilityHallEncounter* Hall)
{
    if (Hall) Hall->PreparationRequestedAt = -1.;
    if (PreparationCandidate.Get() == Hall) PreparationCandidate.Reset();
    Pending.RemoveAll([Hall](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Hall; });
    PreparationPending.RemoveAll([Hall](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Hall; });
    PreparedHalls.RemoveAll([Hall](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Hall; });
}

void UFacilityHallSpawnSubsystem::RequestPreparation(AFacilityHallEncounter* Hall)
{
    if (!IsValid(Hall) || Hall->GetWorld() != GetWorld() || !Hall->HasAuthority() || GetWorld()->GetNetMode() == NM_Client) return;
    // Pending rooms are re-evaluated by maintenance. Do not scan every slot
    // again just because the area's low-frequency update repeats its demand.
    if (PreparationPending.Contains(Hall)) return;
    double DistanceSquared;
    if (Hall->PreparationPriority(Hall->FindPreparationSlot(), DistanceSquared) == INDEX_NONE) return;
    Hall->PreparationRequestedAt = GetWorld()->GetTimeSeconds();
    PreparationPending.Add(Hall);
}

int32 UFacilityHallSpawnSubsystem::PreparedCount() const
{
    int32 Count = 0;
    for (const auto& Hall : PreparedHalls) if (Hall.IsValid()) Count += Hall->PreparedMonsters.Num();
    return Count;
}

uint64 UFacilityHallSpawnSubsystem::PreparedBytes() const
{
    uint64 Bytes = 0;
    for (const auto& Hall : PreparedHalls)
        if (Hall.IsValid()) for (const auto& Entry : Hall->PreparedMonsters) Bytes += Entry->EstimatedBytes;
    return Bytes;
}

bool UFacilityHallSpawnSubsystem::HasPreparationHeadroom(uint64 AdditionalBytes) const
{
    return PreparationHeadroomBlocker(AdditionalBytes).IsNone();
}

FName UFacilityHallSpawnSubsystem::PreparationHeadroomBlocker(uint64 AdditionalBytes) const
{
    const uint64 Required = FacilityHallPreparation::ReserveBytes + AdditionalBytes;
    if (AvailablePhysical < Required) return TEXT("cpu_physical_below_reserve");
    if (AvailableVirtual < Required) return TEXT("cpu_commit_below_reserve");
    if (GetWorld()->GetNetMode() == NM_DedicatedServer || !FApp::CanEverRender()) return NAME_None;
    const auto* Metrics = GetWorld()->GetSubsystem<UFPSPerformanceMetricsSubsystem>();
    uint64 Budget = 0, Used = 0;
    if (!Metrics || !Metrics->GetRecentRenderBudget(Budget, Used)) return TEXT("gpu_budget_unknown_or_stale");
    if (Used >= Budget || Budget - Used < Required) return TEXT("gpu_budget_below_reserve");
    return NAME_None;
}

TSharedRef<FJsonObject> UFacilityHallSpawnSubsystem::PreparationSnapshot() const
{
    const auto Result = MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("policy"), TEXT("Area topology: fixed catalog entry/shrine space and entry passage -> unstarted welcome; connected approach within 18m -> theme. Due waves before future waves; round-robin room reservations. Server-only deferred actors, client assets/PSOs use generator preparation."));
    Result->SetNumberField(TEXT("pending_preparations"), PreparationPending.Num());
    Result->SetNumberField(TEXT("instance_limit"), FacilityHallPreparation::MaxInstances);
    Result->SetBoolField(TEXT("component_pso_precaching_enabled"),IsComponentPSOPrecachingEnabled());
    Result->SetStringField(TEXT("instance_warmup_scope"),TEXT("same-instance staff/Bellow raster skinning and morph; no shadow, GI or ray-tracing capture"));
    Result->SetNumberField(TEXT("estimated_buffer_limit_bytes"), double(FacilityHallPreparation::MaxEstimatedBytes));
    Result->SetNumberField(TEXT("estimated_buffer_bytes"), double(PreparedBytes()));
    Result->SetNumberField(TEXT("required_free_bytes"), double(FacilityHallPreparation::ReserveBytes));
    Result->SetNumberField(TEXT("reclaim_below_bytes"), double(FacilityHallPreparation::ReclaimBelowBytes));
    Result->SetNumberField(TEXT("reclaim_recovery_bytes"), double(FacilityHallPreparation::ReclaimRecoveryBytes));
    Result->SetNumberField(TEXT("critical_free_bytes"), double(FacilityHallPreparation::CriticalReserveBytes));
    Result->SetBoolField(TEXT("memory_pressure_latched"), bPreparationMemoryPressure);
    Result->SetBoolField(TEXT("cpu_memory_sample_available"), MemorySamplePlatformSeconds >= 0.);
    Result->SetNumberField(TEXT("cpu_available_physical_bytes"), double(AvailablePhysical));
    Result->SetNumberField(TEXT("cpu_available_commit_bytes"), double(AvailableVirtual));
    Result->SetNumberField(TEXT("cpu_memory_sample_platform_seconds"), MemorySamplePlatformSeconds);
    Result->SetStringField(TEXT("last_admission_result"), LastPreparationAdmission.ToString());
    Result->SetNumberField(TEXT("last_admission_world_seconds"), LastPreparationAdmissionAt);
    Result->SetNumberField(TEXT("last_candidate_estimated_bytes"), double(LastPreparationCandidateBytes));
    Result->SetStringField(TEXT("admission_contract"), TEXT("Optional allocation requires CPU physical/commit and recent GPU budget headroom. The last admission result survives scheduler yields; CPU memory values are from the latest 0.25s sample, not DXGI non-local memory."));
    const double Now = GetWorld()->GetTimeSeconds();
    double Oldest = 0.;
    for (const auto& WeakHall : PreparationPending)
        if (const auto* Hall = WeakHall.Get(); Hall && Hall->PreparationRequestedAt >= 0.)
            Oldest = FMath::Max(Oldest, Now - Hall->PreparationRequestedAt);
    Result->SetNumberField(TEXT("oldest_request_age_seconds"), Oldest);
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (const auto& WeakHall : PreparedHalls)
        if (const auto* Hall = WeakHall.Get()) for (const auto& Entry : Hall->PreparedMonsters)
        {
            const auto Row = MakeShared<FJsonObject>();
            double DistanceSquared;
            Row->SetNumberField(TEXT("priority"), Hall->PreparationPriority(Entry->Slot, DistanceSquared));
            Row->SetNumberField(TEXT("room"), Hall->Room.Id);
            Row->SetNumberField(TEXT("slot"), Entry->Slot);
            Row->SetStringField(TEXT("class"), Entry->Monster.IsValid() ? Entry->Monster->GetClass()->GetPathName() : FString());
            Row->SetNumberField(TEXT("age_seconds"), Now - Entry->PreparedAt);
            Row->SetNumberField(TEXT("estimated_buffer_bytes"), double(Entry->EstimatedBytes));
            Row->SetStringField(TEXT("warmup"), Entry->GpuWarmup ? Entry->GpuWarmup->Stage().ToString() : TEXT("native_only"));
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
    Result->SetArrayField(TEXT("reservations"), Rows);
    return Result;
}

void UFacilityHallSpawnSubsystem::MaintainPreparation(double Now)
{
    if (Now < NextPreparationMaintenanceAt) return;
    NextPreparationMaintenanceAt = Now + .1;
    AFacilityHallEncounter* Best = nullptr;
    int32 BestPriority = MAX_int32, BestCount = MAX_int32;
    double BestDistance = TNumericLimits<double>::Max();
    // Prune and select in one stable-order pass; each room's slot is searched
    // once here, and activation still revalidates against live gameplay state.
    for (int32 Index = 0; Index < PreparationPending.Num();)
    {
        auto* Hall = PreparationPending[Index].Get();
        double DistanceSquared;
        const int32 Priority = Hall ? Hall->PreparationPriority(Hall->FindPreparationSlot(), DistanceSquared) : INDEX_NONE;
        if (Priority == INDEX_NONE)
        {
            if (Hall) Hall->PreparationRequestedAt = -1.;
            PreparationPending.RemoveAt(Index);
            continue;
        }
        ++Index;
        const int32 Count = Hall->PreparedMonsters.Num();
        if (Priority < BestPriority || (Priority == BestPriority && (Count < BestCount
            || (Count == BestCount && DistanceSquared < BestDistance))))
        { Best = Hall; BestPriority = Priority; BestCount = Count; BestDistance = DistanceSquared; }
    }
    PreparationCandidate = Best;
    if (bPreparationReleasePending)
    {
        if (!PreparationReleaseFence.IsFenceComplete()) return;
        bPreparationReleasePending = false;
    }
    // Retire one stale/lower-priority reservation before any capacity guard.
    // Memory pressure cannot strand a remote holding pool ahead of an active area.
    AFacilityHallEncounter* Retire = nullptr;
    bool bMustRetire = false;
    const auto* Metrics = GetWorld()->GetSubsystem<UFPSPerformanceMetricsSubsystem>();
    const bool bNeedsRenderBudget = GetWorld()->GetNetMode()!=NM_DedicatedServer && FApp::CanEverRender();
    auto BelowReserve = [this,Metrics,bNeedsRenderBudget](uint64 Reserve)
    {
        return AvailablePhysical<Reserve || AvailableVirtual<Reserve
            || (bNeedsRenderBudget && Metrics && Metrics->HasRecentRenderMemoryPressure(Reserve));
    };
    if (BelowReserve(FacilityHallPreparation::ReclaimBelowBytes)) bPreparationMemoryPressure=true;
    else if (AvailablePhysical>=FacilityHallPreparation::ReclaimRecoveryBytes
        && AvailableVirtual>=FacilityHallPreparation::ReclaimRecoveryBytes
        && (!bNeedsRenderBudget || (Metrics && Metrics->HasRecentRenderHeadroom(FacilityHallPreparation::ReclaimRecoveryBytes))))
        bPreparationMemoryPressure=false;
    // A stale render observation cannot authorize eviction, even if a previous
    // valid low-budget observation latched pressure. New admission still needs 1 GiB.
    const bool bPressure = bPreparationMemoryPressure && BelowReserve(FacilityHallPreparation::ReclaimRecoveryBytes);
    const bool bCriticalPressure = BelowReserve(FacilityHallPreparation::CriticalReserveBytes);
    int32 RetireIndex = INDEX_NONE, WorstPriority = bPressure ? INDEX_NONE : BestPriority;
    const uint64 NewBytes = Best ? Best->EstimatePreparationBytes(Best->FindPreparationSlot()) : 0;
    const bool bFull = PreparedCount() >= FacilityHallPreparation::MaxInstances
        || PreparedBytes() + NewBytes > FacilityHallPreparation::MaxEstimatedBytes;
    for (const auto& WeakHall : PreparedHalls)
    {
        auto* Hall = WeakHall.Get();
        if (!Hall) continue;
        for (int32 Index = 0; Index < Hall->PreparedMonsters.Num(); ++Index)
        {
            const auto& Entry = Hall->PreparedMonsters[Index];
            double DistanceSquared;
            const int32 Priority = Hall->PreparationPriority(Entry->Slot, DistanceSquared);
            const bool bWrongClass = Hall->Slots.IsValidIndex(Entry->Slot) && Entry->Monster.IsValid()
                && Entry->Monster->GetClass() != Hall->Members[Hall->Slots[Entry->Slot].Member];
            if (!Entry->Monster.IsValid() || Priority == INDEX_NONE || bWrongClass)
            { Retire = Hall; RetireIndex = Index; bMustRetire = true; break; }
            // Rank 0/1 is the current area's released wave (including its short
            // doorway grace period). Keep it across spawn cadence/backoff; using
            // SpawnPriority here would mistake a cooldown for an unused actor.
            // Critical pressure can reclaim these too, after less relevant slots.
            const bool bDueInCurrentArea = Priority<=1;
            const bool bReclaimForPressure = bPressure && (bCriticalPressure || !bDueInCurrentArea);
            const bool bReclaimForPriority = Best && bFull && Priority>BestPriority;
            if ((bReclaimForPressure || bReclaimForPriority) && Priority > WorstPriority)
            { Retire = Hall; RetireIndex = Index; WorstPriority = Priority; }
        }
        if (bMustRetire) break;
    }
    if (Retire)
    {
        const TCHAR* Reason = bMustRetire ? TEXT("area_priority_or_slot_changed")
            : bCriticalPressure ? TEXT("critical_memory_headroom")
            : bPressure ? TEXT("memory_reclaim_hysteresis") : TEXT("area_priority_or_slot_changed");
        Retire->DiscardPreparation(RetireIndex, Reason);
        PreparationDecision = TEXT("retired_reservation");
        PreparationReleaseFence.BeginFence();
        bPreparationReleasePending = true;
        // A retirement spends this optional slice even if its fence completes
        // immediately. Due gameplay remains eligible below.
        NextPreparationAt = FMath::Max(NextPreparationAt, Now + .1);
        NextWarmupAt = FMath::Max(NextWarmupAt, Now + .1);
    }
}

void UFacilityHallSpawnSubsystem::UpdatePreparation(double Now)
{
    if (Now < NextPreparationAt) return;
    NextPreparationAt = Now + .1;
    if (bPreparationReleasePending && !PreparationReleaseFence.IsFenceComplete())
    { PreparationDecision = TEXT("preparation_release_wait"); return; }
    bPreparationReleasePending = false;
    auto* Best = PreparationCandidate.Get();
    if (!Best) { PreparationDecision = TEXT("no_relevant_request"); return; }
    const int32 Slot = Best->FindPreparationSlot();
    double DistanceSquared;
    const int32 Priority = Best->PreparationPriority(Slot, DistanceSquared);
    if (Priority == INDEX_NONE) { PreparationCandidate.Reset(); return; }
    const uint64 Bytes = Best->EstimatePreparationBytes(Slot);
    if (PreparedCount() >= FacilityHallPreparation::MaxInstances || PreparedBytes() + Bytes > FacilityHallPreparation::MaxEstimatedBytes)
    { PreparationDecision = TEXT("prepared_capacity"); return; }
    const FName Blocker = PreparationHeadroomBlocker(Bytes);
    LastPreparationCandidateBytes = Bytes;
    LastPreparationAdmissionAt = Now;
    LastPreparationAdmission = Blocker.IsNone() ? FName(TEXT("headroom_available")) : Blocker;
    if (!Blocker.IsNone())
    { PreparationDecision = Blocker; return; }
    const double RequestAge = Best->PreparationRequestedAt >= 0. ? Now - Best->PreparationRequestedAt : 0.;
    PreparationCandidate.Reset();
    LastAttemptFrame = GFrameCounter;
    if (Best->PrepareNextSlot())
    {
        NextWarmupAt = Now + .1;
        PreparedHalls.AddUnique(Best);
        Best->PreparationRequestedAt = Now;
        PreparationDecision = TEXT("prepared_by_area_priority");
        // Pace optional registration without making due waves wait for it.
        PreparationRegistrationFence.BeginFence();
        bPreparationRegistrationPending = true;
        UFPSPerformanceMetricsSubsystem::RecordMarker(Best, TEXT("Hall.PreparationSelected"),
            FString::Printf(TEXT("room=%d slot=%d priority=%d request_age=%.3f prepared=%d"),
                Best->Room.Id, Slot, Priority, RequestAge, PreparedCount()), true);
    }
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
    PreparedHalls.RemoveAll([](const auto& Entry) { return !Entry.IsValid() || Entry->PreparedMonsters.IsEmpty(); });
    if (Now >= NextMemorySampleAt)
    {
        const auto Memory = FPlatformMemory::GetStats();
        AvailablePhysical = Memory.AvailablePhysical; AvailableVirtual = Memory.AvailableVirtual;
        MemorySamplePlatformSeconds = FPlatformTime::Seconds();
        NextMemorySampleAt = Now + .25;
    }
    auto* Metrics = World->GetSubsystem<UFPSPerformanceMetricsSubsystem>();
    if (Metrics && World->GetNetMode() != NM_DedicatedServer && (!PreparationPending.IsEmpty() || !PreparedHalls.IsEmpty()))
        Metrics->RefreshRenderBudget();
    MaintainPreparation(Now);
    // Poll existing warmups even if due gameplay has priority; no capture here.
    bool bGpuWarmupPending = false;
    for (const auto& Hall : PreparedHalls)
        if (Hall.IsValid()) for (const auto& Entry : Hall->PreparedMonsters)
            if (Entry->GpuWarmup)
            {
                Entry->GpuWarmup->Tick(false);
                bGpuWarmupPending |= Entry->GpuWarmup->Stage() == TEXT("gpu_pending");
            }
    if (bRenderRegistrationPending && !SpawnRenderFence.IsFenceComplete())
    { PreparationDecision = TEXT("render_registration_wait"); return; }
    bRenderRegistrationPending = false;
    Pending.RemoveAll([](const auto& Entry) { return !Entry.IsValid()||Entry->SpawnPriority()==INDEX_NONE; });
    if (!Pending.IsEmpty() && Now >= NextAttemptAt)
    {
        int32 Best=0;
        for(int32 I=1;I<Pending.Num();++I)
            if(Pending[I]->SpawnPriority()<Pending[Best]->SpawnPriority())Best=I;
        const TWeakObjectPtr<AFacilityHallEncounter> Hall = Pending[Best];
        Pending.RemoveAt(Best);
        LastAttemptFrame = GFrameCounter;
        NextAttemptAt = Now + .05;
        PreparationDecision = TEXT("due_spawn_priority");
        TRACE_CPUPROFILER_EVENT_SCOPE(FacilityHallSpawn_Admission);
        if (Hall.IsValid() && Hall->TrySpawnPendingSlot())
        {
            Hall->FailedSpawnAttempts=0;Hall->NextSpawnAttemptAt=Now+.2;
            SpawnRenderFence.BeginFence();
            bRenderRegistrationPending = true;
        }
        else if(Hall.IsValid())
        {
            ++Hall->FailedSpawnAttempts;
            Hall->NextSpawnAttemptAt=Now+FMath::Min(2.,.2*FMath::Pow(2.,FMath::Min(4,Hall->FailedSpawnAttempts/4)));
            if(Hall->FailedSpawnAttempts==8||Hall->FailedSpawnAttempts%60==0)
                UE_LOG(LogTemp,Warning,TEXT("[FacilityEncounter] Spawn deferred: room=%d attempts=%d objective_pending=%d"),
                    Hall->Room.Id,Hall->FailedSpawnAttempts,Hall->HasObjectiveSlot()?1:0);
        }
        return;
    }
    // Submit at most one capture every 100ms, and never allocate or activate a
    // monster in the same frame. Slow frames skip optional work, not due spawns.
    if (bPreparationRegistrationPending && !PreparationRegistrationFence.IsFenceComplete())
    { PreparationDecision = TEXT("optional_registration_pending"); return; }
    bPreparationRegistrationPending = false;
    if (bGpuWarmupPending) { PreparationDecision = TEXT("optional_gpu_work_pending"); return; }
    if (DeltaTime > 1.f / 30.f) { PreparationDecision = TEXT("optional_work_yield_slow_frame"); return; }
    if (!bPreparationReleasePending && Now >= NextWarmupAt && HasPreparationHeadroom(0))
        for (const auto& Hall : PreparedHalls)
            if (Hall.IsValid()) for (const auto& Entry : Hall->PreparedMonsters)
                if (Entry->GpuWarmup && Entry->GpuWarmup->Tick(true))
                {
                    NextWarmupAt = Now + .1;
                    NextPreparationAt = Now + .1;
                    LastAttemptFrame = GFrameCounter;
                    return;
                }
    UpdatePreparation(Now);
}

void UFacilityHallSpawnSubsystem::Deinitialize()
{
    FPSResourceLifecycle::Record(this,TEXT("SpawnPool.BeforeDeinitialize"),{
        {TEXT("prepared_instances"),PreparedCount()},
        {TEXT("pending_preparations"),PreparationPending.Num()},
        {TEXT("estimated_buffer_bytes"),int64(PreparedBytes())}});
    const auto RetiringHalls = PreparedHalls;
    PreparedHalls.Reset();
    for (const auto& Hall : RetiringHalls) if (Hall.IsValid()) Hall->DiscardPreparedMonster(TEXT("world_cleanup"));
    PreparationPending.Reset(); PreparationCandidate.Reset(); Pending.Reset();
    bPreparationMemoryPressure=false;
    FPSResourceLifecycle::Record(this,TEXT("SpawnPool.AfterDeinitialize"),{
        {TEXT("prepared_instances"),PreparedCount()},
        {TEXT("pending_preparations"),PreparationPending.Num()},
        {TEXT("estimated_buffer_bytes"),int64(PreparedBytes())}});
    Super::Deinitialize();
}
