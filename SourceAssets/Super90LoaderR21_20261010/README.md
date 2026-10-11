# Super90 loader R21

Production update based on the R20 editable source. Adds small shouldered load responses, a delayed right-forearm reaction, a smaller delayed camera response, and a cupped charging-handle grasp. R16 timing/audio and R19 full-ammo fill remain unchanged; R20 shoulder clearance stays in the base.

Rebuild the author inputs with Blender `prepare_hand.py`, fit the hand with Python `fit_grasp.py`, then run Blender `author_r21.py`. `motion.py` is the shared weapon/camera authoring curve. Python `prepare_camera.py` regenerates the existing camera reference header; do not change the source-clock mapping separately.

`Exports/`, `Super90_Speedloader_R21.blend`, four `*_profiles.json`, `grasp_target.json`, and `camera_curves.json` are retained authoring inputs/outputs. `Before/` contains the previous target packages and camera header.

`build_receipt.json`: Editor and Game builds completed. The first completed import mistakenly saved animation packages under `Speedloader21261007`, while runtime and profile bases use `Speedloader20261007`. Its receipt and script are retained under `PathFixBefore/`; that save was not a completed runtime integration. `import_r21.py` now targets the correct stable runtime directory. The corrected import completed with 19 saved assets; see `import-commandlet-20261010-111457.log` and the main `import_receipt.json`. Each profile retains 15 other entries and has 30 entries after loader replacement. No native code was changed by the path repair.

R22 supersedes only this revision's camera authoring. Do not run `prepare_camera.py` here over the current R22 camera header. The R21 weapon/arms/grasp FBX and profile sources remain current.

No preview, gameplay run, or test was performed for R21. User evaluation remains pending. Detailed project record: `Docs/Weapons/super90-speedloader-r21-response-grasp-20261010.md`.
