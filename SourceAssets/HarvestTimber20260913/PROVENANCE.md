# Harvest timber, 2026-09-13

No asset purchase was made for this revision. The log reference images were generated for this project, then processed by the existing local RTX 5080 / ComfyUI TRELLIS.2 pipeline. No third-party timber model or audio sample was downloaded.

## Authoring chain

1. `cut_surface_reference.png`: generated front/right/end-grain reference, 1774 x 887. Its end-grain panel supplies the cut-surface texture through material UV mapping.
2. `three_views.png`: generated front/right/back reference of the same upright, short, thick poplar log. Three separate camera conditions are retained in `view0_00001_.png` through `view2_00001_.png`.
3. `generate.py`: local TRELLIS.2-4B, 1024 cascade, SS64, 16/24/20 sampling steps, seed 913180, 2048 texture resolution, 80,000-face intermediate export. Generation receipt: `07cd3c99-4cfb-4293-89ef-e17746a4d138`. `workflow.json` and `receipt.json` retain the submitted generation settings.
4. `raw_00001_.glb` and `textured_master_00001_.glb`: frozen generated mother meshes. `author_meshes.py` aligns the mother, derives reduced geometry, bakes the normal map, caps the cuts, and produces three log variants, a root-flared stump and a separate tree cut cap.
5. `HarvestTimber_Editable.blend`: editable mother and local mesh derivatives. `Delivery` contains FBX files, 2K bark textures and `authoring.json` with dimensions and triangle counts.
6. `author_audio.py`: original procedural crack and wood/leaf landing sounds, synthesized without third-party recordings. The WAV files are production candidates whose sound quality has not been auditioned.
7. `import_assets.py`: imports the owned timber files into `/Game/Items/HarvestTimber`. Falling-tree material instances derive from the project's existing `MI_BlackPoplarPCG_Bark` and `MI_BlackPoplarPCG_Foliage`. Their original foliage/bark textures remain existing project dependencies and retain their original license terms.

Binary assets and authoring sources remain in the local project under its existing publication rules. The public source commit contains code, authoring scripts and these notes; it does not redistribute the existing third-party tree material or its textures. Model/tool licenses remain applicable; generating a derivative does not relicense its tools or existing project inputs.

## Reference direction

Photorealistic freshly cut poplar trunk segment, roughly 80 cm long and 30 cm across, thick grey-brown longitudinal bark, irregular but solid cylindrical trunk, clearly readable pale end grain with annual rings and restrained radial splits, natural non-uniform silhouette, no branches, no thin sticks, neutral lighting and plain background. One image supplies front/right/end-grain; the generation condition supplies front/right/back views of the same upright object.

No acceptance rendering, PIE session, gameplay test or audio audition was performed for this revision. Texture baking and import are production steps, not visual acceptance.

## Original-tree stump follow-up

At the user's request, runtime stumps now derive directly from the four existing `SK_BlackPoplarPCG_A/B/C/D` source meshes, cut at local Z=42 cm. `original_stumps_export.py` copies editor `SOURCE_MODEL` geometry through Geometry Script; the ordinary skeletal FBX export contains incomplete fallback geometry for these Nanite trees. `original_stumps_cut.py` retains the original bark UVs, root geometry and origin, and creates matching stump and falling-trunk cut surfaces. `original_stumps_import.py` saves the eight derivatives and reuses the existing bark materials and this revision's end-grain texture. Editable FBX/Blend sources are under `OriginalStumps`.

These derivatives inherit the existing tree asset's license restrictions and remain local binary dependencies. The generated three log variants remain in use; the first generated stump is retained as an earlier local candidate. No new generation or purchase was required for this follow-up.

## Closed timber repair

The user reported that the pickup logs appeared as hollow bark. Focused FBX inspection confirmed fragmented surfaces and absent end caps. The textured mother has duplicated UV-island vertices, plus residual boundary cracks even after welding. The first reduction operated before welding and amplified these defects.

`repair_solid_logs.py` samples the same retained mother's outer shape into a continuous surface, rebakes BaseColor/Roughness/Normal onto new cylindrical UVs, and constructs closed, triangulated end caps using the original generated end-grain reference. No new AI generation, purchased asset or third-party download was used. Runtime now selects `SM_PoplarLog_Solid_A/B/C`; original logs remain local historical candidates.

`SolidRepair/SolidTimber_Editable.blend` and `SolidRepair/Delivery` contain editable geometry and production files. The user explicitly requested inspection for this repair: saved UE meshes were re-exported, checked for connected/closed/outward geometry, and rendered in Blender with their corresponding source PBR. `SolidRepair/engine_logs.png` is a Blender inspection image of UE-exported geometry, not a gameplay screenshot. No PIE or full gameplay regression was run.

## Matching cut sections and visible stump end grain

The next user request corrects the stump cross-section texture and requires the tree to separate at the cut before falling. `export_tree_sections.py` exports complete source geometry while explicitly retaining original bark/foliage face material assignments. `cut_tree_sections.py` derives matching lower and upper sections at local Z=42 cm and maps the cap across every inherited UV channel. `import_tree_sections.py` assigns the existing end-grain texture through UV0, retains original bark/foliage materials, enables Nanite for the upper sections and creates cut-rim profiles in imported UE coordinates.

The tree's foliage is held in Nanite assembly child assets and is not part of the exported trunk mesh. `build_falling_assemblies.py` retains the source skeleton, leaf assembly nodes and material remaps while replacing only the trunk source geometry with its cut, capped upper section. Bark, foliage and cut end grain occupy slots 0, 1 and 2 respectively.

`FellingCut/MatchedTreeSections.blend`, its source FBXs and `Delivery` contain local trunk derivatives of the same four licensed project trees; the complete crown remains a dependency of the UE assembly. Runtime now uses `SM_CutStump_*` and `SK_CutUpper_*`; `SM_CutUpper_*` is an authoring intermediate. The prior stump and cut-disk files remain historical local outputs. The closed pickup logs remain unchanged. No new generation, purchase or third-party download was used. No PIE, acceptance rendering or performance test was performed for this follow-up.

## Superseded-output archive

The user's subsequent cleanup request moved 49 superseded files to local `trash/harvest-timber-superseded-20260913`, preserving project-relative paths. This includes the first log/stump/cap outputs, the older OriginalStumps pipeline, unused UE bark packages, the older cut Blend snapshot, and a snapshot of the former base importer. Earlier sections describe historical source locations; current recovery uses README.md and the published per-file archive manifest in `Docs/AssetArchives`.

Frozen generated mothers, current editable files, source references, current timber/cut outputs and authoring dependencies remain in place. `prepare_timber_mother.py` replaces the retired initial low-mesh authoring script; `import_assets.py` now prepares shared materials/reference/audio only. No assets were regenerated during this cleanup, and archive hashes/reference checks are not visual or gameplay acceptance. Binary files, including trash, remain local under the same license boundaries.
