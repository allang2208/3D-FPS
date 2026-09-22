# Workshop surface and close-detail revision

Targets: drawer organizer and labels, wall tools and hammer, perforated panel/header, double service socket; metal/grip finish also applied to tabletop tools.

Saved to `/Game/GameMaps/L_Dungeon_Prototype` on 2026-09-21 at 20:16:56. Six actor mesh references updated. Fourteen new material assets live under `/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopSurface`. The existing whiteboard, generated motor, lighting and room layout are retained.

Editable source: `Authored/DungeonWorkshopSurfaceDetails.blend`; complete assembly: `Authored/DungeonRooms_WithWorkshopSurfaces.blend`. `SOURCE_*` collections retain local-metre components; `ENGINE_EXPORTS` contains the world-coordinate meshes. Recipes and labels are in `material-manifest.json` and `labels.json`.

Production: Python 3.11 `make_materials.py`, Blender 5.1 `author_finish.py`, then `assemble_source.py`. Use the project bridge for `import_and_install.py`. The import creates independent materials, preserves prior assets and records stage receipts. No render or gameplay test was run.

Sources: ambientCG Wood051 CC0 channels already held in `AKMIntegration20260910/Redwood`; existing Quixel imperfection `rmmodbdp` from `ChestZiarat20260909/Source`, used as R dirt mask and G roughness, never as a B metallic texture. Original geometry, paint-channel construction and label artwork are project-authored. User screenshots supply the target corrections.
