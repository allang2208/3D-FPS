#include "FPSPerformanceMetrics.h"
#include "Debugging/SlateDebugging.h"
#include "Async/Async.h"

#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Guid.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
TSharedRef<FJsonObject> LightingJson(const FFPSPerformanceSnapshot& Snapshot)
{
    auto Result = MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("contract"), TEXT("Current-World component snapshot, independent of mesh Top N. Includes ULightComponent local/directional lights, not SkyLightComponent. Enabled means registered, visible flags, affects world and ComputeLightBrightness > 0 (accounts for EV/IES). Candidates only filter enabled state, scaled max draw distance and spherical bounds vs view frustum; not occlusion, exact spot-cone or screen-size culling, actual renderer submissions, or GPU cost."));
    Result->SetStringField(TEXT("ordering"), TEXT("view candidates first, then enabled, then ascending distance; path breaks ties"));
    Result->SetStringField(TEXT("legacy_coverage_contract"), TEXT("scene_coverage.VisibleLights and ShadowLights retain schema <= 6 registered/visible flag semantics; they may include zero intensity or affects-world=false components."));
    Result->SetBoolField(TEXT("view_estimate_available"), Snapshot.bHasView && Snapshot.bHasProjection);
    Result->SetNumberField(TEXT("total"), Snapshot.Coverage.Lights);
    Result->SetNumberField(TEXT("enabled"), Snapshot.Coverage.EnabledLights);
    Result->SetNumberField(TEXT("enabled_with_shadow_flag"), Snapshot.Coverage.EnabledShadowLights);
    auto Estimate = [&](const TCHAR* Name, int32 Value, bool Available)
    {
        if (Available) Result->SetNumberField(Name, Value);
        else Result->SetField(Name, MakeShared<FJsonValueNull>());
    };
    Estimate(TEXT("view_candidates"), Snapshot.Coverage.LightViewCandidates, Snapshot.bHasView && Snapshot.bHasProjection);
    Estimate(TEXT("shadow_view_candidates"), Snapshot.Coverage.ShadowViewCandidates, Snapshot.bHasView && Snapshot.bHasProjection);
    Estimate(TEXT("enabled_bounds_containing_camera"), Snapshot.Coverage.CameraLightBounds, Snapshot.bHasView);
    for (const TCHAR* Name : {TEXT("actual_rendered_lights"), TEXT("local_lighting_gpu_ms"),
        TEXT("shadow_gpu_ms"), TEXT("lumen_gpu_ms"), TEXT("volumetric_fog_gpu_ms")})
        Result->SetField(Name, MakeShared<FJsonValueNull>());
    auto Settings = MakeShared<FJsonObject>();
    for (const auto& Pair : Snapshot.LightingCVars)
    {
        if (Pair.Value == TEXT("未知")) Settings->SetField(Pair.Key, MakeShared<FJsonValueNull>());
        else Settings->SetStringField(Pair.Key, Pair.Value);
    }
    Result->SetObjectField(TEXT("cvar_snapshot"), Settings);
    Result->SetStringField(TEXT("cvar_contract"), TEXT("Game-thread values at scene scan; not proof that a GPU pass executes. Per-light/post-process/platform overrides may apply. Dungeon Optimize applies on next generation, RoomCulling updates at runtime."));
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (const auto& L : Snapshot.Lights)
    {
        auto Row = MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("component"), L.ObjectPath);
        Row->SetStringField(TEXT("label"), L.Label);
        Row->SetStringField(TEXT("type"), L.Type);
        Row->SetStringField(TEXT("mobility"), L.Mobility);
        Row->SetStringField(TEXT("module"), L.Module);
        Row->SetStringField(TEXT("role"), L.Role);
        Row->SetStringField(TEXT("intensity_units"), L.IntensityUnits);
        Row->SetNumberField(TEXT("intensity"), L.Intensity);
        Row->SetArrayField(TEXT("position_cm"), {MakeShared<FJsonValueNumber>(L.Position.X), MakeShared<FJsonValueNumber>(L.Position.Y), MakeShared<FJsonValueNumber>(L.Position.Z)});
        Row->SetNumberField(TEXT("radius_cm"), L.RadiusCm);
        if (Snapshot.bHasView && L.bLocal) Row->SetNumberField(TEXT("distance_cm"), L.DistanceCm);
        else Row->SetField(TEXT("distance_cm"), MakeShared<FJsonValueNull>());
        Row->SetNumberField(TEXT("max_draw_distance_cm"), L.MaxDrawDistanceCm);
        Row->SetNumberField(TEXT("effective_max_draw_distance_cm"), L.EffectiveMaxDrawDistanceCm);
        Row->SetNumberField(TEXT("fade_range_cm"), L.FadeRangeCm);
        Row->SetNumberField(TEXT("outer_cone_degrees"), L.OuterConeDegrees);
        Row->SetNumberField(TEXT("volumetric_scattering"), L.VolumetricScattering);
        Row->SetNumberField(TEXT("ray_traced_shadow_mode"), L.RayTracedShadowMode);
        Row->SetBoolField(TEXT("registered"), L.bRegistered);
        Row->SetBoolField(TEXT("visible_flags"), L.bVisibleFlag);
        Row->SetBoolField(TEXT("affects_world"), L.bAffectsWorld);
        Row->SetBoolField(TEXT("enabled"), L.bEnabled);
        Row->SetBoolField(TEXT("positive_computed_brightness"), L.bPositiveBrightness);
        Row->SetBoolField(TEXT("cast_shadows"), L.bCastShadows);
        Row->SetBoolField(TEXT("cast_volumetric_shadow"), L.bCastVolumetricShadow);
        if (Snapshot.bHasView)
        {
            Row->SetBoolField(TEXT("within_draw_distance"), L.bWithinDrawDistance);
            Row->SetBoolField(TEXT("camera_inside_spherical_bounds"), L.bCameraInsideBounds);
        }
        else
        {
            Row->SetField(TEXT("within_draw_distance"), MakeShared<FJsonValueNull>());
            Row->SetField(TEXT("camera_inside_spherical_bounds"), MakeShared<FJsonValueNull>());
        }
        if (Snapshot.bHasView && Snapshot.bHasProjection)
        {
            Row->SetBoolField(TEXT("frustum_bounds_candidate"), L.bFrustumCandidate);
            Row->SetBoolField(TEXT("view_candidate"), L.bViewCandidate);
        }
        else
        {
            Row->SetField(TEXT("frustum_bounds_candidate"), MakeShared<FJsonValueNull>());
            Row->SetField(TEXT("view_candidate"), MakeShared<FJsonValueNull>());
        }
        Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    Result->SetArrayField(TEXT("lights"), Rows);
    return Result;
}

TSharedRef<FJsonObject> IconCountsJson(const FFPSIconActions& Counts)
{
    const TCHAR* Names[] = {TEXT("requests"),TEXT("cache_hits"),TEXT("pending_hits"),TEXT("failed_recipe_hits"),
        TEXT("queued"),TEXT("completed"),TEXT("failed"),TEXT("deferred")};
    auto Result = MakeShared<FJsonObject>();
    for (int32 Index = 0; Index < static_cast<int32>(EFPSIconAction::Count); ++Index)
        Result->SetNumberField(Names[Index], static_cast<double>(Counts.Values[Index]));
    return Result;
}

TSharedRef<FJsonObject> RecordedFrameJson(const FFPSRecordedFrame& Frame)
{
    auto Row = MakeShared<FJsonObject>();
    Row->SetStringField(TEXT("engine_frame_id"), LexToString(Frame.FrameId));
    Row->SetNumberField(TEXT("start_monotonic_seconds"), Frame.StartSeconds);
    Row->SetNumberField(TEXT("end_monotonic_seconds"), Frame.Seconds);
    Row->SetNumberField(TEXT("frame_ms"), Frame.FrameMs);
    Row->SetBoolField(TEXT("paused"), Frame.bPaused);
    Row->SetBoolField(TEXT("background"), Frame.bBackground);
    const auto Timer = [&Row](const TCHAR* Name, float Ms, bool Valid)
    {
        if (Valid && FMath::IsFinite(Ms) && Ms >= 0.f) Row->SetNumberField(Name, Ms);
        else Row->SetField(Name, MakeShared<FJsonValueNull>());
    };
    Timer(TEXT("game_ms"), Frame.GameMs, Frame.GameMs > 0.f);
    Timer(TEXT("draw_ms"), Frame.DrawMs, Frame.DrawMs > 0.f);
    Timer(TEXT("rhi_ms"), Frame.RhiMs, Frame.RhiMs > 0.f);
    Timer(TEXT("gpu0_ms"), Frame.GpuMs, Frame.GpuMs > 0.f);
    Timer(TEXT("game_wait_ms"), Frame.GameWaitMs, Frame.GameMs > 0.f);
    Timer(TEXT("draw_wait_ms"), Frame.DrawWaitMs, Frame.DrawMs > 0.f);
    Timer(TEXT("game_critical_ms"), Frame.GameCriticalMs, Frame.GameMs > 0.f && Frame.GameCriticalMs > 0.f);
    Timer(TEXT("draw_critical_ms"), Frame.DrawCriticalMs, Frame.DrawMs > 0.f && Frame.DrawCriticalMs > 0.f);
    Row->SetObjectField(TEXT("icon_actions"), IconCountsJson(Frame.Icons));
    auto Actions = MakeShared<FJsonObject>();
    Actions->SetNumberField(TEXT("visibility_fields_changed"), static_cast<double>(Frame.Actions.VisibilityFlagChanges));
    Actions->SetNumberField(TEXT("weapon_rebuilds"), static_cast<double>(Frame.Actions.EquipmentRebuilds));
    Actions->SetNumberField(TEXT("outfit_rebuilds"), static_cast<double>(Frame.Actions.OutfitRebuilds));
    Actions->SetNumberField(TEXT("equipment_captures"), static_cast<double>(Frame.Actions.EquipmentCaptures));
    Actions->SetNumberField(TEXT("owner_visibility_updates"), static_cast<double>(Frame.Actions.VisibilityUpdates));
    Actions->SetNumberField(TEXT("world_visibility_updates"), static_cast<double>(Frame.Actions.WorldVisibilityUpdates));
    Row->SetObjectField(TEXT("player_body_actions"), Actions);
    return Row;
}

TSharedRef<FJsonObject> EventJson(const FFPSPerformanceEvent& Event)
{
    auto Row = MakeShared<FJsonObject>();
    Row->SetStringField(TEXT("id"), LexToString(Event.Id));
    Row->SetStringField(TEXT("parent_id"), LexToString(Event.ParentId));
    Row->SetStringField(TEXT("stage"), Event.Stage.ToString());
    Row->SetStringField(TEXT("key_or_detail"), Event.Key);
    Row->SetStringField(TEXT("start_engine_frame_id"), LexToString(Event.StartFrame));
    Row->SetStringField(TEXT("end_engine_frame_id"), LexToString(Event.EndFrame));
    Row->SetNumberField(TEXT("start_monotonic_seconds"), Event.StartSeconds);
    Row->SetNumberField(TEXT("end_monotonic_seconds"), Event.EndSeconds);
    Row->SetNumberField(TEXT("inclusive_wall_ms"), (Event.EndSeconds - Event.StartSeconds) * 1000.0);
    Row->SetBoolField(TEXT("marker"), Event.bMarker);
    Row->SetBoolField(TEXT("crosses_window_start"), Event.bCrossesWindowStart);
    Row->SetBoolField(TEXT("crosses_window_end"), Event.bCrossesWindowEnd);
    Row->SetBoolField(TEXT("parent_missing"), Event.bParentMissing);
    return Row;
}

TSharedRef<FJsonObject> HitchRecordJson(const FFPSHitchRecord& Hitch, int32 EventCapacity)
{
    auto Row = MakeShared<FJsonObject>();
    Row->SetStringField(TEXT("peak_engine_frame_id"), LexToString(Hitch.PeakFrameId));
    Row->SetNumberField(TEXT("peak_frame_ms"), Hitch.PeakMs);
    TArray<TSharedPtr<FJsonValue>> Context, ContextEvents;
    int32 Before = 0, After = 0;
    for (const auto& Frame : Hitch.Frames)
    {
        Context.Add(MakeShared<FJsonValueObject>(RecordedFrameJson(Frame)));
        Before += Frame.FrameId < Hitch.PeakFrameId ? 1 : 0;
        After += Frame.FrameId > Hitch.PeakFrameId ? 1 : 0;
    }
    Row->SetNumberField(TEXT("preceding_frames_captured"), Before);
    Row->SetNumberField(TEXT("following_frames_captured"), After);
    Row->SetBoolField(TEXT("frame_context_complete"), Before == 2 && After == 2);
    Row->SetArrayField(TEXT("context_frames"), Context);
    Row->SetBoolField(TEXT("events_capacity_limited"), Hitch.bEventsCapacityLimited);
    Row->SetNumberField(TEXT("event_capacity"), EventCapacity);
    Row->SetNumberField(TEXT("active_scopes_at_context_end"), Hitch.ActiveScopesAtContextEnd);
    TSet<uint64> Ids;
    for (const auto& Event : Hitch.Events) Ids.Add(Event.Id);
    for (auto Event : Hitch.Events)
    {
        Event.bCrossesWindowStart = Event.StartSeconds < Hitch.Frames[0].StartSeconds;
        Event.bCrossesWindowEnd = Event.EndSeconds > Hitch.Frames.Last().Seconds;
        Event.bParentMissing = Event.ParentId != 0 && !Ids.Contains(Event.ParentId);
        ContextEvents.Add(MakeShared<FJsonValueObject>(EventJson(Event)));
    }
    Row->SetArrayField(TEXT("events"), ContextEvents);
    return Row;
}

void AddRecordedDetails(const TSharedRef<FJsonObject>& Root, const FFPSPerformanceSnapshot& Snapshot)
{
    Root->SetStringField(TEXT("session_id"), Snapshot.SessionId);
    Root->SetStringField(TEXT("capture_generation"), LexToString(Snapshot.CaptureGeneration));
    Root->SetNumberField(TEXT("snapshot_monotonic_seconds"), Snapshot.SnapshotSeconds);
    Root->SetNumberField(TEXT("window_start_monotonic_seconds"), Snapshot.WindowStartSeconds);
    Root->SetNumberField(TEXT("window_end_monotonic_seconds"), Snapshot.Budget.LatestSampleSeconds);
    Root->SetNumberField(TEXT("hitch_threshold_ms"), Snapshot.HitchThresholdMs);
    if (!Snapshot.Frames.IsEmpty()) Root->SetStringField(TEXT("peak_engine_frame_id"), LexToString(Snapshot.Budget.PeakFrameId));
    Root->SetStringField(TEXT("frame_identity"), TEXT("session_id + engine_frame_id; generation changes when samples are cleared; peak ties select earliest frame"));
    Root->SetStringField(TEXT("raw_timer_contract"), TEXT("Values observed at this frame boundary, not same-frame CPU/GPU attribution; null means unavailable"));
    auto Alignment = MakeShared<FJsonObject>();
    Alignment->SetStringField(TEXT("status"), TEXT("independently_published_unaligned"));
    Alignment->SetStringField(TEXT("game_source"), TEXT("Interval between viewport draw entries, not OnEndFrame boundaries"));
    Alignment->SetStringField(TEXT("draw_source"), TEXT("Slate PresentWindow_RenderThread publication; may contain editor/other windows"));
    Alignment->SetStringField(TEXT("gpu_source"), TEXT("Delayed GPU0 result"));
    Alignment->SetBoolField(TEXT("same_frame_attribution_available"), false);
    Alignment->SetField(TEXT("source_frame_id"), MakeShared<FJsonValueNull>());
    Alignment->SetField(TEXT("publication_monotonic_seconds"), MakeShared<FJsonValueNull>());
    Alignment->SetStringField(TEXT("interpretation"), TEXT("Source identity/freshness unavailable; do not sum columns, infer freshness from repeated values, or apply a fixed frame offset. Project scopes use recorded monotonic intervals."));
    Root->SetObjectField(TEXT("thread_timer_alignment"), Alignment);
    auto Phases = MakeShared<FJsonObject>();
    Phases->SetStringField(TEXT("world"), TEXT("World.Tick covers the current World's tick delegates, not the entire engine tick"));
    Phases->SetStringField(TEXT("viewport"), TEXT("Viewport.Draw covers current GameViewportClient OnBeginDraw to OnEndDraw on the game thread, not GPU execution"));
    Phases->SetStringField(TEXT("slate"), TEXT("Slate.TickAndDrawWidgets covers process-wide OnPreTick to OnPostTick, including other editor windows and nested work; excludes platform/input tick and renderer resource release before OnPreTick"));
    Phases->SetStringField(TEXT("core_ticker"), TEXT("Engine.CoreTickerBoundary is an instant in the registered core ticker callback. In the normal engine loop it follows FFrameEndSync, but the interval before it also includes RHI work, cleanup and other callbacks. It is not an isolated wait measurement."));
    Phases->SetStringField(TEXT("interpretation"), TEXT("Use monotonic intervals, retain multiple invocations per frame and nested scopes; missing scope/marker means unobserved, not zero. Gaps are unattributed wall time; never add overlapping scopes."));
    Root->SetObjectField(TEXT("phase_observation_contract"), Phases);
    Root->SetStringField(TEXT("capture_lifetime"), TEXT("Current World only; clear/restart resets history. Travel destroys this collector: cross-World loading intervals and prior World histories are not retained."));
    const bool bHasIconWindow = Snapshot.IconTask.bAvailable && !Snapshot.Frames.IsEmpty();
    Root->SetBoolField(TEXT("window_icon_actions_available"), bHasIconWindow);
    auto IconActions = bHasIconWindow ? IconCountsJson(Snapshot.IconActions) : MakeShared<FJsonObject>();
    if (!bHasIconWindow) IconActions->SetStringField(TEXT("status"),TEXT("unknown/no source or complete frame window"));
    Root->SetObjectField(TEXT("window_icon_actions"), IconActions);

    TArray<TSharedPtr<FJsonValue>> Frames, HitchIds;
    for (const auto& Frame : Snapshot.Frames)
    {
        auto Row = RecordedFrameJson(Frame);
        Frames.Add(MakeShared<FJsonValueObject>(Row));
        if (Frame.FrameMs >= Snapshot.HitchThresholdMs) HitchIds.Add(MakeShared<FJsonValueString>(LexToString(Frame.FrameId)));
    }
    Root->SetArrayField(TEXT("raw_frames"), Frames);
    Root->SetArrayField(TEXT("hitch_engine_frame_ids"), HitchIds);
    auto Severity = MakeShared<FJsonObject>();
    Severity->SetStringField(TEXT("contract"), TEXT("Cumulative counts in raw_frames; categories overlap and must not be added; empty raw_frames means no observation"));
    Severity->SetNumberField(TEXT("over_target_budget_ms"), 1000.f / Snapshot.TargetFps);
    Severity->SetNumberField(TEXT("over_target_budget_frames"), Snapshot.OverBudgetFrames);
    Severity->SetNumberField(TEXT("over_slow_threshold_ms"), Snapshot.SlowFrameThresholdMs);
    Severity->SetNumberField(TEXT("over_slow_threshold_frames"), Snapshot.SlowFrames);
    Severity->SetNumberField(TEXT("at_least_50_ms_frames"), Snapshot.FramesAtLeast50Ms);
    Severity->SetNumberField(TEXT("at_least_100_ms_frames"), Snapshot.FramesAtLeast100Ms);
    Root->SetObjectField(TEXT("frame_severity"), Severity);
    TArray<TSharedPtr<FJsonValue>> SlowestIds;
    for (const auto& Frame : Snapshot.SlowestFrames) SlowestIds.Add(MakeShared<FJsonValueString>(LexToString(Frame.FrameId)));
    Root->SetArrayField(TEXT("slowest_engine_frame_ids"), SlowestIds);
    Root->SetStringField(TEXT("slowest_frames_contract"), TEXT("Up to three longest raw_frames, regardless of hitch threshold; ties prefer earlier frame"));
    auto History = MakeShared<FJsonObject>();
    History->SetNumberField(TEXT("threshold_ms"), 50);
    History->SetNumberField(TEXT("capacity"), Snapshot.HitchHistoryCapacity);
    History->SetStringField(TEXT("overwritten_since_clear"), LexToString(Snapshot.HitchesOverwritten));
    History->SetStringField(TEXT("contract"), TEXT("Recent >=50ms frames since clear/restart, oldest first, separate from rolling window. Context is up to two previous and two following frames; deduplicate by session+frame ID. Events cover context, not exclusive cause. Active scopes may be absent; flags refer to context interval."));
    TArray<TSharedPtr<FJsonValue>> HistoryRows;
    for (const auto& Hitch : Snapshot.RecentHitches)
    {
        HistoryRows.Add(MakeShared<FJsonValueObject>(HitchRecordJson(Hitch, Snapshot.HitchEventCapacity)));
    }
    History->SetArrayField(TEXT("entries"), HistoryRows);
    Root->SetObjectField(TEXT("recent_hitch_history"), History);
    auto Worst = MakeShared<FJsonObject>();
    Worst->SetNumberField(TEXT("capacity"), Snapshot.WorstHitchCapacity);
    Worst->SetNumberField(TEXT("threshold_ms"), 50);
    Worst->SetStringField(TEXT("contract"), TEXT("Largest >=50ms frames since clear/restart, descending duration; ties prefer earlier frames. All peak IDs are listed. Entries contain only contexts absent from recent_hitch_history; resolve other IDs there, using session+frame ID. Independent of rolling-window eviction; current World lifetime only."));
    TArray<TSharedPtr<FJsonValue>> WorstIds, WorstRows;
    for (const auto& Hitch : Snapshot.WorstHitches)
    {
        WorstIds.Add(MakeShared<FJsonValueString>(LexToString(Hitch.PeakFrameId)));
        if (!Snapshot.RecentHitches.ContainsByPredicate([&Hitch](const auto& Recent) { return Recent.PeakFrameId == Hitch.PeakFrameId; }))
            WorstRows.Add(MakeShared<FJsonValueObject>(HitchRecordJson(Hitch, Snapshot.HitchEventCapacity)));
    }
    Worst->SetArrayField(TEXT("peak_engine_frame_ids"), WorstIds);
    Worst->SetArrayField(TEXT("entries"), WorstRows);
    Root->SetObjectField(TEXT("worst_hitch_history"), Worst);
    Root->SetBoolField(TEXT("events_capacity_limited_in_window"), Snapshot.bEventsCapacityLimited);
    Root->SetStringField(TEXT("events_overwritten_since_clear"), LexToString(Snapshot.EventsOverwritten));
    Root->SetNumberField(TEXT("events_discarded_at_recording_boundary"), Snapshot.EventsDiscardedAtBoundary);
    Root->SetNumberField(TEXT("active_events_at_snapshot"), Snapshot.ActiveEventCount);
    Root->SetStringField(TEXT("event_contract"), TEXT("Completed game-thread scopes overlapping the sampled frame interval; inclusive wall time, not exclusive CPU. Nested durations must not be added. Markers are instants. Boundary flags retain full event duration; missing parents are explicit. Active scopes are not yet exported."));
    TArray<TSharedPtr<FJsonValue>> ScopeCoverage;
    for (const TCHAR* Stage : {TEXT("Icon.Tick"),TEXT("Icon.Prepare"),TEXT("Icon.CreateStudio"),TEXT("Icon.CreateRig"),
        TEXT("Icon.InitializeVisuals"),TEXT("Icon.AssemblyAndBounds"),TEXT("Icon.SkinnedBounds"),TEXT("Icon.MeleeAssembly"),
        TEXT("Pickup.CreateRig"),TEXT("Pickup.Warm"),TEXT("Pickup.BuildWeapon"),TEXT("Pickup.InitializeVisuals"),
        TEXT("Icon.CaptureSubmit"),TEXT("Icon.FinalCaptureSubmit"),TEXT("Icon.ReadbackSubmit"),TEXT("Icon.ReadbackPoll"),TEXT("Icon.PublishTexture"),TEXT("Icon.NotifyReady"),
        TEXT("Panel.Snapshot"),TEXT("Panel.ExportSubmit"),TEXT("Panel.UiUpdate"),TEXT("World.Tick"),
        TEXT("Viewport.Draw"),TEXT("Slate.TickAndDrawWidgets"),TEXT("Icon.MaterialReadinessSubmit"),
        TEXT("PlayerBody.EquipmentCapture"),TEXT("PlayerBody.OwnerVisibility"),TEXT("PlayerBody.WorldVisibility"),
        TEXT("Dungeon.RoomLighting")}) ScopeCoverage.Add(MakeShared<FJsonValueString>(Stage));
    Root->SetArrayField(TEXT("instrumented_scope_names"), ScopeCoverage);
    TArray<TSharedPtr<FJsonValue>> MarkerCoverage;
    for (const TCHAR* Stage : {TEXT("Engine.CoreTickerBoundary"),TEXT("Icon.WaitState"),TEXT("Icon.BoundsCacheHit"),TEXT("Icon.Deferred"),TEXT("Icon.Completed"),TEXT("Icon.Failed"),TEXT("Icon.ReadbackReady")})
        MarkerCoverage.Add(MakeShared<FJsonValueString>(Stage));
    Root->SetArrayField(TEXT("instrumented_marker_names"), MarkerCoverage);
    TArray<TSharedPtr<FJsonValue>> Events;
    for (const auto& Event : Snapshot.Events)
    {
        auto Row = EventJson(Event);
        Events.Add(MakeShared<FJsonValueObject>(Row));
    }
    Root->SetArrayField(TEXT("events"), Events);
    auto Task = MakeShared<FJsonObject>();
    Task->SetBoolField(TEXT("available"), Snapshot.IconTask.bAvailable);
    Task->SetStringField(TEXT("scope"), TEXT("Current GameInstance state at observed_monotonic_seconds, separate from the frame window; ages include waiting, not CPU cost"));
    if (Snapshot.IconTask.bAvailable)
    {
        const auto& State = Snapshot.IconTask;
        Task->SetNumberField(TEXT("observed_monotonic_seconds"), State.ObservedSeconds);
        Task->SetNumberField(TEXT("queue_length"), State.Queued);
        Task->SetNumberField(TEXT("cached_recipes"), State.Cached);
        Task->SetNumberField(TEXT("failed_recipes"), State.FailedRecipes);
        Task->SetStringField(TEXT("current_recipe"), State.Key);
        Task->SetNumberField(TEXT("stage"), State.Stage);
        Task->SetStringField(TEXT("stage_contract"), TEXT("0 select eligible job/request resources or retry cooldown; 1 initial warmup/capture; 2 independent readiness polling/final capture; 3 async GPU readback/worker conversion/texture publication; 4 async asset load; 5 preparation slices. Queue length 0 is idle. Skin bounds use a 1.5ms cooperative budget, polled every 512 vertices, not a hard frame-time limit."));
        Task->SetNumberField(TEXT("cooling_down_recipes"), State.CoolingDownRecipes);
        Task->SetNumberField(TEXT("next_job_eligible_in_seconds"), State.NextEligibleSeconds);
        Task->SetStringField(TEXT("queue_policy"), TEXT("Confirmed resource blockers yield after 2 wall seconds if another job is eligible; attempt limit 10 seconds; retries cool down 2/4/6/8 seconds. Jobs in async readback do not rotate; readback/conversion timeout fails after 10 seconds. Eligibility is retry time, not a guarantee that resources are ready."));
        Task->SetStringField(TEXT("readback_state"), State.ReadbackState);
        Task->SetNumberField(TEXT("readback_age_seconds"), State.ReadbackAgeSeconds);
        if (State.ReadbackCopyMs >= 0.0) Task->SetNumberField(TEXT("readback_copy_render_cpu_ms"), State.ReadbackCopyMs);
        else Task->SetField(TEXT("readback_copy_render_cpu_ms"), MakeShared<FJsonValueNull>());
        if (State.ReadbackConversionMs >= 0.0) Task->SetNumberField(TEXT("readback_conversion_worker_ms"), State.ReadbackConversionMs);
        else Task->SetField(TEXT("readback_conversion_worker_ms"), MakeShared<FJsonValueNull>());
        Task->SetStringField(TEXT("readback_timing_contract"), TEXT("Age includes queued/GPU/worker waiting and is not CPU time. Copy is render-thread CPU staging read/copy; conversion is worker CPU wall time. Null means unfinished/unavailable; idle has no active readback. Icon.ReadbackReady preserves these values in a completion marker; they are not nested game-thread scopes or same-frame GPU time."));
        Task->SetStringField(TEXT("wait_reason"), State.WaitReason.IsNone()?TEXT("none"):State.WaitReason.ToString());
        Task->SetStringField(TEXT("wait_resource"), State.WaitResource);
        Task->SetNumberField(TEXT("wait_age_seconds"), State.WaitAgeSeconds);
        Task->SetBoolField(TEXT("material_check_pending"), State.bMaterialCheckPending);
        Task->SetStringField(TEXT("wait_contract"), TEXT("Last observed blocker and its duration; material_check_pending identifies an unfinished async query, preserving the last known material blocker. The first blocking resource is reported, not a complete dependency list. Ages are wall time, not CPU cost."));
        Task->SetNumberField(TEXT("readiness_polls_this_attempt"), State.ReadinessPolls);
        Task->SetNumberField(TEXT("capture_submissions_this_attempt"), State.CaptureSubmissions);
        Task->SetNumberField(TEXT("deferred_attempts_this_recipe"), State.DeferredAttempts);
        Task->SetBoolField(TEXT("bounds_cache_hit_this_attempt"), State.bBoundsCacheHit);
        Task->SetNumberField(TEXT("request_age_seconds"), State.RequestAgeSeconds);
        Task->SetNumberField(TEXT("attempt_age_seconds"), State.AttemptAgeSeconds);
        Task->SetNumberField(TEXT("failure_detail_capacity"), State.FailureCapacity);
        Task->SetBoolField(TEXT("failure_details_capacity_limited"), State.bFailureDetailsLimited);
        Task->SetStringField(TEXT("failure_details_scope"), TEXT("Recent failed recipes in this GameInstance, not restricted to the performance window/generation. Clearing samples does not retry failures or clear catalog fallback. Reasons are limited to 2048 characters with explicit truncation."));
        TArray<TSharedPtr<FJsonValue>> Failures;
        for (const auto& Failure : State.RecentFailures)
        {
            auto Row = MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("recipe"), Failure.Recipe);
            Row->SetStringField(TEXT("stage"), Failure.Stage.ToString());
            Row->SetStringField(TEXT("resource"), Failure.Resource);
            Row->SetStringField(TEXT("reason"), Failure.Reason);
            Row->SetBoolField(TEXT("reason_truncated"), Failure.bReasonTruncated);
            Row->SetStringField(TEXT("occurred_at_utc"), Failure.OccurredAtUtc);
            Row->SetStringField(TEXT("engine_frame_id"), LexToString(Failure.FrameId));
            Row->SetNumberField(TEXT("monotonic_seconds"), Failure.Seconds);
            Row->SetBoolField(TEXT("catalog_fallback_active"), true);
            Failures.Add(MakeShared<FJsonValueObject>(Row));
        }
        Task->SetArrayField(TEXT("recent_failures"), Failures);
    }
    Root->SetObjectField(TEXT("icon_task_at_snapshot"), Task);
    if (!Snapshot.ExportRequestedAtUtc.IsEmpty())
    {
        Root->SetStringField(TEXT("export_requested_at_utc"), Snapshot.ExportRequestedAtUtc);
        Root->SetStringField(TEXT("export_submitted_engine_frame_id"), LexToString(Snapshot.ExportSubmittedFrame));
    }
}
}

bool UFPSPerformanceMetricsSubsystem::ExportSnapshot(const FFPSPerformanceSnapshot& Snapshot, FString& OutPath)
{
    const TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetNumberField(TEXT("schema_version"), 9);
    AddRecordedDetails(Root, Snapshot);
    Root->SetNumberField(TEXT("event_capacity"), MaxEvents);
    Root->SetStringField(TEXT("icon_counter_scope"), TEXT("Current GameInstance icon request/completion paths, deltas between sampled frame boundaries; cache hits count Request hits, not paint-time Find lookups"));
    Root->SetStringField(TEXT("captured_at_utc"), Snapshot.CapturedAtUtc);
    Root->SetStringField(TEXT("environment"), Snapshot.Environment);
    Root->SetStringField(TEXT("frame_source"), TEXT("OnEndFrame monotonic wall clock; no delta clamping"));
    Root->SetStringField(TEXT("timing_scope"), TEXT("Engine process, includes editor/other views in PIE; independently published timers, not same-frame attribution"));
    Root->SetStringField(TEXT("gpu_source"), TEXT("RHIGetGPUFrameCycles(0); delayed results; zero is unavailable, not zero cost"));
    Root->SetStringField(TEXT("counter_scope"), TEXT("Current World; instrumented player-body paths only; changed fields are not render-state recreates"));
    Root->SetStringField(TEXT("rank_contract"), TEXT("Source geometry complexity: (triangles + .1 * vertices + 2500 * material slots) * total instances; not measured time"));
    Root->SetStringField(TEXT("percentile_method"), TEXT("nearest-rank: sorted[ceil(p*n)-1]"));
    Root->SetStringField(TEXT("unavailable"), TEXT("CPU subsystems outside instrumented scopes, detailed engine waits, aligned thread/GPU source frames, GPU passes, actual animation evaluations, actual rendered LOD/Nanite/instances/occlusion, Niagara particles, memory, loading durations"));
    Root->SetStringField(TEXT("phase_contract"), TEXT("Slate.WindowPaint covers process-wide window Paint only, not prepass, buffer acquisition or GPU execution; Slate minus Paint is unattributed, not pure wait. GC is process-wide; sync load / async flush starts are markers, not durations."));
#if WITH_SLATE_DEBUGGING
    Root->SetBoolField(TEXT("window_paint_instrumentation_available"), true);
#else
    Root->SetBoolField(TEXT("window_paint_instrumentation_available"), false);
#endif
    const auto ObserverJson = [](const FFPSObserverContext& State)
    {
        auto Json = MakeShared<FJsonObject>();
        Json->SetBoolField(TEXT("known"), State.bKnown);
        if (State.bKnown)
        {
            Json->SetBoolField(TEXT("panel_open"), State.bPanelOpen);
            Json->SetBoolField(TEXT("display_frozen"), State.bFrozen);
            Json->SetNumberField(TEXT("page_index"), State.Page);
            Json->SetNumberField(TEXT("refresh_interval_ms"), State.RefreshMs);
            Json->SetNumberField(TEXT("blur_strength"), State.BlurStrength);
            Json->SetNumberField(TEXT("blur_radius"), State.BlurRadius);
        }
        return Json;
    };
    Root->SetObjectField(TEXT("observer_at_snapshot"), ObserverJson(Snapshot.ObserverAtSnapshot));
    Root->SetObjectField(TEXT("observer_at_export_request"), ObserverJson(Snapshot.ObserverAtExport));
    Root->SetStringField(TEXT("observation_cost_scope"), TEXT("Snapshot construction and UI update only; excludes Slate layout/paint and GPU UI/blur"));
    Root->SetBoolField(TEXT("recording_at_capture"), Snapshot.Budget.bRecording);
    Root->SetNumberField(TEXT("requested_window_seconds"), Snapshot.RequestedWindowSeconds);
    Root->SetNumberField(TEXT("observed_duration_seconds"), Snapshot.Budget.DurationSeconds);
    Root->SetNumberField(TEXT("sample_age_at_capture_seconds"), Snapshot.Budget.SampleAgeSeconds);
    Root->SetBoolField(TEXT("capacity_limited"), Snapshot.Budget.bCapacityLimited);
    Root->SetNumberField(TEXT("capacity_frames"), MaxSamples);
    Root->SetStringField(TEXT("first_engine_frame_id"), LexToString(Snapshot.Budget.FirstFrameId));
    Root->SetStringField(TEXT("last_engine_frame_id"), LexToString(Snapshot.Budget.LastFrameId));
    Root->SetNumberField(TEXT("paused_frames"), Snapshot.Budget.PausedFrames);
    Root->SetNumberField(TEXT("background_frames"), Snapshot.Budget.BackgroundFrames);
    Root->SetNumberField(TEXT("target_fps"), Snapshot.TargetFps);
    Root->SetNumberField(TEXT("slow_threshold_ms"), Snapshot.SlowFrameThresholdMs);
    if (Snapshot.Budget.Frame.Count > 0)
    {
        Root->SetNumberField(TEXT("window_fps"), Snapshot.Budget.Fps);
        Root->SetNumberField(TEXT("latest_frame_ms"), Snapshot.Budget.LatestFrameMs);
        Root->SetNumberField(TEXT("over_budget_fraction"), Snapshot.Budget.OverBudgetFraction);
        Root->SetNumberField(TEXT("slow_fraction"), Snapshot.Budget.SlowFrameFraction);
    }
    const TSharedRef<FJsonObject> Timings = MakeShared<FJsonObject>();
    const auto AddTiming = [&Timings](const TCHAR* Name, const FFPSMetricDistribution& D)
    {
        const TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
        Entry->SetNumberField(TEXT("valid_samples"), D.Count);
        Entry->SetStringField(TEXT("unit"), TEXT("ms"));
        if (D.Count)
        {
            Entry->SetNumberField(TEXT("average"), D.Average);
            Entry->SetNumberField(TEXT("p50"), D.P50);
            Entry->SetNumberField(TEXT("p95"), D.P95);
            Entry->SetNumberField(TEXT("p99"), D.P99);
            Entry->SetNumberField(TEXT("peak"), D.Peak);
        }
        else Entry->SetStringField(TEXT("status"), TEXT("unknown/no valid observations"));
        Timings->SetObjectField(Name, Entry);
    };
    AddTiming(TEXT("frame"), Snapshot.Budget.Frame);
    AddTiming(TEXT("game"), Snapshot.Budget.Game);
    AddTiming(TEXT("draw"), Snapshot.Budget.Draw);
    AddTiming(TEXT("rhi"), Snapshot.Budget.Rhi);
    AddTiming(TEXT("gpu0"), Snapshot.Budget.Gpu);
    AddTiming(TEXT("game_wait"), Snapshot.Budget.GameWait);
    AddTiming(TEXT("draw_wait"), Snapshot.Budget.DrawWait);
    AddTiming(TEXT("game_critical"), Snapshot.Budget.GameCritical);
    AddTiming(TEXT("draw_critical"), Snapshot.Budget.DrawCritical);
    AddTiming(TEXT("snapshot_build"), Snapshot.Budget.Scan);
    AddTiming(TEXT("ui_update_through_previous_refresh"), Snapshot.Budget.UiUpdate);
    Root->SetObjectField(TEXT("timings"), Timings);
    const TSharedRef<FJsonObject> Actions = MakeShared<FJsonObject>();
    Actions->SetNumberField(TEXT("visibility_fields_changed"), Snapshot.Actions.VisibilityFlagChanges);
    Actions->SetNumberField(TEXT("weapon_rebuilds"), Snapshot.Actions.EquipmentRebuilds);
    Actions->SetNumberField(TEXT("outfit_rebuilds"), Snapshot.Actions.OutfitRebuilds);
    Actions->SetNumberField(TEXT("equipment_captures"), Snapshot.Actions.EquipmentCaptures);
    Actions->SetNumberField(TEXT("owner_visibility_updates"), Snapshot.Actions.VisibilityUpdates);
    Actions->SetNumberField(TEXT("world_visibility_updates"), Snapshot.Actions.WorldVisibilityUpdates);
    Root->SetObjectField(TEXT("window_actions"), Actions);
    const TSharedRef<FJsonObject> Coverage = MakeShared<FJsonObject>();
#define FPS_COVERAGE(Field) Coverage->SetNumberField(TEXT(#Field), Snapshot.Coverage.Field)
    FPS_COVERAGE(SkeletalComponents); FPS_COVERAGE(SkeletalWithAsset); FPS_COVERAGE(SkeletalTickEnabled);
    FPS_COVERAGE(SkeletalLeaderFollowers); FPS_COVERAGE(TotalAssetBones); FPS_COVERAGE(AlwaysRefreshConfigured);
    FPS_COVERAGE(AlwaysPoseConfigured); FPS_COVERAGE(TickEnabledAlwaysRefresh); FPS_COVERAGE(HiddenShadowEligible);
    FPS_COVERAGE(InstancedComponents); FPS_COVERAGE(Instances); FPS_COVERAGE(DynamicMeshes);
    FPS_COVERAGE(Lights); FPS_COVERAGE(VisibleLights); FPS_COVERAGE(ShadowLights);
    FPS_COVERAGE(EnabledLights); FPS_COVERAGE(EnabledShadowLights);
    FPS_COVERAGE(PointLights); FPS_COVERAGE(SpotLights); FPS_COVERAGE(RectLights); FPS_COVERAGE(DirectionalLights);
    FPS_COVERAGE(SkyLights); FPS_COVERAGE(EnabledSkyLights); FPS_COVERAGE(RealTimeSkyCaptures);
    FPS_COVERAGE(AudioComponents); FPS_COVERAGE(PlayingAudio); FPS_COVERAGE(NiagaraComponents);
    FPS_COVERAGE(ActiveNiagara); FPS_COVERAGE(CascadeComponents); FPS_COVERAGE(CascadeParticles);
    FPS_COVERAGE(OtherPrimitives); FPS_COVERAGE(GeometryUnavailable);
#undef FPS_COVERAGE
    Root->SetObjectField(TEXT("scene_coverage"), Coverage);
    Root->SetObjectField(TEXT("lighting"), LightingJson(Snapshot));
    TArray<TSharedPtr<FJsonValue>> Skies;
    for(const auto& Sky:Snapshot.SkyLights)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("component"),Sky.ObjectPath);
        Row->SetStringField(TEXT("source"),Sky.Source);Row->SetNumberField(TEXT("intensity"),Sky.Intensity);
        Row->SetBoolField(TEXT("enabled_flags"),Sky.bEnabled);Row->SetBoolField(TEXT("real_time_capture_flag"),Sky.bRealTimeCapture);
        Row->SetBoolField(TEXT("casts_shadows_flag"),Sky.bCastsShadows);Skies.Add(MakeShared<FJsonValueObject>(Row));
    }
    Root->SetArrayField(TEXT("sky_lights_configuration"),Skies);
    TArray<TSharedPtr<FJsonValue>> DungeonReports;
    for(const FString& Json:Snapshot.DungeonGenerationReports)
    {
        TSharedPtr<FJsonObject> Report;
        if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Report)&&Report)
            DungeonReports.Add(MakeShared<FJsonValueObject>(Report));
    }
    Root->SetArrayField(TEXT("dungeon_generation"),DungeonReports);
    Root->SetBoolField(TEXT("has_view"), Snapshot.bHasView);
    Root->SetBoolField(TEXT("has_projection"), Snapshot.bHasProjection);
    Root->SetNumberField(TEXT("actors"), Snapshot.ActorCount);
    Root->SetNumberField(TEXT("components"), Snapshot.ComponentCount);
    Root->SetNumberField(TEXT("ranked_meshes"), Snapshot.RankedMeshCount);
    Root->SetNumberField(TEXT("all_rank_total"), Snapshot.AllRankTotal);
    Root->SetNumberField(TEXT("displayed_rank_total"), Snapshot.DisplayedRankTotal);
    TArray<TSharedPtr<FJsonValue>> Assets;
    for (const auto& Asset : Snapshot.MeshAssets)
    {
        auto Row = MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("asset"), Asset.Asset);
        Row->SetNumberField(TEXT("components"), Asset.Components);
        Row->SetNumberField(TEXT("instances"), Asset.Instances);
        Row->SetNumberField(TEXT("source_lod0_triangles_all_instances"), Asset.SourceLod0Triangles);
        Row->SetNumberField(TEXT("source_complexity"), Asset.SourceComplexity);
        if (Snapshot.bHasView) Row->SetNumberField(TEXT("view_eligible_components"), Asset.ViewEligibleComponents);
        if (Snapshot.bHasProjection) Row->SetNumberField(TEXT("frustum_candidate_components"), Asset.FrustumCandidates);
        Assets.Add(MakeShared<FJsonValueObject>(Row));
    }
    Root->SetArrayField(TEXT("all_mesh_asset_summary"), Assets);
    Root->SetStringField(TEXT("asset_summary_contract"), TEXT("All registered ranked mesh components before Top N; source geometry and component eligibility, not draw calls, actual LOD, occlusion or GPU cost."));
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (const FFPSComponentCost& Cost : Snapshot.Costs)
    {
        const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("component"), Cost.ObjectPath);
        Row->SetStringField(TEXT("class"), Cost.ClassName);
        Row->SetStringField(TEXT("label"), Cost.Label);
        Row->SetStringField(TEXT("asset_or_detail"), Cost.Detail);
        Row->SetStringField(TEXT("geometry_source"), Cost.bDynamicGeometry ? TEXT("current CPU mesh") : TEXT("asset LOD0/fallback"));
        Row->SetNumberField(TEXT("triangles_per_instance"), Cost.Triangles);
        Row->SetNumberField(TEXT("vertices_per_instance"), Cost.Vertices);
        Row->SetNumberField(TEXT("material_slots"), Cost.MaterialSlots);
        Row->SetNumberField(TEXT("total_instances"), Cost.Instances);
        Row->SetNumberField(TEXT("rank"), Cost.Rank);
        Row->SetNumberField(TEXT("share_of_all_mesh_rank"), Cost.ShareOfAll);
        Row->SetNumberField(TEXT("relative_to_top_rank"), Cost.ShareOfTop);
        Row->SetBoolField(TEXT("has_nanite_asset_data"), Cost.bHasNaniteData);
        if (Cost.ForcedLodModel >= 0)
        {
            Row->SetNumberField(TEXT("forced_lod_model"), Cost.ForcedLodModel);
            if (Cost.ForcedLodModel > 0) Row->SetNumberField(TEXT("forced_lod_index"), Cost.ForcedLodModel - 1);
            else Row->SetField(TEXT("forced_lod_index"), MakeShared<FJsonValueNull>());
            Row->SetBoolField(TEXT("override_min_lod"), Cost.bOverrideMinLod);
            Row->SetNumberField(TEXT("component_min_lod"), Cost.ComponentMinLod);
        }
        Row->SetField(TEXT("actual_rendered_lod"), MakeShared<FJsonValueNull>());
        Row->SetBoolField(TEXT("component_visible_flags"), Cost.bVisible);
        Row->SetBoolField(TEXT("view_visibility_known"), Cost.bViewVisibilityKnown);
        if (Cost.bViewVisibilityKnown) Row->SetBoolField(TEXT("view_visible_flags"), Cost.bVisibleToView);
        Row->SetBoolField(TEXT("has_frustum"), Cost.bHasFrustum);
        if (Cost.bHasFrustum) Row->SetBoolField(TEXT("bounds_intersect_frustum"), Cost.bOnScreen);
        Row->SetBoolField(TEXT("casts_shadow_flag"), Cost.bCastsShadow);
        if (Cost.bViewVisibilityKnown) Row->SetBoolField(TEXT("hidden_shadow_eligible"), Cost.bHiddenShadowEligible);
        TArray<TSharedPtr<FJsonValue>> Lods;
        for (int64 Count : Cost.LODTriangles) Lods.Add(MakeShared<FJsonValueNumber>(Count));
        Row->SetArrayField(TEXT("asset_lod_triangles"), Lods);
        Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    Root->SetArrayField(TEXT("displayed_meshes"), Rows);
    FString Json;
    if (!FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Json))) return false;
    const FString Directory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("PerformanceReports"));
    if (!IFileManager::Get().MakeDirectory(*Directory, true)) return false;
    OutPath = Directory / FString::Printf(TEXT("performance-%s-%s.json"),
        *FDateTime::UtcNow().ToString(TEXT("%Y%m%d-%H%M%S")), *FGuid::NewGuid().ToString(EGuidFormats::Digits));
    return FFileHelper::SaveStringToFile(Json, *OutPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

void UFPSPerformanceMetricsSubsystem::ExportSnapshotAsync(const FFPSPerformanceSnapshot& Snapshot,
    TFunction<void(bool, const FString&, double)> Completion)
{
    const double Submitted = FPlatformTime::Seconds();
    FFPSPerformanceSnapshot Copy = Snapshot;
    Copy.ExportRequestedAtUtc = FDateTime::UtcNow().ToIso8601();
    Copy.ExportSubmittedFrame = GFrameCounter;
    // The worker serializes captured values only, never live actors/components/widgets.
    for (auto& Cost : Copy.Costs) { Cost.Owner.Reset(); Cost.Component.Reset(); }
    Async(EAsyncExecution::ThreadPool, [Copy = MoveTemp(Copy), Completion = MoveTemp(Completion), Submitted]() mutable
    {
        FString Path;
        const bool bSaved = ExportSnapshot(Copy, Path);
        const double ElapsedMs = (FPlatformTime::Seconds() - Submitted) * 1000.0;
        AsyncTask(ENamedThreads::GameThread, [Completion = MoveTemp(Completion), bSaved, Path = MoveTemp(Path), ElapsedMs]() mutable
        {
            Completion(bSaved, Path, ElapsedMs);
        });
    });
}
