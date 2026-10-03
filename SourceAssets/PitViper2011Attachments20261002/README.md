# Pit Viper 2011 common accessories

Production order:

1. Run `author_parts.py` with the project Blender executable in background mode. It fits existing approved common pistol bodies to the native Pit Viper frame, exports 11 FBX meshes plus editable blends, and saves `authoring.json` with input paths and socket definitions.
2. Run `run_import.ps1`. The existing UE batch mutex and bridge/commandlet launcher preserve active project work. `import_assets.py` saves meshes and materials first, then promotes existing images to shared icon keys and publishes only this weapon's catalog row.
3. Run `build_editor.ps1` for the required native module build. It waits for existing commandlets/builders and does not open or close an editor.

Reused image assets are copied once to shared keys; no image generator or renderer runs. Geometry, metal/optical material separation, emitter/outlet sockets and native mesh-section replacement are independent of the shared UI image.

Asset root: `/Game/Weapons/PitViper2011/Attachments20261002`.
`catalog.json`, `import_receipt.json`, and `build_receipt.json` record production results. No game run or acceptance test is performed by this pipeline. See `Docs/Weapons/pit-viper2011-common-attachments-20261002.md`.

2026-10-03: the three shared grip patterns now use the native longitudinal grip-body surface authored in `../PitViper2011CommonLongitudinalGrips20261003`. `authoring.json.GripSurface` points to its FBX and editable Blender. The lower edge follows the slanted native palm seam and excludes the magazine, baseplate and magwell. UV0 retains physical 0.1 m tiling; existing quiet materials, statistics and shared icons are retained. Only the existing grip mesh was reimported and saved; no native build or game test was required for this geometry change. See that batch's `import_receipt.json`. Full accessory authoring calls its producer last to retain this outline.
