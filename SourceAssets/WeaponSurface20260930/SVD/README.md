# SVD WS1 Clean production

Applied to the current SVD runtime mesh and 16 attachment meshes on 2026-10-01.
See `Docs/Weapons/svd-surface-standard-20261001.md` for the exact scope and preserved regions.

Authoring order: collect.py, read_graphs.py, seat_pose.py (Blender source), plan_surface.py,
bake_surface.py (Blender background), install_all.py (gated Unreal background authoring).

The install batch has saved 29 private masters, 59 bound instances, 8 masks and 59 wet
self mappings. Original package backups are in Before/. Runtime/game testing was not run.
Do not re-export FBX or rebuild shared WS1 materials as part of this batch.

Current finish: `Refine04/apply_finish.py`, after Refine03. R04 saves 59 existing
instances, one 1024 RGBA physical-scale grain map and one private furniture graph.
It keeps R03's shallow factory/extended-magazine pressing, original normal maps,
bevel normal layers and per-part base roughness/colour. The mixed original
handguard/stock receives finer satin polymer contrast and grain before wetness.
See `Docs/Weapons/svd-finish-refine04-20261001.md`.

`install_all.py` resumes R04 when its receipt exists, including partial saves.
Do not run historical WS1, MagazineSatin02 or Refine03 installers over this finish.
Those stages describe earlier production, not the current final asset state.
