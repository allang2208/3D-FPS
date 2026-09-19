# AKM replacement and gunplay animation sources

This isolated package fits the user's `D:/迅雷下载/akm.fbx` to the existing
`SK_AKM_Viewmodel` animation rig and replaces the old cubic arms with the new
WRAD-derived arms from `../ArmsReplacement/`.

## Source and material provenance

- User-provided gun FBX: 935,148 bytes; SHA-256
  `BBB7A8CF56D7ED7EF850B410933C056BB9C478F229A7576D5C585B7102D57D43`.
- `UserProvided_AKM.fbx` is an unchanged copy. The original download is untouched.
- The FBX contains 32,020 gun triangles in four separate meshes: body, bolt,
  magazine and trigger. It does not include a rig or animation.
- All 12 referenced images under `AKM.fbm` are missing from the supplied download.
  The seven candidate steel, walnut, bakelite, fabric and glove materials are
  authored PBR substitutes, not a recovery of the source artist's textures.
- WRAD arm geometry is CC0. See `../ArmsReplacement/README.md` and its retained
  author license/source files. The arms retain all three finger segments.
- The gun source supplied by the user does not include a license document.
  Existing hand/weapon animation provenance is retained from `../AKM/README.md`.

## Delivered files

- `SK_AKM_Replacement_Source.blend`: editable 82-bone combined rig, new gun,
  new gloved arms and all source/candidate actions.
- `SK_AKM_Replacement.fbx`: combined skeletal mesh.
- `A_AKM_*.fbx`: ten animation clips, listed in the export report.
- `akm_replacement_idle_001.png`: combined model render.
- `akm_replacement_ads_anchor.png`: real geometry rendered down the two sight
  anchors, with a 30 cm preview eye distance. Runtime sets its own eye distance.
- `akm_replacement_reload_empty.gif`: actual empty-reload animation render,
  sampled every two source frames at approximately 12 fps.

The final game skeletal mesh is
`/Game/Weapons/AKMReplacement/Rendering/SK_AKM_Replacement_Game`.
Its seven `*_PBR_Skinned` materials are in the same `Rendering` directory and
explicitly enable SkeletalMesh shader usage. It shares the original candidate
skeleton. The earlier `SK_AKM_Replacement` and seven PBR assets remain retained
as source packages.

Animations remain in `/Game/Weapons/AKMReplacement/`: `A_AKM_idle`, `A_AKM_aim`, `A_AKM_fire`,
`A_AKM_aim_fire`, `A_AKM_reload`, `A_AKM_reload_empty`, `A_AKM_draw`,
`A_AKM_holster`, `A_AKM_inspect`, and `A_AKM_equip`.

## Fit and animation contract

The gun uses uniform scale 0.13459, plus rigid axis conversion: source +X maps
to Blender world +Y, source +Y to world -X, and +Z stays up. The fitted rifle
is about 87.5 cm long. A separate rigid magazine offset of -1.3 cm forward and
+0.5 cm upward preserves the existing grasp and insertion volume.

The supplied sight mesh has protective front ears without a central post and
a solid rear leaf. Three small geometric inserts add a working rear notch and
front post. `WPN_RearSight` and `WPN_FrontSight` sit on the inserts' upper edges;
their separation is 37.611 cm. `WPN_SOCKET_Muzzle` and `WPN_SOCKET_Eject` follow
the new gun geometry. Full source, Blender and weapon-root-local coordinates
are recorded in `akm_replacement_export_report.json`.

- Seven original actions retain their timing and bone animation. Normal reload
  is 3.333333 seconds; empty reload is 4.291667 seconds.
- `fire` and `aim_fire` are 0.10-second mechanical clips at 120 fps. They preserve
  the idle/aim hand grip and gun root, reuse the source bolt's 7.458 cm travel,
  and add a four-degree trigger movement. Both start and end locked closed.
  Whole-viewmodel and camera recoil are supplied by the C++ gunplay layer.
- `equip` blends idle to the empty-reload pose at source time 1.75 seconds over
  0.18 seconds, then plays the remaining action. Export duration is 2.725 seconds
  (3.333 milliseconds of final-frame quantization at 120 fps).
- Gameplay reload retiming and synchronized sound cues are owned by the C++ layer.

## Verification and use

`akm_replacement_validation.json` checks 19 samples of preserved actions with
zero Blender matrix deviation, 28 evaluated model samples with finite positions
and plausible dimensions, and stable hands/root with closed single-fire endpoints.
`akm_replacement_unreal_import_report.json` records successful UE imports and
duration readback for all ten clips. UE shared-source pose sampling found maximum
drift of about 0.0000305 cm and 0.0000652 degrees.

The first PBR binding pass saved seven material references, but the runtime
capture revealed missing SkeletalMesh usage flags and default gray rendering.
The final game version therefore duplicates those materials into `Rendering`,
enables their skeletal shader usage, and duplicates the mesh with the corrected
bindings. This creates independent runtime packages while the source assets
remain available to the open editor.

`akm_runtime_materials_build.json` and `akm_runtime_materials_build.log` record
`AKM_RUNTIME_MATERIALS_BUILD_OK`: seven saved materials with SkeletalMesh usage,
the same skeleton, and compatibility with all ten original animation assets.
`akm_runtime_materials_readback.json` and its matching log record the separate
read-only process verification under `AKM_RUNTIME_MATERIALS_READBACK_OK`.
Commandlet exit code 1 can still reflect the existing GameFeatureData or
occupied MCP-port errors; the explicit script markers and reports provide
the asset verification evidence.

The Interchange importer emits an invalid-bind-pose fallback warning. Sampled
bone poses agree with the source, but live skinning, ADS and input verification
belong to the runtime acceptance pass. Asset import and material finalization
are complete. Integrated UE captures and input acceptance are now recorded in
`../GunplayUpgrade/validation.md`, including final runtime mesh/material usage,
ADS alignment, reload movement, held-trigger reload and cosmetic effects.

Blender pipeline scripts are in `../../Tools/AssetPipeline/` with
`akm_replacement` in their names. `import_akm_replacement_ue.py` imports only the
new UE directory. `finalize_akm_replacement_ue.py` binds the seven `*_PBR`
materials, requires a successful save, and validates the current UE assets.
The validation JSON records whether it was produced by independent readback or
by a same-process material finalization.

`build_akm_runtime_materials.py` creates and saves the final game mesh and seven
materials under `Rendering`; it does not modify the earlier source packages.
Its `-AKMRuntimeReadback` command-line mode only reads the saved assets and
asserts mesh skeleton identity, every material binding and SkeletalMesh usage,
and compatibility with all ten existing clips.
