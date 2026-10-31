# Apartment kitchen detail — integration notes

## Current V2 state (2026-10-25)

V2 black/grey repaint, PBR detail upgrade and contact repair are installed in the authoritative map.

- Source hash: `3b6ffeb1d33f781072eaac6234d9c05aa390c1d46f79d6c69aef4f80036aef00` (`KitchenDetailV1.blend`), bound by `geometry-repair-v2.json`.
- Asset receipt: `assets_saved.json` — 22 meshes, 23 materials, 21 textures, seven connected PBR normal bindings.
- Map receipt: `map_saved.json` / `installed.json` — `stage: map_saved`, 27 kitchen objects updated, 0 added.
- Map hash: `63ccf479f2d6a361da17b1dca31a79265b6e6492a4ce3f5a2cf36d63f56c2dfb`, changed from `92703e6d…`; backup at `Backups/20261025-230301/L_CyberpunkApartment.umap`.
- Counter collision: four convex slabs around the open basin aperture (not the earlier two-wing layout).
- Twelve native containers and four refrigerator trim components on native hinges are preserved with identity local transforms.

Known limitations recorded rather than passed: `Prep` and `DiningDressing` each retain one hidden internal bottom-cap overlap inside their own revolved solid (238 and 80 face pairs, not visible, not a cross-object clash); `DiningDressing` has six sub-millimetre (0.5–0.83 mm) utensil-to-mat contact gaps. No PIE, gameplay, screenshot, performance or visual acceptance was run.

## Scope and route

Blender authors only kitchen component geometry and the original PBR surfaces. The authoritative UE scene is `/Game/GameMaps/L_CyberpunkApartment`; the old whole-apartment Blender assembly is **not** a replacement for this map. The production editor was closed before the background UE batches, so the project mutex/background commandlet route is used. No second UE process is launched while the production editor owns the project.

- Kitchen asset root: `/Game/Props/CyberpunkApartmentKitchen20261024`.
- Independent editable source: `KitchenDetailV1.blend`, with packed texture images.
- Original procedural 2048 BC/N/ORM surfaces: `Textures/` and `make_surfaces.py`.
- Component export and manifest: `build_kitchen.py`, `model.py`, `assembly.json`.
- UE asset publication: `build_assets.py`, `publish_background.ps1`.
- Scoped map integration: `install_level.py`, with the explicit `publish_level_entry.py` commandlet entry through the guarded `publish_background.ps1` route.
- Map save evidence is `map_saved.json` plus `installed.json` and a changed formal `.umap` hash; a commandlet exit alone is not a save receipt.

## Gameplay and scene boundaries

The target is exactly twelve native `ColdSteelSceneContainer` actors: five lower cabinets, five upper cabinets, and two refrigerator compartments. The cooking hob is not searchable. Existing actor identity, container ID, caption, storage pages, hinge transform, opening contract and collision settings are preserved. New refrigerator detail is attached to the native hinge and does not implement separate animation or ticking.

The legacy `AP_Kitchen_Run` fixed visual is retired only after all required component assets are saved. Native storage actors remain. The shared StaffLiving refrigerator mesh is not edited: only exterior `RS_Ceramic` and `RS_BareSteel` instance slots are changed. Interior `RS_PoolIvory` and `RS_FreshPlastic` slots remain intact.

No changes are authorized to bedroom V3, bay scenery, portal IDs, the atmosphere/clock schedule, global exposure, Lumen, ray tracing, texture pool, gameplay C++, or unrelated maps/assets. Preview-only room walls, lights and cameras in the independent Blender file are not imported into the UE apartment.

## Component and placement contract

`Cooking` is an authoring support designation, not a separate exported asset. Its induction glass, rings and controls are merged into `SM_KP_OvenFront`; the existing `OvenFront` placement installs that mesh once. Do not request an invented `SM_KP_Cooking` or skip the hob.

Before map mutation, the installer reconciles all 15 placement keys. Eight fixed details are new actors (`Counter`, `BackSplash`, `OvenFront`, `Sink`, `UtilityRail`, `Prep`, `Dishes`, `DiningDressing`). Four refrigerator details belong to the existing native root/hinge components. Coffee and kettle remain existing UE actors with their original transforms and collision; their duplicate-authoring placements are not spawned. An unrecognized placement is refused rather than silently omitted.

The measured translation in `spec.py::source_to_ue_cm()` converts the kitchen-source metre coordinates to apartment UE centimetres. Native containers are anchored and are never moved by this mapping. Fixed component-local axes and the support relationships of small props remain a separate authoring concern; the source-to-UE translation is not evidence of a component-axis or visual-fit review.

## PBR contract

Seven procedural families carry authored base colour, DirectX tangent-space normals, and packed occlusion/roughness/metallic maps. UE normal textures disable green-channel flipping; the OpenGL conversion exists only in the Blender preview material. UV0 uses authored metre coordinates with per-family physical texture periods. Imported FBX normals are retained with high-precision UV/tangent settings. No unbounded texture streaming override is used.

## Geometry correction record

The cabinet panel helper is called with explicit `thick=.034`. The right lower fastener was subsequently found at `x+w-.026` rather than the right edge inset `x+w/2-.026`; that separate placement defect caused the residual 80.955 cm overall width. Both corrections are in the current source, and the imported base and upper door bounds are 55.5 cm wide with the hinge at local X=0.

The original refrigerator door enamel face is at Blender local Y=-0.0325 m. Added trim stays near that face and avoids the original handle at X=0.623 m. Existing StaffLiving shells and handles remain unchanged. The exported component uses the established Blender FBX convention with `axis_forward='-Y'`, `axis_up='Z'`; no broad new axis conversion is applied to the apartment.

## Saved result — `level-background-11`

The formal apartment map was saved at **2026-10-24 23:05:53 +08:00**. Both `map_saved.json` and `installed.json` report `stage: map_saved`; the batch exited 0. The disk SHA-256 of `Content/GameMaps/L_CyberpunkApartment.umap` is `7d49abc03588099e51a60a43352a3885b3fc0ef2e7d4b701fa8cb6ec256e92b7` (1,160,992 bytes), matching the receipt. The pre-install backup is `Backups/20261024-230532/L_CyberpunkApartment.umap`, SHA-256 `5616890451ef1ce72a87be0a5647a86408cea7f95c3e231bb00ae0795245c41d`.

Saved scope: twelve native searchable containers, eight fixed-detail actors and four refrigerator detail components. The refrigerator body details are attached to native roots; the door details are attached to native `DoorHinge` components with identity local transforms. The saved receipt records the installer's native-container contract comparison. No new refrigerator animation or Tick was introduced. Existing coffee/kettle actors, collision and transforms remain authoritative.

The PBR materials and seven connected normal bindings were saved in the preceding asset batch. The installer read their saved bindings before changing the map. No kitchen FBX or geometry was rebuilt for the Cooking mapping or subsequent commentary about possible coordinate conventions. The authoritative receipt records asset paths and placement contracts; it does not prove component-local visual orientation or a separate fresh-process reload review.

## Evidence and limits

`assets_saved.json` is the asset save receipt, including FBX SHA-256 resume keys and seven read-back normal-property bindings. `map_saved.json` and `installed.json` are written only at their reported map stage; a failed guard is not a saved integration. The formal `.umap` is backed up into `Backups/<timestamp>/` only after all source/asset gates pass and before the single scoped write batch. The source and receipts do not constitute visual or gameplay acceptance.

The opt-in `test_pure_contracts.py` has three assertions covering panel geometry, all manifest/receipt FBX hashes, and the explicit refrigerator material-slot replacement rule. It uses Blender Python for `bpy`; it does not run a UE editor or PIE. `RS_PaintedSteel` is not an observed project slot and must not be added to the replacement mapping. The original fridge's ivory/plastic/gasket slots remain unchanged.

An editor session was opened separately by project work. The installation's editor guard rejected an active PIE without loading or saving a map; after the user authorized stopping PIE, the existing editor exited normally through an independently issued `QUIT_EDITOR`. No new interactive UE editor was launched by this kitchen task. Subsequent installation uses the same background mutex route.

No gameplay tests, performance capture, screenshots or acceptance renders are run as part of this task. The only tests are the three explicit pure-function/file-contract cases above. Existing `KitchenPreview.png` is from an earlier source revision and must not be treated as final visual evidence.
