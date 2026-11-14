# Freight warehouse entrance sample

Target: `/Game/GameMaps/Design/L_FreightTransit_Theme_Subject`

User direction: abandoned warehouse with wear, dust and localized damage; keep the main route legible. This is a limited art sample, not a new room layout or a dungeon-wide replacement.

## Installed scope

- Entrance packing area: stacked damaged pallets, a remaining crate, dolly, toolbox, loose slats, cardboard and discarded station forms.
- Adjacent west rack W1: a partial pallet/crate in an empty lower bay, an empty damaged pallet in the upper bay, sparse shelf remnants and dust. Existing cargo, rack structure and interactive containers remain.
- Corresponding south/west walls: localized crack and flake normals, low handling wear and irregular damp marks. Different authored masks are used for dust, abrasion and dampness.
- 35 static decorations and 21 surface decals replace 36 previous decorations and 8 decals in this scope. Decorations elsewhere remain unchanged.

The original five concrete surface bindings, all original actors/transforms, lights, post process, player start, main path, containers and gameplay logic are retained. Surface overlays do not replace wall/floor materials. Dust overlays do not overwrite their normal maps. No global lighting or rendering settings are changed.

## Asset sufficiency

The currently owned assets support this sample; no Fab acquisition is needed for the present scope.

| Source | Reuse |
| --- | --- |
| UndergroundTunnel | Weathered pallet variants, crate, dolly, toolbox, slats, cardboard with native PBR and normal maps, a small rubble remnant |
| HospitalCorridor | Three different authored grime/scuff masks; crack and damaged-plaster decals with their original normal maps |
| TransitIncidentDetail20261010 | Curled discarded station forms |
| Existing CargoWarehouse | Original structure, racks, concrete, cargo, labels, lamps and gameplay containers |

Substantial added props use scoped mesh copies with static geometry collision. Small paper, cardboard, slats and fragments have no collision. Copies retain original asset PBR material references. Shared source meshes and materials are not modified.

## Authoring

`Config/layout.json` is the assembly placement source, in UE centimetres relative to warehouse origin `[3760,-900,0]`. `author_layout.py` derives floor and rack support heights from source-model triangles, and stacked support from actual pallet/box triangles. No procedural whole-room scatter is used.

`read_authoring_inputs.py` reads selected source meshes/materials. Its texture thumbnails are input-reference inspection only, not a rendered scene preview. `install.py` saves only this map and this namespace, with an exact pre-install map/external-package backup. `finish_rack_collision.py` completes the three added rack props' collision.

Production receipt: `Receipts/install.json`. The previous full before-weathering comparison map is retained unchanged.

## User entry

```text
open /Game/GameMaps/Design/L_FreightTransit_Theme_Subject
```

Follow the original route from the freight-transfer spawn to the warehouse entrance. The sample is on the wall side of the entrance packing area and the adjacent west rack. Spawn and route have not been relocated.

No game, visual acceptance, screenshot, render, navigation test or performance test was run. The user evaluates the saved sample in game.
