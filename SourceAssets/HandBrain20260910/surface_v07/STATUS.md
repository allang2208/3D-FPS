# HandBrain V07 local surface refinement

2026-09-11. Continues the V06 visible-hand pass. This is connected local tessellation and constrained surface relaxation, not a claim that every constituent hand has been anatomically retopologized into quads.

## Changes

- Body mesh: 60,926 -> 91,112 vertices; 120,876 -> 177,990 polygons. Connected subdivisions interpolate UV and deform layers. Boundary edge count remains zero.
- The 26-hand landmark field controls the refinement region. Alternating Laplacian relaxation reduces local tessellation kinks with a bounded displacement; localized knuckle/tendon support maintains the existing bony features. Maximum net surface shift: 3.763 mm.
- The 538,524-vertex bake source adds shallow joint folds and nail borders. Normal replacement is masked to 16.879% of the body UV image. V06 color, roughness, oral and other-object maps are retained; unmasked normal pixels remain exact.
- Combined FBX mesh: 114,732 vertices, six slots, 38 bones. This increases near-view geometry cost; no new LOD or packaging-performance acceptance is claimed.
- Body weight sums remain normalized after interpolation. Other three meshes retain exact skin-weight hashes/topology counts; five sampled poses for each of the five actions match V06. See `contracts_validation.json`.

## Evidence and source

- `HandBrain_Sculpt_Source.blend`: editable local surface and hidden high bake source, original rig/actions.
- `HandBrain_Refined_Baked.blend`: runtime surface with baked maps reloaded.
- `Geometry_Before.png` / `Geometry_After.png`: same-light clay comparison against V06.
- `Hands_Before.png` / `Hands_After.png`: same-light material comparison.
- `A_HandBrain_Howl_Surface.fbx`: reimported and rendered at five mouth poses plus the full three-second preview.
- Original Fab and generation provenance remains in prior V04/V05 deliveries; this pass performs no new paid generation.

## Rebuild

Run `Tools/HandBrain/build_surface_v07.py`, `bake_surface_v07.py`, `merge_surface_v07.py` (system Python 3.11 with NumPy/Pillow), `verify_surface_v07.py`, `preview_surface_compare_v07.py`, `validate_surface_v07.py`, `export_surface_v07.py`, `preview_surface_export_v07.py`, then `import_surface_mesh_v07.py`, `import_surface_materials_v07.py`, `activate_surface_v07.py`. Bake-only float attributes are removed from the export copy before joining the four meshes. Keep them in the editable source.

## Quality boundary

The comparison improves local hand surface continuity but does not eliminate all broad planar forms in the source. Occluded regions, individual thumb anatomy and the separate attack/crown pieces are not individually rebuilt in this pass. Treat full per-hand anatomical retopology as remaining work, not as completed by subdivision alone.

## UE activation and runtime — 2026-09-11 13:19

`BP_HandBrain` now references `/Game/Monsters/HandBrain/SurfaceV07/SK_HandBrain_Surface` and `A_HandBrain_Howl_Surface`; the shared skeleton and other four clips remain. See `activation.json` and the mesh/material import reports. Materials and mesh slots were force-saved with skeletal usage enabled. UE startup briefly stalled before reaching the import script and recovered without terminating other processes. Commandlets produced their completion markers; exit 1 still includes the pre-existing GameFeatureData error, not a clean-project assertion.

Fresh independent game run: **30 passed, 0 failed**, including real weapon damage, attacks, fear, death transition, corpse removal and village respawn. Capsule sweep contact gap: **-0.057 cm**. Inspected the actual howl and visible grounded corpse screenshots. `runtime/acceptance.json`, `runtime/play.log` and screenshots preserve this specific run. This does not establish exhaustive physics stability, LOD performance or packaged-game acceptance.
