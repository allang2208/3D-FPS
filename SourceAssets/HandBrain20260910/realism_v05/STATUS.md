# HandBrain realism and howl mouth refinement — V05

2026-09-11. Source reference actually reviewed: `Y:/开发/游戏/素材库/怪物/手脑/attacking-2.png`, 28 images. Existing contract retained: 3-second one-shot howl, full opening 0.82–1.8 s, closed by 2.62 s; gameplay six pulses at 0.5-second intervals. The reference raises many constituent hands; this revision addresses the face/jaw and does not claim full reconstruction of all those hand motions.

## Mouth and material

- Refined lower lip vertices and redistributed chin weights. Replaced the 31 cm downward jaw translation with a 29-degree hinge rotation plus small retreat/drop. Reduced upper-lip lift and cheek widening. Preserved the same face and its attached mouth lining; no replacement head.
- Added nondegenerate UVs to the original oral lining, replacing the old constant-only workaround. Eighteen usable baked maps, including oral color, roughness and tangent normal, passed reload validation.
- Increased dry-skin roughness, reduced uniform shine/saturation, retained wound-local red color and separate roughness, and used the user-added Fab organic height/AO/roughness/color variation. Lip rim has a muted tissue transition. UE uses Default Lit to avoid washing the skin with uniform green subsurface color.
- Geometry edits are localized to the lip band; chin influence changes primarily affect howl. Other authored action curves remain unchanged. This is a refinement of the existing generated topology, not a complete anatomical resculpt of every hand.

## Editable source and export proof

`HandBrain_Refined.blend` contains editable shaders and five actions. `HandBrain_Refined_Baked.blend` reloads the baked textures. `SK_HandBrain_Realism.fbx` and `A_HandBrain_Howl_Realism.fbx` are engine exports. Reimported FBX has 38 bones and a 90-frame/3-second span; Blender's FBX importer offsets its frame range to 2–92. UE validates exactly 3 seconds.

`Mouth_export_1/16/34/66/91.png` and `Howl_Realism.gif` render the reimported FBX with baked maps. GIF repeats for inspection; gameplay howl remains one-shot. `preview_frames/` retains source frames. These are Blender renders; `runtime-*/` images are actual UE village captures.

## UE integration and physics

`/Game/Monsters/HandBrain/RealismV05/SK_HandBrain_Realism` shares the existing skeleton. `BP_HandBrain` references this mesh and the new howl sequence; idle, movement, slam and death still use the existing sequences. Original V04 assets remain available. `activation.json` records the prior and active references.

The three ragdoll bodies retain corrected bone-scaled dimensions and now use CCD with 16 position / 8 velocity solver iterations. Contact verification sweeps the actual oriented capsule against scene geometry, rather than extending one sampled terrain triangle into an infinite plane. It retains the -5 cm penetration threshold and logs the old plane estimate for comparison.

Build `9111407` succeeded. The first fresh village run passed 30/30; capsule sweep gap was -0.009 cm, while the old plane estimate was +3.496 cm. `runtime-1/` contains the report/log/screenshots. This validates the tested village scenario, not every slope or network configuration.

## Rebuild tools

In `Tools/HandBrain`: `refine_realism.py` (uses `adjust_jaw.py` here), `bake_realism.py`, `verify_realism.py`, `export_realism.py`, `preview_realism_export.py`, `import_realism_mesh.py`, `import_realism_materials.py`, `activate_realism.py`. Compile the native physics changes before importing the candidate PhysicsAsset. Force-save imported texture settings/material slots and enable skeletal-mesh material usage. Run the mesh import before material import and activation.

Fab source files and attribution remain in `../material_v04/fab_source` and `../material_v04/provenance.json`; the material script references those exact local inputs. Original Hunyuan maps and the existing death source are also reconstruction dependencies.

## Repeat verification

`runtime-2` also passed ragdoll contact: actual sweep +0.017 cm versus the old triangle-plane estimate -5.322 cm. This demonstrates a false penetration classification by the plane approximation. That full run passed 29/30, with `fear_stacks_and_moves_away` failing intermittently; it was not discarded. Additional fear-state diagnostics were added without modifying gameplay or relaxing assertions. Build `9111427` succeeded. `runtime-3` passed 30/30; fear had 3 stacks and 198.502 cm displacement. The earlier fear failure did not reproduce on that diagnostic run, so it is not claimed independently fixed. All three V05 runs passed actual capsule contact.
