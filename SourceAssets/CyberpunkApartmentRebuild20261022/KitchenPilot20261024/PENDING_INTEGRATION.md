# Kitchen integration — saved map receipt

## V2 black/grey contact repair — installed 2026-10-25 23:03 +08:00

The V2 source and assets are now installed in the authoritative map.

- Source: `KitchenDetailV1.blend`, SHA-256 `3b6ffeb1d33f781072eaac6234d9c05aa390c1d46f79d6c69aef4f80036aef00`; `geometry-repair-v2.json` records `stage: local_layout_checked` with `source_matches: true` bound to that hash.
- Assets: `assets_saved.json` reached `assets_saved` in `v2-assets-20261025-202143` through the guarded background commandlet route. It records 22 mesh imports, 23 materials, 21 textures and seven connected PBR normal-property bindings. Every FBX SHA-256 matches the current manifest.
- Map: `v2-level-20261025-230053` completed with exit code 0 and printed `KITCHEN_SCOPED_INSTALL_SAVED 27 0`. `map_saved.json` and `installed.json` report `stage: map_saved`. The formal `.umap` hash changed from `92703e6d1e0ef47e587f9c483a4766d55a52d860867452f50daedb953051ca88` to `63ccf479f2d6a361da17b1dca31a79265b6e6492a4ce3f5a2cf36d63f56c2dfb`. The pre-install backup is `Backups/20261025-230301/L_CyberpunkApartment.umap`.
- Counter collision is now four convex slabs surrounding the real rounded basin aperture (`aperture_local x [-1.412,-0.617], y [-0.272,0.272]`), replacing the provisional two-wing layout. `sink_aperture: open` is recorded in the receipt.
- Preserved contract comparison passed: twelve native containers, twelve collision records, four refrigerator trim components on their native DoorHinge parents with identity local transforms, and the shared refrigerator shells unchanged. Captions, storage pages, hinge locations/rotations and door parents are unchanged. No geometry or lighting writes outside the kitchen were made.

### Local geometry state at freeze

Component mesh audit (`audit_mesh`, self-intersection on):

| Component | Verdict | Self-intersections |
|---|---|---|
| Counter | pass | 0 |
| BackSplash | pass | 0 |
| Sink | pass | 0 |
| OvenFront | pass | 0 |
| UtilityRail | pass | 0 |
| Dishes | pass | 0 |
| Prep | fail | 238 |
| DiningDressing | fail | 80 |

All eight are closed, manifold and free of boundary/non-manifold edges. The `Prep` and `DiningDressing` counts are a single hidden internal overlap between the revolved solid's bottom cap and its own side wall (inside the glass jar foot and inside the vase mouth). They do not share vertices with the intersecting face, are not on a visible surface, and are not a placement clash between separate objects.

Support scans: `Dishes`, `Prep` and `Sink` pass with zero clash and zero float. `DiningDressing` has zero clash and six sub-millimetre contact gaps (0.5–0.83 mm) on the utensil shafts/heads against the linen mat. Fixture scans run as two real assemblies: the architectural chain (wall → backsplash → rail) passes with zero clash and zero float; the counter-supported prop assembly has zero clash and sub-millimetre gaps.

### Not claimed

This is a saved asset-and-map integration, not gameplay, visual or performance acceptance. No PIE, gameplay test, screenshot, performance capture or visual approval was run in this task. The two residual mesh self-intersection counts above and the sub-millimetre dining contact gaps are recorded as known limitations rather than silently passed. Visual and gameplay acceptance remain with the user.

## Historical V1 receipt — superseded

The following describes the earlier V1 installation and is retained for traceability only.


## Saved authoring and asset work

- `KitchenDetailV1.blend` contains the independent kitchen source; it does not replace the apartment Blender assembly.
- The latest `assembly.json` has 22 actual component rows, including the six preview/reused shell exports; 16 are new UE installation components.
- `assets_saved.json` reached `assets_saved` in `assets-background-04`. It records 22 mesh imports, 23 materials and seven connected PBR normal-property bindings. Every FBX SHA-256 matches the current manifest, including `FridgeLowerDoor` and `FridgeUpperDoor`.
- Imported `BaseFront` and `UpperFront` bounds reach 55.5 cm in local X; the off-panel fastener was moved from outside the right edge to its inset. The new refrigerator trim is no longer overwritten by reused-shell exports.
- The three explicit pure-function/file-contract tests passed under Blender Python. No UE gameplay, PIE, screenshot, performance or visual acceptance was run.

## Map installation is saved — 2026-10-24 23:05:53 +08:00

`level-background-11` completed through the guarded background commandlet route with exit code 0. `map_saved.json` and `installed.json` both report `stage: map_saved` for `/Game/GameMaps/L_CyberpunkApartment`. The formal `.umap` is 1,160,992 bytes, timestamped 2026-10-24 23:05:53 +08:00; its current SHA-256 is `7d49abc03588099e51a60a43352a3885b3fc0ef2e7d4b701fa8cb6ec256e92b7`, matching the receipt. The retained pre-install backup `Backups/20261024-230532/L_CyberpunkApartment.umap` has the old hash `5616890451ef1ce72a87be0a5647a86408cea7f95c3e231bb00ae0795245c41d`.

The saved receipt records twelve native containers, eight fixed-detail actors and four native refrigerator trim components. All 15 placement designations are reconciled: `Cooking` is part of `OvenFront`, coffee/kettle stay on existing actors, and fridge details stay on their native root/hinge. The native DoorHinge parents of both refrigerator door trims are recorded with identity local transforms. The in-installer native contract comparison preserves IDs, captions, pages, hinges, door collision/parents and shared refrigerator shells. The counter asset has four simple collision boxes around an open sink aperture; the old fixed cabinet-run visual is retired without retiring native storage actors. No additional gameplay C++ or global rendering settings were changed.

This is a saved asset-and-map integration, not a gameplay, visual or performance acceptance. No PIE/gameplay test, new screenshot, performance capture or visual acceptance was run. Native component parent and transform fields were read during installation; there was no separate fresh-process saved-map reload audit. The older `ue-scope.json` remains a partially failed scope read: its attempted matrix iteration failed, and it is not a complete post-install contract record. Component-local orientation and actual support/contact in the running scene have not been visually approved; the measured kitchen translation is not a claim of a full local-axis review. Leave those to the user's visual/gameplay review rather than treating `KitchenPreview.png` as final proof.

## Historical installation attempts — superseded by the receipt above

**Historical status, not the current state:** before `level-background-11`, no successful map save or `installed.json` existed. The user freed D-volume space: approximately 160.5 GB was observed available, rising to approximately 206.5 GB during later independent work. Disk capacity was no longer a blocker. Earlier source-asset gates/backups completed, but subsequent Python API errors prevented a map save; retained backups were never installation receipts.

- `level-background-01`: refused because the production project was open. No map script ran.
- `install-editor-01`: refused because PIE was active. No backup, map load or save occurred.
- `install-editor-02`: bridge queue timed out; it did not send the script. No stop-PIE or install action was executed by this batch. The editor then exited through an independently issued `QUIT_EDITOR`; this task did not issue that command.
- `level-background-02`: failed during UE startup because the D volume could not write `Saved/Config/WindowsEditor/EditorPerProjectUserSettings.ini` (Windows error 112). No kitchen script ran.
- `level-background-03`: failed during engine initialization with DDC write error 112 followed by an AssetRegistry worker assertion (`Header.Len != 0`), exit code 3. No kitchen script ran. The attempted per-process cache variables did not route the actual DDC/Zen initialization away from D; this attempt is not a verified cache solution.

At that historical point, `map_saved.json` recorded the `level-background-04` Python failure: the unsupported `StaticMesh.mark_package_dirty()` stopped countertop preparation after its backup. The package-level dirty call and unrelated Transform snapshot API were corrected in later batches. The current receipt is the successful `level-background-11` result above.

- `level-background-04`: waited for independently owned UE game-audit processes; they were not killed or contacted. Once the window opened, the commandlet ran, backed up the formal map, loaded it and stopped before map save. Its full backup is retained under `Backups/20261024-221159/`.
- `subobject-probe-01`: did not run. A newly opened production editor caused the existing background ownership guard to reject another UE process. No script or probe log was created.
- `probe_reflection.py`: after the separately opened editor completed initialization, `probe-reflection.json` and `probe-reflection-response-02.json` returned the live reflected API. The editor was in a newly started PIE; the read did not load or save a map. The actual parameter field is `conform_transform_to_parent`, without a `b_` prefix. Neither `Object.mark_package_dirty()` nor `Package.mark_package_dirty()` is exposed. Save through `EditorAssetLibrary.save_loaded_asset()`/`EditorLoadingAndSavingUtils` instead.
- `probe_asset_api.py`: read the saved kitchen assets without loading a map or saving anything. `probe-asset-api.json` confirms the save-map and object-modify interfaces and non-null Base Color, Normal, Roughness, Metallic and AO input nodes for all seven PBR materials. This confirms saved asset bindings, not map installation.
- `probe_subobjects.py`: the guarded editor attempt reached its `Preserve running game` guard and stopped. It did not load the apartment or create an instance component. The later installer did execute the Subobject add/attach route; see the saved receipt above.
- `level-background-05` through `level-background-10`: corrected hidden-actor, root-component, refrigerator-mesh lookup, EditorActorSubsystem, duplicate coffee/kettle and merged-cooking placement issues in turn. Batch 10 stopped on the absent `SM_KP_Cooking`; batch 11 reconciled that support designation with the actual `OvenFront` mesh before installation.
- `level-editor-05`: bridge request for `publish_level_entry.py` failed before execution because no Python remote node was discoverable. Its response file remained empty and the installer did not run; it did not create a new backup or save the map. The separately opened editor received an independent `QUIT_EDITOR` at 22:38; this kitchen task did not issue that command. The editor entry was changed to refuse PIE without stopping it. `level-background-05` was subsequently submitted through the established background mutex with `publish_level_entry.py` as its explicit main entry.


## Native attachment route and reproduction

The reflected `SubobjectDataSubsystem` route was executed during `level-background-08` in memory and then saved as part of `level-background-11`. Refrigerator door trim is attached to each native `DoorHinge`; body trim is attached to the native root. `Actor.add_instance_component()` and `ActorComponent.register_component()` are not exposed UE Python functions and are not used. The route uses `SubobjectDataSubsystem.add_new_subobject()` and `attach_subobject()` with `SubobjectDataBlueprintFunctionLibrary.get_associated_object()`. The historical `probe_subobjects.py` did not run past PIE, but the later actual installer did reach and save the attachment code.

For a future intended rebuild with no production editor owning the project, use `publish_background.ps1 -ScriptName publish_level_entry.py -RunName <new-run-name>`. The explicit entry calls the installer with `run_name='__main__'`. Both editor and background routes must use their ownership guards; never bypass the bridge mutex, launch a second UE for a loaded project, or stop PIE. The editor entry refuses PIE and dirty maps. No routine reinstall is needed after this successful saved batch.

The installer now verifies every FBX hash and the actual seven normal/PBR input bindings before backing up the formal map. It refuses the wrong map, unexpected container identities and changes to captured native container contracts. Its save path calls `save_map()` directly, checks the returned result, and requires the formal `.umap` SHA-256 to differ from the retained backup before writing `installed.json`.

`spec.py::source_to_ue_cm()` is the sole authoring-source-to-formal-UE conversion: `(100*x+445, -100*y-673, 100*z)` cm, with identity rotation. The old kitchen-source world coordinates must not be used directly in the apartment. The measured counter translation `(890,-1312,0) -> (1335,-1985,0)` cm and all twelve native kitchen/fridge actor anchors agree with it. `SOURCE_CONTAINER_ANCHORS` enumerates those native anchors, including the two searchable old `Base_1`/`Base_4` placements now named `Kitchen_Sink_1`/`Kitchen_Base_4`. Installation rejects an unexpected native anchor instead of moving gameplay actors. Component-local refrigerator trim stays at identity relative to its native root/hinge; only fixed decoration uses the world-space conversion. No FBX re-export is required for this integration-origin correction.

Do not bypass those guards or replace the apartment with the old whole-apartment Blender source. Do not invent `RS_PaintedSteel` as an observed slot: only `RS_Ceramic` and `RS_BareSteel` exterior slots are recoloured. Ivory/plastic/rubber interior slots and native fridge meshes remain unchanged.
