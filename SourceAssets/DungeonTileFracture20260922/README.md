# Bonded ceramic remnants

User reference: `C:/Users/allan/AppData/Local/Temp/codex-clipboard-64b8c32c-6ea1-444d-a4a7-dd96ff5f9b97.png`. The supplied image identifies thin triangular fragments, overly straight break edges and detached-looking pieces. It is not a preview of this revision.

The input is the previous `DungeonWallRelief20260922/Authored/DungeonWallRelief_Source.blend`. Existing glazed coverage identifies partial tile cells. Intact ceramic cells, repair patches, existing mortar relief, wall dimensions and scene layout remain the authoring baseline.

This pass replaces partial cells with broad edge-attached remnants, removes isolated slivers, adds a fine glaze lip, a 6.2–7.8 mm ceramic body and a bonded adhesive backing. Broken edges have long irregular fracture sections with small chips; the original tile atlas mapping is retained. Exposed ceramic body uses new project-authored 1K porous PBR maps at a 7.5 cm scale.

- Configuration: `Config/fracture.json`.
- Producer: `Scripts/author_core.py`, Blender `Scripts/author_fractures.py`.
- Editable source: `Authored/DungeonTileFracture_Source.blend`.
- Output geometry: eight FBX wall groups with their original actor/slot mappings in `Authored/geometry-manifest.json`.
- UE path: `/Game/Dungeons/AtmosphereV2/TileFracture/`.
- Target map: `/Game/GameMaps/L_Dungeon_Prototype`.
- Production receipts: `Receipts/materials.json`, `Receipts/meshes.json`, `Receipts/install.json`.

Run `py -3.11 SourceAssets/DungeonTileFracture20260922/Scripts/build.py` from the project root for local production. Add `--install` to import and save through the existing project bridge. `Scripts/install_saved_walls.py` only switches the references to already-saved meshes. The full dungeon installer applies this pass after WallRelief; the workbench editable-scene assembly includes the new source override.

Production counters: 143 partial ceramic cells, 100 replacement remnants and 43 cells with isolated fragments removed. Counts describe the producer, not visual acceptance. No PIE, screenshot, scene render, collision regression or performance test is run; the user evaluates the result. Local source binaries and previous wall sources remain restoration dependencies.
