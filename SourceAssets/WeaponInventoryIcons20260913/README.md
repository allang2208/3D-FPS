# Weapon inventory artwork authoring

Entry point: `Tools/UI/build_weapon_catalog_icons.ps1`.

The `ColdSteelWeaponIconCatalog` commandlet invokes the same `UColdSteelWeaponIcons` assembly and capture code as the inventory. It creates an uninitialized GameInstance only to satisfy the subsystem's UObject outer; it does not initialize gameplay/profile subsystems or begin play in a map.

Outputs are written to `Content/ColdSteelData/Icons`:

- `ue_m1911.png`: 480 x 320, M1911 Hero20260913 mesh, Contact20260913 idle pose, Hero PBR materials.
- `ue_akm.png`: 768 x 320, SovietFab/RearGrip20260913 mesh and its runtime materials.
- `ue_m4a1.png`: 768 x 320, M4HK416Replica mesh and its runtime materials.

The image is a transparent side view of the current base assembly with arms excluded. Mounted component materials, shader readiness, texture residency, posing, geometry framing and capture are shared with dynamic inventory images. Modified instances continue to render their installed parts at runtime.

`before/` preserves pre-existing catalog PNGs without replacing a prior backup. `export.log` records production output; `build-editor-final.log` records the required native build. Existing GameFeatureData configuration and occupied HTTP service port messages can give the commandlet process a nonzero exit code independently of its image export result; the commandlet separately reports each written PNG and its export failure count.

These are derivatives of the project's existing local weapon assets. Source model and texture provenance and redistribution restrictions remain those of each weapon's integration records and `Docs/AssetSetup.md`. No external reference images or newly downloaded assets were used.

The image export is the requested artwork production. No gameplay tests or visual acceptance runs were requested or performed.
