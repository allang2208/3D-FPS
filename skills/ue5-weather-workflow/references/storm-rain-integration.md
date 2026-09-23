# Storm clouds and bounded rain effects (UE 5.8)

## Diagnose the first missing link

An MPC cloudiness scalar is not proof that the sky reads it. Inspect actual runtime cloud components, materials, scalar/vector parameter names, sky meshes, active directional lights and sky lights in each map. Editor actor enumeration can be empty for a World Partition map; a runtime actor/component audit is the fallback.

Keep the existing day/night clock authoritative. A Blueprint may own its sun rotation, scenario materials and light intensity while imported maps use a native controller. Apply weather overrides after that controller through tick prerequisites. Cache the unmodified baseline, distinguish it from the last weather-applied value, and never compound your own dimmed output. Restore materials, component visibility, layer properties and current clock-derived light intensity when weather clears.

Test at the end of world actor ticking. Timers can observe a light between the day/night write and a PostUpdateWork weather override. Sample with `OnWorldPostActorTick` or an equivalent ordering guarantee; use a practical float tolerance for interpolated material values. Identify the active, affecting-world directional light rather than taking the last component in an iterator.

## Cloud appearance and ownership

- Reuse a map's cloud layer; create at most one weather-owned fallback when no layer exists. Reuse MIDs and record ownership so teardown restores authored components and only destroys weather-created ones.
- A baked sunny sky can retain its sun even after the directional light is dimmed. Fade or replace that actual sky material as well as changing cloud coverage and sun-disk brightness.
- Cloud parameter semantics matter. The UE 5.8 SimpleVolumetricCloud graph multiplies its shaped density field by `Cloud_GlobalDensity` (engine default `0.008`); setting it to zero makes clear-weather clouds transparent. `Cloud_GlobalCoverage` is the separate additive layout bias (engine default `-0.2`). Use coverage, layer thickness and erosion/noise to shape sparse or overcast skies while retaining nonzero extinction. These meanings were confirmed from the loaded material graph on 2026-09-13; the former guidance describing global density as a bias was incorrect. Do not copy its tuning numbers to a different material without inspecting it.
- Preserve meaningful vector alpha values. Cloud albedo/control vectors may pack extra controls in alpha.
- Disable an independent material lightning timer when the weather manager already owns lightning and delayed thunder.
- Never add another sun to solve a weather problem. ForwardShadingPriority selects a preferred forward light; it does not remove a redundant light or resolve two controllers writing the same component.

## Canopy shadow readability

For dark outdoor shadows, read the map's sky-light baseline and exposure limits together with weather attenuation. With extended luminance range enabled, exposure min/max are EV100; equal values disable eye adaptation. Tune diffuse sky fill and local shadow exposure before increasing direct sunlight. Bound any extra eye-adaptation range and fade daytime readability compensation out with the authoritative day/night clock.

Apply map-specific gameplay corrections through an owned transient post-process component when existing maps must receive them without regeneration. Preserve authored light baselines, account for cloud-bottom occlusion as well as the sky-light weather multiplier, and avoid new per-tree shadow lights. The 2026-09-13 hills settings are an untested tuning revision documented in `Docs/Weather/hills-canopy-lighting-20260913.md`, not a measured performance or visual acceptance result.

## Rain, splashes and resource budgets

Niagara user spawn rate may control only one emitter. Inspect all conventional and stateless emitter handles: an extra Fountain emitter caused coarse blue particles independent of the weather rate. Verify emitter count and actual GPU particles, not only a successful SetVariable call.

Above-view rain emitters need offscreen newborn particles to survive until they fall into view. Bounds and scene-depth collision settings must match world-space motion. Use soft thin sprites, lifetime/depth fading, explicit material usage and exposure-aware highlights; validate silhouettes against both sky and ground.

Use fixed pools for surface decals, splash emitters and eaves drips. Keep placed puddles fixed in world coordinates, limit placement/revalidation traces, recheck newly built roofs, smooth wetness accumulation/drying, and cap nearby details by quality. Zero spawn rate does not imply a particle is missing: contact-only and shelter-only effects may legitimately be idle.

## Per-frame cost traps (2026-09-23 audit)

- A MID `SetScalarParameterValue`/`SetVectorParameterValue` enqueues a render command that invalidates the proxy's uniform expression cache (two global waits inside). Writing an unchanged value still costs the call; only write when the quantized value actually changed (`LastPushed` guard, 1/255 step), and never write a parameter no material declares — dead writes look free in a profiler until you count them.
- Component setters on cloud/light components are guarded engine-side (`MarkRenderStateDirty` only on change), so constant per-frame writes there are absorbed; do not confuse them with MID writes, which are not absorbed the same way.
- Never scan the whole world (`TActorIterator`) every frame to find level-static content (a sky-clock actor, its reflected property, cloud components, lights). Resolve once, cache weak handles (`TWeakObjectPtr` + `TWeakFieldPtr<FProperty>`), and re-scan only after the handle goes stale. The same applies to `SetActorLocation` follow logic: compare against the current location first.
- A quality CVar set to "off" must skip the work loop entirely, not just the traces: zero the pool once via a one-shot flag, then return. Integrate shared state (wetness) outside the gate if cross-quality continuity is wanted.
- Count expensive setters before optimizing: a per-second written/skipped counter logged from the tick (`WEATHER_WET_WRITES perSec=… skippedPerSec=…`) settles "did the guard work?" without A/B guessing. Single A/B runs across editors, compilation or paging are invalid evidence.
- Weapon wetness is per-MID, not MPC-driven; coverage gaps between dry/wet tables are invisible at runtime, so run `Tools/Weather/audit_weapon_wetness.ps1` after adding weapons or attachments.

## Acceptance and publication

Render clear → storm → clear twice on every supported map. Check sunlight recovery, material/visibility restoration, component count, indoor shelter and a stable clock. Save matched-camera screenshots. Compile editor and game targets; run the changed runtime paths separately from packaged-cook or audio claims.

Concurrent editors, resource compilation, paging and too few frames invalidate GPU A/B comparisons. Whole-scene clear/storm times include rain and lighting, not just clouds. Publish invalid samples as diagnostic evidence only; do not claim a speedup from them.

Keep source scripts, final evidence and dependency/license records. Retire only unreferenced owned files to `trash` with path/size/SHA-256. A locked package is not authorization to close a user's editor. Source snapshots that require local Niagara graphs or licensed content must name those prerequisites and must not claim to be standalone projects.
