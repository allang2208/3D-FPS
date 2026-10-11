# Super90 Loader R14

User rejected R13 for losing the visible push in both partial and empty reloads. R14 samples the immutable R12 preview Blend and matching grip profiles. It changes the clock, not the authored spatial path. Every count retains the full push, with ammo committed on its final N contact points.

- `extract_reference_camera.py`: reads existing user-video frames and writes `reference_camera.json` (screen translation/roll, not a 3D camera solve).
- `prepare_timing.py`: writes the common monotone timing map and measured camera tables, including `Source/FPSGAME/Weapons/Super90LoaderCameraReference.h`.
- `author_r14.py`: writes the editable R14 Blend, 15 animation FBXs and four grip-profile JSON files from R12 baked input. No IK/mesh changes or renders.
- `run_r14.ps1` / `import_r14.py`: save the 19 animation/profile packages through the existing editor or background commandlet. `import_receipt.json` records actual completion; backups are under `Before/`.
- `livecoding-final-result.txt`: final patch application to the running editor. `build_r14.ps1` is the normal Editor/Game build entry, only when binaries are not occupied; a live patch does not establish a base build.

Full phase, mechanics and camera limitations: `../../Docs/Weapons/super90-speedloader-r14-preserved-push-20261009.md`. No game tests or new preview renders were requested or performed.

Saved: `import_receipt.json` completed with 19 animation/profile packages. Both normal Editor and Game builds completed successfully in batch 20261009-205347 (`build_receipt.json`); the two earlier successful Live Coding patches are no longer the only integration. The fully saved, non-PIE editor was normally closed for the persistent clock build, and was not reopened afterward.
