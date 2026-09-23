# PKM machine gun — source record

- User-supplied file: `D:/FPS3D/资产/pkm_machine_gun.glb`.
- User-confirmed page: https://sketchfab.com/3d-models/pkm-machine-gun-c87bd6e648f140f98934d371180e69fb
- Author: EXcaliburK117 / account EXcalibur117, https://sketchfab.com/EXcalibur117.
- Page accessed 2026-09-22 through indexed page text: Free Standard; NoAI tag; published 2025-03-02.
- Embedded metadata: `SKETCHFAB Standard (https://sketchfab.com/licenses)`.
- The original GLB and source SHA-256 are retained in `Original/` and `source_structure.json`.
- This is a third-party asset, not an original model by Codex or the project owner. Preserve author and license information with derivatives. The source asset has not been uploaded to a model/texture generation service or publicly redistributed during this task.
- The NoAI restriction is recorded with the asset. This task uses local Blender mesh modifiers and deterministic procedural material baking; it does not run Meshy or another generative model on the asset.

## Work produced locally

`Refinement01/PKM_Lowpoly_Refined.blend` preserves 141 separate source meshes and their UV layout. Selected hard-surface parts have editable, overlap-limited 0.18 mm / three-segment bevels and weighted-normal modifiers. Unselected parts keep their source geometry and custom normals.

Six surface families receive BaseColor, Roughness, and tangent-space Normal textures: blued steel, copper jackets, lacquered cases, laminated wood, wood grip panels, and painted ammunition box. Wood textures use 2048 pixels; other surfaces use 1024 pixels. These textures add material appearance, not new mechanical detail. Steel and copper use metallic shading; wood and paint remain nonmetallic.

## Development boundary

This first revision develops the supplied exterior mesh and materials. It does not invent internal parts, cut mechanical assemblies by bounding boxes, add a rig, animate a reload, or restore retired PKM / PKM A game entries. The source has no skeleton or animation. Moving-part identification and first-person hand contact need a subsequent animation/integration stage.

No preview renders, game tests, or visual acceptance were run. The user reviews appearance.

## Reproduction

Run `read_source.py` once with Blender to import the user file. Run `build_finish.py` to produce the editable Blend, FBX, GLB, textures, and `delivery.json`. Shared production settings are in `finish_settings.json`; all paths resolve relative to this source directory except the original user input. The original user file is not modified.
