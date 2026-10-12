# Pistol catalog icon normalization (2026-10-06)

Backpack/quickbar showed pistols at mismatched sizes: `ue_g18.png` (1024×1024) and
`ue_pit_viper2011.png` (512×512) used square canvases while the rest of the pistol
family follows the footprint rule — 3×2 slot → 480×320.

Fix: re-exported both through the shared capture pipeline
(`Tools/UI/build_weapon_catalog_icons.ps1 -Definitions <name>`, one engine launch
per definition). Canvas is now 480×320 with the dominant axis filling ~91% and the
silhouette centred — identical framing math to `ue_m1911.png` (480×320, 90.8%×85.0%):

| icon | canvas | content | dominant fill |
|---|---|---|---|
| ue_m1911 | 480×320 | 436×272 | 90.8% W |
| ue_g18 | 480×320 | 378×291 | 90.9% H |
| ue_pit_viper2011 | 480×320 | 418×291 | 90.9% H |
| ue_dan_wesson715 | 480×320 | 436×228 | 90.8% W |
| ue_rsh12 | 480×320 | 436×210 | 90.8% W |

G18/Pit Viper are height-dominant (stockier silhouettes); that fill is the same
`OrthoWidth = max(Size.Y, Size.Z*Aspect) / .91` rule the runtime capture uses, so
the catalog PNG now agrees with the live icon instead of letterboxing.

`.uasset` twins re-imported headless (`-run=pythonscript import_icons.py`) with the
same texture settings as the RSH12 icon batch: sRGB, TC_EDITOR_ICON,
TEXTUREGROUP_UI, no mipmaps, never_stream. Receipt: `import_receipt.json`.

Pre-normalization copies of the two PNGs are preserved in
`SourceAssets/WeaponInventoryIcons20260913/before/` (by the export script) and
`D:\FPS3D\_icon_probe` (session scratch). Production logs:
`export-ue_g18.log`, `export-ue_pit_viper2011.log` under that folder.

Not gameplay-tested per standing rules; the PNG itself is the runtime icon source.
