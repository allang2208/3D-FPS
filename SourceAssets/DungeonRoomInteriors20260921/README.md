# Dungeon room interiors — approved concept implementation

**2026-09-22 status:** the delivery below is historical. The user rejected the motor; its source files and dedicated import script are archived, and `assets.json` no longer generates it. Current workshop authority is `DungeonWorkbenchKit20260921` plus `DungeonWorkshopRackPolish20260922`. See [publication and recovery](../../Docs/Gameplay/dungeon-workshop-publication-20260922.md).

Project: `D:/FPS3D/FPSGAME`, Unreal Engine 5.8.2.

Delivery: all 37 authored mesh groups and both generated masters are saved in UE;
the motor and two bank placements are saved in the dungeon map. The editable
assembled Blender source is saved. `Receipts/room-install.json` is `map_saved`.
No game tests or screenshots were run; user visual acceptance remains pending.

This revision dresses the workshop and ruin side chamber in the existing
`/Game/GameMaps/L_Dungeon_Prototype`. It does not change runtime topology, combat,
events or saves. Source concepts are in
`Docs/Gameplay/Previews/DungeonRoomConcepts_20260921`.

The authored models use the original Blender metre coordinates. Workshop local
coordinates map to `(10-u, -v, z)`; ruin coordinates map to `(15+u, 4+v, z)`.
FBX import converts metres to centimetres and mirrors Y as in the original V2.
Scene-authored meshes keep baked world positions; generated props use a centred
bottom pivot and explicit placements in `Authored/room-manifest.json`.

## Production files

- `Scripts/author_surfaces.py`: original PBR surface maps, no preview render.
- `Scripts/author_rooms.py`: geometry, FBX exports and the room manifest.
- `Scripts/local_pipeline.py`: owned ComfyUI references and mesh jobs; receipts
  prevent duplicate submissions. Uses the preinstalled FLUX.2 / TRELLIS.2 setup.
- `Scripts/refine_generated.py`: preserves each master, adapts the game mesh and
  bakes tangent normals. Game density targets are 60,000 motor triangles and
  90,000 bank triangles, not measured runtime performance.
- `Scripts/assemble_room_source.py`: saves a combined editable room source.
  The existing statue is represented by its anchor; its actual asset stays in UE.
- `Scripts/import_room_assets.py`: revision-only UE material and mesh packages.
- `Scripts/import_generated_phase.py`: imports the generated masters' game exports.
- `Scripts/install_rooms.py`: complete room installation after source/import readiness.
- `Scripts/install_authored_phase.py` and `finish_scene_props.py`: the staged route
  used this turn while remote production completes; they save the same final rooms.

UE operations use the existing project `Tools/AssetPipeline/mcp_call_codex.ps1`
batch mutex, with unique `-OutputFile` and `-MaxOutputChars 3000`. No direct MCP
bypass, cross-task coordination, default tests, PIE start or screenshots.

The V2 installation chain now reapplies this revision after its tile and natural
surface passes, so a future deliberate full V2 rebuild retains the room work.
That full rebuild was not run for this scoped implementation.

## Receipts and boundaries

`Receipts/asset-import.json` records saved UE assets. `room-install.json` uses
`authored_saved` while generated dressing remains outstanding and `map_saved`
only after the complete room installation. Previous actor references, transforms
and relevant visibility/collision values are in `previous-room-state.json`.
Earlier assets are retained, not deleted.

The motor uses front/side/back conditioning. The bank uses the front of its
reference sheet because its backing is embedded; unseen sides are reconstruction.
The original queued multiview-bank receipt is retained under `superseded_...` and
was withdrawn before execution. No other task's queue item was cancelled.

All previews in the concept directory remain generated concepts. This production
turn does not supply new in-game screenshots or claim gameplay/visual acceptance.
