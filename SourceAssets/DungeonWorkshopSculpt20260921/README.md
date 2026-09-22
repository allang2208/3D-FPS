# Workshop component modeling revision

Reference: `../../Docs/Gameplay/Previews/DungeonRoomConcepts_20260921/01_workshop_concept.png`.

The existing 5080 motor, whiteboard, cabinet, shelving and room layout are retained. This revision authors new tool and vise profiles, manufactured lamp shells, a folded-steel bench, worn timber, gravity-draped cloth and a small parts organizer.

Production order: `make_surfaces.py` with Python 3.11; `author_components.py` with Blender 5.1; `assemble_source.py` with Blender. Import and install only through `Tools/AssetPipeline/mcp_call_codex.ps1`, running `import_components.py` followed by `install_components.py`. Active play and unsaved maps are preserved by the installer.

`Authored/DungeonWorkshopComponents.blend` contains editable `SOURCE_*` collections and evaluated `ENGINE_EXPORTS`. Source collections use local workshop metres and are hidden by default; exported objects use the established dungeon world mapping. `Authored/DungeonRooms_WithRefinedWorkshop.blend` contains the complete room assembly. Earlier assets remain available.

No gameplay, performance, visual acceptance tests or screenshots were run. Production save receipts state the actual integration stage; source/FBX export alone does not mean the UE map was updated.

Installed and saved on 2026-09-21 at 19:53:14: 10 mesh assets, 6 new materials and 10 scene actors in `/Game/GameMaps/L_Dungeon_Prototype`. `Receipts/asset-import.json` reports `assets_saved`; `Receipts/scene-install.json` reports `map_saved`. User authorized ending the active play session for this installation. Existing light parameters and accepted unrelated room props were retained.
