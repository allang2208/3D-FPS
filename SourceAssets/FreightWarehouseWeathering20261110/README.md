# Freight warehouse weathering subject

Target: `/Game/GameMaps/Design/L_FreightTransit_Theme_Subject`.

This revision dresses only the existing warehouse inside the freight-to-station
line. At the user's request, wall and floor surfaces use their original
`MI_WallConcrete` bindings. Both replacement surface passes are retired, and
the authoring entry keeps the original materials on rebuild. Eleven authored groups add packing residue,
maintenance items, rack-end debris and service-corner grime. Imported prop
meshes retain their materials. New scenery has no collision or interaction.
Existing room geometry, containers, route, lighting and player start stay in
place. The production dungeon catalog is not modified.

## Enter

```text
open /Game/GameMaps/Design/L_FreightTransit_Theme_Subject
```

The player starts in the original freight transfer area. Continue along the
existing route to the warehouse.

## Before comparison

```text
open /Game/GameMaps/Design/L_FreightTransit_BeforeWeathering
```

This is a saved copy of the subject immediately before this art pass.

## Return

```text
open /Game/GameMaps/DayNight_Lighting
```

## Authoring sources

- `inputs.json`: saved-map and source-kit authoring inputs.
- `Geometry/`: actual source surfaces used to place floor objects and wall decals.
- `materials.py`: scoped surface and grime material authoring.
- `author_layout.py` and `Config/layout.json`: deterministic decoration groups,
  support heights, route/container clearances and material bindings.
- `build_assets.py` and `install.py`: background asset and map saves.
- `Receipts/assets.json` and `Receipts/install.json`: actual save status.
- Pre-install backups are archived under `trash/FreightStation20261114/` using their original project-relative paths.
- `SurfaceRevision2` was explicitly rejected and is now archived under the same trash root, including its original inputs and restoration record.
- `FloorRollback20261111/restore_floor.py`: restore the four original floor bindings.
- `FloorRollback20261111/install.json`: actual floor rollback save status.

No game, PIE, screenshots, rendering or acceptance tests are run by this workflow.
The user will review the saved sample in game. It remains a subject-map revision
until the user accepts its appearance and requests production integration.
