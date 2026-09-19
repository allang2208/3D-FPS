# M4 large drum source and derivatives

Prepared 2026-09-09–10 for FPSGAME.

- Design and topology source: `E:/3d/3-dfps/tools/ai-gen/drum-v2-20260907/large-drum-v2.blend`.
- Original attribution: `E:/3d/3-dfps/assets/models/attachments/large_drum_v2/CREDITS.md`. Its design reference was the project's existing large-drum icon and an image-generated three-view concept. The initial TRELLIS mesh was rejected; the shipped Godot mesh was rebuilt locally. This migration derives from that rebuilt mesh.
- M4 fit, original upper magazine contour and current rig: `../M4FoldingSights20260909/M4_FoldingSights_Editable.blend`, with source coordinates from `../M4Replacement/m4_source_imported.blend`.
- Animation source: the project's existing Infima M4 normal reload and M4 bolt-release empty reload. Existing M4 and Infima asset license/provenance records continue to apply; this derivative does not grant new rights to those assets.
- Surface textures: the project's M4 `Magazine_Light_BaseColor`, `Magazine_Light_Roughness` and `Body_BaseColor`. `T_M4Drum_Roughness` is a separate linear (sRGB disabled) duplicate, keeping the original texture untouched. The drum uses new polymer/fastener materials; original geometry-specific normal maps are not reused on new geometry.

The Godot source files were read only. Optimized derivatives, runtime assets and editable files are kept in this UE project.

`M4_Drum_Optimized.blend` contains the fitted editable model. `M4_Drum_Reload_Editable.blend` additionally contains the corrected animation actions. Preserve their relative M4Infima source-library paths when moving the editable sources.

The runtime animation assets end in `_Smooth`. The earlier unsmoothed animation assets are retained as intermediate candidates and are not referenced by the character.

Reproduction scripts are under `Tools/AssetPipeline`: `inspect_m4_drum.py`, `build_m4_drum.py`, `build_m4_drum_reload.py`, `validate_m4_drum.py`, `import_m4_drum.py`, `import_m4_drum_reload.py`. Run model build, animation build, source validation, then the two imports in that order. Import scripts write only `/Game/Weapons/M4Drum` derivatives.
