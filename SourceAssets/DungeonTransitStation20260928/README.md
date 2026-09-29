# Abandoned Transit Station — random dungeon combat room

The user accepted the expanded architecture and requested pool integration plus retirement of the independent map/menu entry on 2026-09-29.

The hall is 48 × 33 m with an 11.7 m vault. The track pit is 10.5 m wide and 1.8 m deep; standard rail gauge, doors, stair risers, tiles and fittings keep their real scale. Pier bases clear the side doorway frame by 0.60 m. The existing approved geometry and materials are reused without another art iteration.

`Config/pool.json` controls the initial selection policy: 30% eligibility per run, at most one station, on the pre-junction Approach route. Placement remains subject to the normal spatial constraints. Eligibility is not a guaranteed appearance percentage. The module has 12 safe floor spawn anchors and a sealed 4–6 member encounter using the existing FreightTransfer monster pool, levels and ranks.

Production files:

- `Config/room.json`: architecture in Blender metres, UE mapping `(100x, -100y, 100z)`.
- `Config/pool.json`: frequency, monster count and spawn/path anchors.
- `Config/module.json`: generated runtime module in UE centimetres.
- `Authored/AbandonedTransitStation_Subject.blend`: editable approved source; legacy filename retained.
- `Scripts/prepare_design.py` and `author_station.py`: author geometry if requested.
- `Scripts/import_assets.py`: reimport owned runtime meshes without creating a sample level.
- `Scripts/install_pool.py`: save module and dependencies into the current dungeon generator; no layout generation.
- `Receipts/pool-install.json`: map persistence receipt.
- `Receipts/pool-delivery.json`: final build/retirement record.

The production map is `/Game/GameMaps/L_Dungeon_Randomized`. The room has 20 authored meshes plus 11 reused fixtures and one power cabinet. It omits sample port caps, return portals, PlayerStart and the sample exposure volume. All 11 lights use the existing room light scheduler.

The independent map `/Game/GameMaps/Design/L_AbandonedTransitStation_Subject` is retired from Content and the expedition menu. Retired map/cap assets are retained outside Content under `trash/dungeon-transit-station-standalone-20260929`. The old map installers and module draft live under `trash/dungeon-rooms-closeout-20260929/SourceAssets/DungeonTransitStation20260928/SourceBackup/StandaloneRetired20260929`; do not run them to restore the retired entry.

Optional furnishings remain listed in `Config/asset-schedule.json`. No train, ticket machine, seating or new graphics are implied by pool integration. Source/license dependencies keep their existing restrictions. No gameplay, layout-seed, navigation, visual or performance tests were run.

Current documentation: `Docs/Gameplay/dungeon-transit-station-pool-20260929.md`. Earlier sample design and build history: `Docs/Gameplay/dungeon-transit-station-subject-20260928.md`.

Archive status update: the user cleared trash during closeout and explicitly requested continuation. Earlier sample maps/installers/backups were deleted by the user after archival; their paths above are historical, not available recovery locations. Only the second closeout asset batch remains in trash; consult the publication archive manifest. Current production assets/author inputs remain in place.
