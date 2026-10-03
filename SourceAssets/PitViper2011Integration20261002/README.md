# Pit Viper 2011 production source

Source model: [Low Poly TTI JW4 Pit Viper 2011, D_U](https://sketchfab.com/3d-models/low-poly-tti-jw4-pit-viper-2011-2daaf7fe78604ee7941a4ad5fd4d0153), CC BY 4.0.

Official Download API source is in `Original/PitViper2011_Official.glb`; download receipt and live license metadata are retained. No API credential or temporary download URL is saved. Preserve `Original` and the separate project donor source branches.

Rebuild order: `read_download.py`, Blender `prepare_geometry.py`, `prepare_authoring_recipe.py`, Blender `author_pit_viper.py -- single|r|l`, `prepare_delivery.py`, then `import_assets.py` through the project headless authoring launcher. Runtime routing is captured by `connect_runtime.py`; source copies before this task are under `BeforeSource`. Native build entry is `build_editor.ps1`.

Geometry keeps source UV0, split normals and mechanical part identity. Source dimensions use the author-provided 9mm cartridge to establish metres. The held factory scene uses the fitted 15-round magazine and its top cartridge; spare loose rounds and spare magazine remain in the original source only. Arm bone reference matrices and native V7 skin weights stay on their original donor chain.

`finish_recipe.json` defines per-slot private instances of the shared WeaponSurface Clean presets. Copper and brass retain intentional coloured metal; the front sight uses a small nonmetallic emissive material. The source contains no textures; shared mother material provides physical micrograin and wetness. No shared master or preset is rewritten.

Single and each dual hand have their own skeletal mesh, skeleton and baked action family. Production action durations, donor actions and contact adaptation are in each `authoring.json`. Imported package paths, actual saved assets and source audio bindings are in `import_receipt.json`. Catalog and build outcomes are recorded separately.

The subsequent M1911-based firing upgrade is produced in `../PitViper2011Fire20261002`. Canonical authoring now samples the complete native fire action and blends it locally with `fire_motion.py` before contact adaptation, instead of substituting a frozen idle pose. The recipe generator retains this correction. Hip/dual fire lasts 0.35 seconds and ADS lasts 0.30 seconds; firing cadence remains separate. That batch's delivery/build receipts supersede the earlier native build status below for the new timing changes.

Animation sharing is now saved in four fitted/long profiles for the two dual hands. They replace playback references to 16 full quick-combat variants with the existing bases plus sparse pose deltas. The 59 authoring sequences remain available; 43 sequences make up the remaining independent full-clip family. `run_import.ps1` refreshes these profiles after animation reimport. Production receipts and the reusable batch entry point are in `SourceAssets/WeaponAnimationSharing20261002`; this does not imply a Cook-size or runtime-test result.

No game, PIE, runtime visual test, acceptance screenshot or acceptance render is performed. The production catalog PNG is an actual deliverable.

Actual asset import and catalog publication completed through the already running editor's existing bridge. After the user closed UE, `build_editor.ps1` completed the regular `FPSGAMEEditor Win64 Development -Module=FPSGAME` build with `Succeeded`; `UnrealEditor-FPSGAME.dll` was linked and saved. Total build time was 75.33 seconds; the log is `Saved/BuildEditor/pit-viper2011-20261002.log`. The earlier two `CompileNotStarted` Live Coding outcomes are historical. No editor, game or PIE was started, and there is no lingering build queue. See `build_receipt.json` and `delivery_receipt.json` for the saved build and asset status; runtime behavior remains for the user to test.
