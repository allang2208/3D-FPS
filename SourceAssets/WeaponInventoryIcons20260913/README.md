# Weapon inventory artwork authoring

Entry point: `Tools/UI/build_weapon_catalog_icons.ps1`.

Targeted re-shoot of one or more weapons without a native rebuild: `Tools/UI/build_weapon_catalog_icons.ps1 -Definitions ue_highland_claymore,ue_frost_crystal_sword`. One process exports one `-Definition=`, so a list costs one engine launch per name; the run is judged by whether the PNG timestamp advanced, not by the process exit code. Targeted runs log to `export-<definition>.log` and back up to `before/<definition>.png`.

The `ColdSteelWeaponIconCatalog` commandlet invokes the same `UColdSteelWeaponIcons` assembly and capture code as the inventory. It creates an uninitialized GameInstance only to satisfy the subsystem's UObject outer; it does not initialize gameplay/profile subsystems or begin play in a map.

Outputs are written to `Content/ColdSteelData/Icons`:

- Canvas follows the item's authored inventory footprint at 320 px per grid row, so image aspect equals slot aspect: 5x2 rifle 800 x 320, 3x2 pistol 480 x 320, 2x4 two-handed blade 384 x 768.
- Framing is one rule on both channels: the dominant axis fills 91% of the frame, and the silhouette centre — not an offset constant — sits at the frame centre (`ColdSteelWeaponIcons.cpp:246`, `ColdSteelMeleeIcon.cpp:36-42`).
- `ue_m1911.png`, `ue_dan_wesson715.png`: 480 x 320. M1911 Hero20260913 mesh, Contact20260913 idle pose, Hero PBR materials.
- `ue_akm.png`, `ue_m4a1.png`, `ue_a762.png`, `ue_m16a2.png`, `ue_ash12.png`, `ue_qbz191.png`, `ue_svd.png`, `ue_pkm_lowpoly.png`: rifles and the machine gun in 5x2 slots. SovietFab/RearGrip20260913, M4HK416Replica and the rest of their runtime meshes and materials.
- Melee `ue_rune_sword.png`, `ue_frost_crystal_sword.png`, `ue_highland_claymore.png`: 384 x 768. `ColdSteelMeleeIcon.cpp` stands the blade up on the longest bounding-box axis.
- Materials `stone.png`, `iron_ore.png`, `copper_ore.png`, `silver_ore.png`, `gold_ore.png`, `ironIngot.png`, `copperIngot.png`, `silverIngot.png`, `goldIngot.png`: 320 x 320 (1x1 slots). `ColdSteelMaterialIcon.cpp` shoots the pickup mesh with its pickup material — see *Production material icons* below.

The footprint rule and the 91% constant live in the capture code, so the catalog PNG and the live inventory image always agree. That rule compiled into `UnrealEditor-FPSGAME.dll` at 2026-09-25 01:58 and the whole gun set was re-exported against it the same morning, so the 5x2 PNGs are now 800 x 320 and match their slots. The per-definition canvas table it replaced (`... ? 480 : 768`) is what let three icons drift: `ue_qbz191.png` and `ue_ash12.png` were foreign 512 x 256 files sitting in 5x2 slots, drawing ~25% and ~18% narrower than their neighbours — and `ue_qbz191.png` also rendered 15% below centre — while `ue_dan_wesson715.png` had no catalog image at all and fell back to a blank slot. `ue_qbz191` was missing from the commandlet definition list, which is how it stayed foreign.

The image is a transparent side view of the current base assembly with arms excluded. Mounted component materials, shader readiness, texture residency, posing, geometry framing and capture are shared with dynamic inventory images. Modified instances continue to render their installed parts at runtime.

`before/` preserves pre-existing catalog PNGs without replacing a prior backup. `export.log` records production output; `build-editor-final.log` records the required native build. Existing GameFeatureData configuration and occupied HTTP service port messages can give the commandlet process a nonzero exit code independently of its image export result; the commandlet separately reports each written PNG and its export failure count.

## Equipment bar orientation

The 随身装备 card (`ColdSteelInventoryPresentation.cpp`, `GearSlot>=0`) spends its left 48% on the slot name, the item name and the 已装备 line, so its image area is a wide strip — about 126 x 68 px at the default panel size. Guns are captured lying down and fill that strip. The melee and tool art is upright (sword 384 x 768, `ProductionTools/axe.png` 256 x 768, `ProductionTools/pickaxe_upright.png` 512 x 768), and the aspect-preserving fit squeezed it into a 23-45 px sliver.

Equipment cards now lay that art down. `FItemPresentation::MeleeArt` is set once in `RefreshPresentation` from the JSON already parsed there — no extra `Item.Data` read per paint frame — and the card reuses the turned-bag-item path, transposed fit plus `MakeRotatedBox`, at -90° so the blade edge or axe head points left the way a muzzle does. At the default card size the sword goes from 34 x 68 px to 126 x 63 px, the axe from 23 x 68 to 126 x 42, the pickaxe from 45 x 68 to 102 x 68.

Nothing else moved: bag cells still draw the same upright art (`GearSlot < 0`), guns and armour are untouched, and no capture, canvas or PNG changed — this is a draw-side orientation only.

## Equipment (gloves and sweaters)

The five `category=equipment` items — `ue_field_sweater`, `ue_field_sweater_charcoal` (3x3) and `ue_field_gloves`, `ue_field_gloves_black`, `ue_original_gloves` (2x2) — are not captured at runtime: `Supports()` is false for them, so their catalog PNG *is* the icon. They are rendered offline by `Tools/ModularOutfit/render_equipment_icons.py` under the same canvas and 91% framing rule, and stay **upright**: `Lay` only fires for `MeleeArt`, so armour cards never get the equipment-bar turn. `ue_original_gloves` shares the brown gloves' pickup mesh and material, so it shares their image. Details and the exposure calibration in `Tools/ModularOutfit/README.md`.

## Production material icons (2026-09-25)



`ColdSteelMaterialIcon.cpp` adds a third capture channel next to the gun rig and `ColdSteelMeleeIcon.cpp`. Materials have no attachments and no assembly variant, so `Key()` is the bare definition and the subject is the pickup object itself: the channel mounts `ProductionHarvestAssets::PickupMesh` and overrides slot 0 with `PickupMaterial`, then normalizes to 24 cm exactly like `AColdSteelPickup::InstallProductionMaterial`, so bag icon and world drop are the same thing seen from the same angle. `ProductionHarvestAssets::IsIconSubject` gates the channel and deliberately excludes `wood`, which already has a correct offline Blender render (`Tools/HarvestTimber/render_wood_log_icon.py`) sized for its 1x2 slot.

Nine subjects, all 1x1 footprints, so all canvases are 320 x 320: `stone`, `iron_ore`, `copper_ore`, `silver_ore`, `gold_ore`, `ironIngot`, `copperIngot`, `silverIngot`, `goldIngot`. Measured after export: dominant axis 90.6-91.2% of the frame, silhouette centre at 0.498/0.498, nine distinct PNG hashes.

Producing them exposed a real asset bug: the four ore icons rendered byte-identical and near-black. `Tools/Smelting/build_ingot_assets_ue.py` had three silently failed material connections — see `Docs/UI/smelting-panel-plan-20260923.md` 7.17. Fixed and re-exported; the world ore pickups were black too and are fixed by the same asset rebuild.

**Pending a build**: the delivered PNGs are shot side-on, which flattens two subjects — the ingot's 24 cm long axis points *into* the camera (it reads as a flat plate) and `Rock_S_02` lies flat (22% frame height). `PrepareMaterial` now poses every material at a fixed 3/4 angle (yaw 30° then pitch 22°, framing on the rotated bounds); weapons keep the side view because attachment silhouettes are the information there. That change compiles clean (action 32/154 of the 10:34 build, zero diagnostics) but never linked: `Source/FPSGAME/Weapons/Bow/` is another session's untracked work-in-progress and does not compile, so `Build-Editor.ps1` fails through no fault of these files. After the module builds again, re-run `Tools/UI/build_weapon_catalog_icons.ps1 -Definitions stone,iron_ore,copper_ore,silver_ore,gold_ore,ironIngot,copperIngot,silverIngot,goldIngot` to match the catalog images to the live capture.

These are derivatives of the project's existing local weapon and material assets. Source model and texture provenance and redistribution restrictions remain those of each weapon's integration records and `Docs/AssetSetup.md`. No external reference images or newly downloaded assets were used.

The image export is the requested artwork production. No gameplay tests or visual acceptance runs were requested or performed.
