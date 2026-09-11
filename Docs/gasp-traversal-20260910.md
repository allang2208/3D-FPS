# Official GASP traversal integration work

## Verified source

- Epic Games Game Animation Sample, Fab listing `880e319a-a59e-4ed2-b268-b32dac7fa016`; ownership confirmed in the launcher UI.
- Launcher downloaded `GameAnimationSample_5.8`; manifest version `5.8.2-56817199+++UE5+Release-5.8-Windows`. Installed engine is `5.8.2-56702186`.
- Independent local project: `D:/FPS3D/游戏动画示例/GameAnimationSample.uproject`.
- Launcher download completed with `ProcessSuccess: TRUE`, `ErrorCode: OK` on 2026-09-10. Original assets remain outside the FPS Content tree.
- No purchased product, character replacement or source binary publication was performed.

## Actual animation inspection

`Tools/AssetPipeline/inspect_gasp_traversal.py` reads the sample asset registry, animation durations, skeleton and notify timing. Output: `SourceAssets/GASPTraversal20260910/official_sample_inventory.json`, 170 related assets. `AC_TraversalLogic` is an official Blueprint component. The sample also includes Mover and other locomotion infrastructure; copying all project configuration would change our existing movement assumptions.

Three original sequences were exported with the official preview mesh using `export_gasp_reference.py`, then rendered in Blender using `render_gasp_reference.py`. FBX and editable Blender reference scenes are under `SourceAssets/GASPTraversal20260910/Reference`. These renders are the official mannequin, not our FPS arms and not runtime acceptance.

- Standing vault: `M_Neutral_Traversal_Vault_1_0_stand_F_Lfoot`, original sequence duration about 2.5667 seconds, 78 sampled keys. Hands reach forward, plant on the edge, the torso pitches forward and legs tuck before the hands release. The remaining source motion descends substantially; playing the entire root trajectory into a flat landing is unsuitable. Its montage contains a traversal blend-out window beginning around 0.7294 seconds; the current FPS must provide the transition to falling/landing.
- Standing mantle: `M_Neutral_Traversal_Mantle_1_0_stand_F_Lfoot`, original sequence duration 2 seconds. The initial leg lift and asymmetric arm motion lead into the raised pelvis and standing recovery. Root translation rises about one metre in the exported reference.
- Official montage Motion Warping and handplant notifies are present. Notify times are in the inventory JSON. The FBX export frame interval must be checked against the original sequence duration before baking a destination action; exported frame counts are not a replacement for the UE timing contract.

## FPS integration boundaries

Existing `AFPSGAMECharacter` uses CharacterMovement, a capsule-mounted camera and a camera-mounted merged weapon/arms skeletal mesh. `UFPSGunplayAnimInstance` evaluates explicit idle/aim/action sequences; it has no montage slot. A montage on the camera child does not drive CharacterMovement root motion.

The integration preserves CharacterMovement and the existing weapon animation evaluator. `FPSTraversalComponent` owns traversal lifetime. `FPSTraversalExecution.cpp` advances the capsule along the validated swept route and evaluates a separate native arms sequence on a shared action clock. This replaces the earlier proposed montage driver; no Motion Matching/Mover migration is needed. It is a single-player executor and declines networked starts.

## Native arms pipeline

The high source is `M_Neutral_Traversal_Climb_Start_2_5_stand_F_Lfoot`, 3.3333 seconds, with handplant notifies near 0.698 and 0.738 seconds. Its actual mannequin reach, grip, pull and recovery renders were inspected before adapting it.

`author_traversal_arms.py` preserves `SK_Manny_Arms_Export` geometry/weights and native arm lengths, maps the anatomical palm frame, and solves shoulder/elbow/wrist reach. The geometry SHA-256 before/after matches in `Native/authoring.json`. Clips are sampled at 60 Hz. Low vault is trimmed to 0.8 seconds to omit the source's falling tail; mantle retains 2 seconds; high climb retains 3.3333 seconds. `TraversalArms_Editable.blend`, three animation FBXs and the mesh FBX are local editable/export deliverables. These source binaries are not cleared for public redistribution.

`import_traversal_arms.py` imports under `/Game/Movement/Traversal/Native`, binds existing MI_Manny materials, and checks durations. `measure_traversal_bounds.py` measures deformed mesh bounds over all three actions with 10 cm margin. `apply_traversal_bounds.py` produces `SK_TraversalArms_AnimatedBounds` without overwriting a source mesh held open by another process. Original static viewmodel bounds incorrectly culled the moving arms; the measured bounds fix was confirmed by runtime images.

## Runtime validation

- `TraversalWorldAudit-v4.log`: 39 policy assertions and 18 independent physical-world cases pass; process exit 0.
- `TraversalRuntime-v3.log`: five actual-game cases pass, including 1 m thin-wall vault, 1 m broad-platform mantle, 1.8 m and 2 m climbs, and obstacle destruction during traversal. Missing-clip fallback, combat suppression, destination, restoration and unchanged ammo are checked.
- `Saved/TraversalRuntimeAudit/ColdSteel_TraversalRuntimeAudit_v3` contains real rendered frames. This exposed shoulder-cut visibility during mantle and a high-climb wrist entering the front face; camera and high-ledge grip offsets were adjusted and the v4 contact/recovery frames were inspected. The high-climb wrists now remain in front of the wall, and the mantle camera no longer exposes the open shoulder cut.
- `TraversalRuntime-v4.log`: six game cases pass with zero failures, adding AKM traversal, restored weapon switching, and suppression of both wheel directions during traversal. Output and preview: `Saved/TraversalRuntimeAudit/ColdSteel_TraversalRuntimeAudit_v4/traversal_runtime.gif`. Editor build `2026091112` succeeded; the runtime was launched after the build from the shared project module map.
- `TraversalSlideRegression.log`: existing slide-combat acceptance passes with zero failures, including hip fire, ADS fire, reload during slide, slide during reload, and slide-jump reload recovery. The audit uses a separate profile.
- The runtime audit requires `-TraversalRuntimeAudit -ColdSteelProfile=TraversalRuntimeAudit_<run>` and writes into that isolated profile's output directory. `-UseFixedTimeStep -FPS=60` provides frame-complete visual capture; it is not a performance measurement.
- Gameplay state checks and image acceptance are distinct. No multiplayer, arbitrary moving-object climbing, hanging, vault over a cliff, packaged build or measured FPS gain is claimed.

The first preview export failed under `-nullrhi` with a SkinnedMeshComponent MeshObject assertion. Retrying with `-AllowCommandletRendering -RenderOffscreen` succeeded with exit code 0. The read-only inventory and rendering export have separate scripts so a rendering failure does not invalidate the inventory output.
