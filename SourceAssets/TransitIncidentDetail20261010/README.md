# FacilityTransit detailed incident props

Detailed replacement for the nine original incident props; the room's current transforms and lighting remain the placement authority.

Production entry points:

1. `textures.py` authors seven shared PBR/print maps with Pillow and NumPy.
2. `author.py` runs in Blender 5.1 background mode, creates nine locally grounded FBX meshes and `Authored/TransitIncidentDetail.blend`. `blender_materials.py` packs editable source PBR materials into the blend file; it does not render.
3. `run_background.ps1 -RenderShaders` runs `install.py` through the existing UE mutex/bridge or a background commandlet. It imports 25 scoped assets and replaces mesh references in the formal map and two existing subject maps.
4. `recipe.py` is the idempotent source-catalog and subject overlay. It preserves current positions, rotations, gameplay fields and original blood decals.

`Receipts/install.json` records actual save stages. Source provenance and delivery boundaries are in `../../Docs/Gameplay/transit-incident-detail-20261010.md`. Old authoring assets remain in `../TransitIncidentDressing20261010`. A future geometry revision should use a fresh asset path instead of overwriting a differing imported source hash.

No game, screenshot, render or acceptance test was run. The user owns visual acceptance.
