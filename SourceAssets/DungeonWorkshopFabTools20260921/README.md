# Workshop Fab tool adaptation / 2026-09-21

User-selected source: [Ultimate Garage Tools Pack (10 Items) - Game Ready FREE](https://www.fab.com/listings/eba94efa-c186-4004-83ba-d420d35f8f90), by Vladyslav Chykunov. The user downloaded the individual FBX files, then the Blender source with packed textures. Original files and Fab metadata are preserved under `Sources/`. This is a local project adaptation; no third-party source files have been published.

## Production

- Preserve the ten distinct tool profiles, metre scale and atlas UVs.
- Add angle-limited 0.25–0.65 mm, three-segment edge radii and weighted normals. These are small manufactured chamfers, not a blanket subdivision pass.
- Extract the publisher's clean and worn 2048² BaseColor, Normal, Roughness and Metallic atlases from `hand_tools_set.blend`. Height maps are retained as source data, not connected as displacement.
- Mix corresponding PBR channels with a different `WearBlend` per tool. Working tools on the bench are cleaner than the wall versions. The existing rust, wood grain, paint chips and engravings remain in their original UV locations.
- OpenGL normal convention follows the publisher's Blender normal-map graph; Unreal textures invert the green channel. Color textures are sRGB/BC7; data maps are linear; normal maps use normal-map compression.
- Place nine tools on the board and four on the bench (all ten types are represented). Use unequal spacing, small deliberate angles, bent steel hooks and mounting tabs. Replace the previous uniform wrench row and loose wrench/screwdriver/pliers.
- Preserve the vise, ratchet, socket rail, caliper, oil cans and parts tray. Preserve drawer, header and socket labels; remove the previous five wrench-size labels, which no longer match the tool arrangement.

## Outputs

- `Authored/DungeonWorkshopFabTools.blend`: editable tool sources, material variations, positions and export meshes.
- `Authored/DungeonRooms_WithFabWorkshopTools.blend`: the complete editable room assembly.
- `Authored/manifest.json`: 26 FBX exports, original ten reusable tools plus thirteen placements and three supporting assemblies.
- UE destination: `/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopFabTools`.
- Target map: `/Game/GameMaps/L_Dungeon_Prototype`.

Imported and map saved on **2026-09-21 21:18:21**: 26 meshes, 14 material instances, 8 textures; 16 installed actors. Previous tool and old wear actors remain hidden. See `Receipts/bridge-delivery-05.txt`, `asset-import.json` and `scene-install.json`. This is an import/save result, not visual or runtime acceptance.

Run `author_tools.py`, `bind_materials.py`, then `assemble_source.py` with Blender 5.1. `prepare_sources.py` and `extract_atlas.py` are source acquisition steps; their preserved outputs are already local. Import and install through `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript .../Scripts/import_and_install.py`. Scene-install and asset-import receipts record completed stages. No game, screenshot, render or performance test is part of this work.
