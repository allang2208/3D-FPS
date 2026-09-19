# HandBrain Fab material V04 — 2026-09-11

User-added source: `/Game/ZombiSkinMaterial`. Five actual 4096x4096 texture sources were exported to `fab_source`; see `assets.json` and `provenance.json` for asset paths, attribution context and hashes.

The red organic surface contributes height, roughness, AO and color luminance. Original Hunyuan color retains the wound placement; local shading supplies olive green skin and darker wet wounds. Height is box-projected in model rest space and converted to bumps, then baked to existing UVs. The supplied tangent normal is archived but not directly box-projected, which would use incorrect tangent directions.

Fifteen valid final UV maps: body 4K, other surfaces 2K. The original degenerate mouth-interior UV uses constant mucosa shading, never its empty test bake. Geometry positions, 38 bones and five action durations are unchanged.

Editable source: `HandBrain_Refined.blend`. Export-map reload validation: `HandBrain_Refined_Baked.blend`, `Baked_check.png`, `bake_validation.json`. Neutral-light images are Blender renders, not UE screenshots. Surface detail is deliberately subtle; rounded fingers and joints still require geometry sculpting to improve their anatomical structure.

Tools in `Tools/HandBrain`: `export_fab_skin.py`, `refine_fab_materials.py`, `bake_fab_materials.py`, `verify_fab_bake.py`, `import_fab_materials.py`. The dedicated import targets `/Game/Monsters/HandBrain/RefinedV04` and only replaces the six skeletal-mesh material slots. It does not rebuild the corrected PhysicsAsset or import skeleton/animations.

UE import completion is recorded separately by `ue_import_report.json`; runtime evidence belongs in `runtime/` when available.

## Runtime material correction

The first fresh game run exposed two earlier integration defects: the original materials lacked `used_with_skeletal_mesh`, so UE substituted the default material; and `save_loaded_asset(mesh)` skipped a material-slot change because the asset was not considered dirty. `finalize_fab_materials.py` sets the skeletal usage flag and forces saving with `save_loaded_asset(mesh, False)`. `finalize_report.json` confirms the previously persisted original slots and the six replacement V04 slots. Blueprint component material overrides are empty. The main import script now applies these fixes for future rebuilds.

## Actual verification boundary

Fresh UE game images show the green material instead of the default material; no HandBrain missing-skeletal-usage warning remains. Village lighting strongly shifts green toward yellow. Runtime images and the latest full log are in `runtime/`.

The latest 12:02 run passed 29/30 gameplay checks. Slam contact passed on this run, but the cranium capsule support sample was -8.470 cm against the -5 cm threshold, failing `ragdoll_stays_above_terrain`. The preceding run passed ragdoll contact (-0.738 cm) but failed the slam timing check during slow startup. Thus this material delivery is not a claim of all-green gameplay regression or universally stable ragdoll contact. The mesh remains visibly on the ground rather than falling meters below it; slope/contact stability still needs investigation. No gameplay or physics assets were modified in this material task.
