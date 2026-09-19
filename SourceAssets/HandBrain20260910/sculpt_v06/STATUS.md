# HandBrain V06 — hand anatomy sculpt

2026-09-11. This pass addresses the rounded constituent hands of the V05 monster. It uses the accepted V05 face, oral UVs, rig and five actions.

## Actual sculpt scope

`landmarks.json` contains manually authored finger and wrist landmarks on the 1400-pixel left/right/back orthographic model renders. `projected_features.json` records their ray-projected surface positions. The pass covers 26 visible constituent hands and 92 finger segments; occluded hands, thumbs without clear landmarks, and the separately generated attack-arm/crown meshes are not claimed individually rebuilt.

The runtime body mesh has actual coordinate edits: knuckle and wrist prominences, narrowing between joints, lateral finger shape changes and dorsal tendon ridges. `sculpt_report.json` records the moved vertices and maximum displacement. Topology and vertex group assignments remain unchanged. This is a landmark-guided geometric refinement of the existing mesh, not a replacement anatomically retopologized hand model.

A subdivided high mesh adds shallow joint creases and recessed nail borders/raised nail beds. Its fine surface and nail coloration are baked to the runtime UVs. A surface mask limits normal/color replacement to sculpted regions; V05 oral/mouth textures and the other object maps are reused. The low-mesh tangent-normal map is not directly applied to the subdivided high mesh, and inherited custom normals are cleared before sculpting. Broad low-poly planar areas still limit extreme close-up quality.

## Editable assets and comparison

- `HandBrain_Sculpt_Source.blend`: low mesh and hidden high sculpt, 38-bone rig and five original actions.
- `HandBrain_Refined_Baked.blend`: runtime geometry with baked textures reloaded.
- `Hands_Before.png` / `Hands_After.png`: identical-camera/lighting material comparison.
- `Geometry_Before.png` / `Geometry_After.png`: clay comparison that excludes texture changes.
- The original four view images are landmark references; `Hand_high_closeup.png` is an intermediate high-mesh preview, not the final runtime bake.
- `bake_manifest.json`, `bake_validation.json`, `mask_validation.json` identify the actual maps and validation boundaries.

## Rebuild order

Use `Tools/HandBrain/sculpt_reference_views.py`, then `sculpt_hands.py`, `bake_sculpt.py`, `merge_sculpt_maps.py`, `verify_sculpt.py`, `preview_sculpt_compare.py`, `export_sculpt.py`, `preview_sculpt_export.py`, `import_sculpt_mesh.py`, `import_sculpt_materials.py`, `activate_sculpt.py`. `merge_sculpt_maps.py` runs with the system Python 3.11 that has NumPy/Pillow; the Blender scripts use Blender 5.1. The source sculpt can skip costly intermediate renders with `-- --skip-render`.

Dependencies include the V05 editable source and its maps, with Fab attribution retained in `../material_v04/provenance.json`. Do not delete the original generated meshes or V05 source. UE assets use the separate `/Game/Monsters/HandBrain/SculptV06` folder. Integration and actual game evidence are recorded separately after validation.

## Final V06 validation and activation — 2026-09-11 13:06

- Body: 60,926 vertices, 6,137 displaced, maximum 5.731 mm. High sculpt: 1,456,656 vertices. Combined exported mesh: 84,546 vertices, six material slots and 38 bones.
- `contracts_validation.json`: topology counts and exact skin-weight hashes unchanged for all four meshes; five sampled bone poses per action match V05. No new animation curves or gameplay logic were introduced.
- 18 baked maps reloaded and checked. Body slot 0 replaces only masked color/normal pixels (10.298% nonzero mask); unmasked pixels remain exact. Oral/mouth maps reused. `mask_validation.json` records this boundary.
- Exported Howl FBX reimported and rendered: 90-frame span at 30 fps, 3 seconds, 38 bones. Material lookup uses the actual names from `export_report.json`, including Blender numeric suffixes; hardcoded old names can retrieve unused white materials. `Howl_Sculpt.gif` is a repeating inspection preview of this export.
- `BP_HandBrain` now uses `/Game/Monsters/HandBrain/SculptV06/SK_HandBrain_Sculpt` and `A_HandBrain_Howl_Sculpt`, with the original skeleton and other four clips. Candidate physics was regenerated through the corrected scale-aware factory; materials, slots and Blueprint were force-saved.
- Fresh independent village game: **30 passed, 0 failed**. Actual capsule sweep gap **-0.004 cm**; corpse visible on terrain. `runtime/acceptance.json`, `runtime/play.log` and the five-state screenshots preserve this run. This is one successful runtime regression, not a claim of exhaustive stability or packaging acceptance.
- UE commandlets emitted completion markers and saved reports, but exited 1 due to the pre-existing GameFeatureData asset-manager error. Import success and the independently passing runtime are reported separately from that unrelated project error.
- Close-up hand and clay comparisons show the actual local refinement. Some broad planar areas, occluded hands and the separate attack/crown meshes still need manual anatomical rebuilding for extreme close-up realism. This pass must not be described as a complete per-hand retopology.
