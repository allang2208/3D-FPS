# Storm clouds and bounded rain effects (UE 5.8)

## Diagnose the first missing link

An MPC cloudiness scalar is not proof that the sky reads it. Inspect actual runtime cloud components, materials, scalar/vector parameter names, sky meshes, active directional lights and sky lights in each map. Editor actor enumeration can be empty for a World Partition map; a runtime actor/component audit is the fallback.

Keep the existing day/night clock authoritative. A Blueprint may own its sun rotation, scenario materials and light intensity while imported maps use a native controller. Apply weather overrides after that controller through tick prerequisites. Cache the unmodified baseline, distinguish it from the last weather-applied value, and never compound your own dimmed output. Restore materials, component visibility, layer properties and current clock-derived light intensity when weather clears.

Test at the end of world actor ticking. Timers can observe a light between the day/night write and a PostUpdateWork weather override. Sample with `OnWorldPostActorTick` or an equivalent ordering guarantee; use a practical float tolerance for interpolated material values. Identify the active, affecting-world directional light rather than taking the last component in an iterator.

## Cloud appearance and ownership

- Reuse a map's cloud layer; create at most one weather-owned fallback when no layer exists. Reuse MIDs and record ownership so teardown restores authored components and only destroys weather-created ones.
- A baked sunny sky can retain its sun even after the directional light is dimmed. Fade or replace that actual sky material as well as changing cloud coverage and sun-disk brightness.
- Cloud parameter semantics matter. In the engine SimpleVolumetricCloud material used in this project, positive global density bias and excessive thickness produced a flat dark slab. Preserving erosion/noise restored distinct cloud forms. Do not copy its tuning numbers to a different material without inspecting/rendering it.
- Preserve meaningful vector alpha values. Cloud albedo/control vectors may pack extra controls in alpha.
- Disable an independent material lightning timer when the weather manager already owns lightning and delayed thunder.
- Never add another sun to solve a weather problem. ForwardShadingPriority selects a preferred forward light; it does not remove a redundant light or resolve two controllers writing the same component.

## Rain, splashes and resource budgets

Niagara user spawn rate may control only one emitter. Inspect all conventional and stateless emitter handles: an extra Fountain emitter caused coarse blue particles independent of the weather rate. Verify emitter count and actual GPU particles, not only a successful SetVariable call.

Above-view rain emitters need offscreen newborn particles to survive until they fall into view. Bounds and scene-depth collision settings must match world-space motion. Use soft thin sprites, lifetime/depth fading, explicit material usage and exposure-aware highlights; validate silhouettes against both sky and ground.

Use fixed pools for surface decals, splash emitters and eaves drips. Keep placed puddles fixed in world coordinates, limit placement/revalidation traces, recheck newly built roofs, smooth wetness accumulation/drying, and cap nearby details by quality. Zero spawn rate does not imply a particle is missing: contact-only and shelter-only effects may legitimately be idle.

## Acceptance and publication

Render clear → storm → clear twice on every supported map. Check sunlight recovery, material/visibility restoration, component count, indoor shelter and a stable clock. Save matched-camera screenshots. Compile editor and game targets; run the changed runtime paths separately from packaged-cook or audio claims.

Concurrent editors, resource compilation, paging and too few frames invalidate GPU A/B comparisons. Whole-scene clear/storm times include rain and lighting, not just clouds. Publish invalid samples as diagnostic evidence only; do not claim a speedup from them.

Keep source scripts, final evidence and dependency/license records. Retire only unreferenced owned files to `trash` with path/size/SHA-256. A locked package is not authorization to close a user's editor. Source snapshots that require local Niagara graphs or licensed content must name those prerequisites and must not claim to be standalone projects.
