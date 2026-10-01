# ASH12 WS1 Clean authoring

Production record: `Docs/Weapons/ash12-surface-standard-20260930.md`.
Runtime mesh remains `/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface`.
New material assets: `/Game/Weapons/ASH12/SurfaceStandard20260930`.

Inputs are the existing ASH12 assets and the shared WS1 pipeline. No new third-party media.

Pipeline:
1. `export_inputs.py` and `export_bones.py` through `../run_ue.ps1`.
2. Blender background opens `SourceAssets/ASH12Surface20260919/ASH12_Surface_Editable.blend` and runs `seat_pose.py`.
3. `py -3.11 plan_surface.py`, then Blender background runs `bake_surface.py`.
4. `../run_ue.ps1 -Script <absolute path to install_all.py>` installs/saves the assets in a gated batch.

`install_all.py` uses the existing editor when open and otherwise supports the shared background entry. It does not start PIE or tests. Do not run it while the ASH target packages have unrelated unsaved changes.

`Before/` is the package backup before this upgrade. Keep it with the receipts. Do not restore packages over a running editor or replace its unsaved work. The UV writer only changes gun UV1; it preserves the original arm channels and authored vertex colors. Reimporting the old FBX requires reapplying UV1.

Main instances retain source normals and vertex-color material regions. Static instances keep their own mask/normal mapping. Extended-magazine normal continuity still reads UV1 through UV6. Mixed optical/light materials and the suppressor bronze band remain original, as listed in `slot_plan.json`.

Delivery: 27 bound instances, 15 mesh packages including the main gun, 5 masks; weather mapping saved. No gameplay or visual acceptance run.

Current finish is **Refine02 (2026-10-01)**. It saves the same 27 instances with
physical-scale fine grain, separate mixed-region detail controls, per-part metal
response and matching factory/extended polymer magazines. Seven main-gun
instances use the new regional graph through three copied private presets.
The other 20 retain their parents; all source normals and extension seam data
remain on their original inputs. No meshes or weather table were rewritten.

Current entry: `Refine02/apply_finish.py`, also selected by `install_all.py` when
its receipt exists. Do not directly rerun the old `build_region_master.py` /
`install_surface.py` stages over this revision, since they reset its parameters.
See `Docs/Weapons/ash12-finish-refine02-20261001.md` and the saved receipt in
`Refine02/apply_receipt.json`. No game/visual tests were run for this revision.
