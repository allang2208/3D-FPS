# Bow sight/contact V11

This batch retains the wooden longbow, V7 arm mesh/skin, original audio and gameplay timings. It changes the support shoulder/elbow pose, distributes left upper-arm roll to avoid the inner-elbow skin fold, and adds an original open mechanical sight fitted to the riser.

Reference: user-provided Bilibili BV1jGdDBkEkc, 33–48 seconds; the already saved 39-second frame was used for the open mechanical sight layout. The fitting geometry was made locally; no mesh or texture was extracted from the video. Existing bow, arm and animation sources retain their respective provenance in `SourceAssets/DarkBow20260925`.

Run `author_actions.py` and `author_sight.py` with Blender background to create editable Blend and FBX files. `author_actions.py` creates `generated_actions.py` from the retained V10 implementation and scoped replacements. `inspect_deformation.py`, `measure_pose.py -- --after`, and `fit_elbow_roll.py` record the user-requested source diagnosis; they do not launch a game or render.

`import_assets.py` runs through the existing UE bridge mutex or the established headless commandlet. It creates only this batch's asset names, and may reimport owned animation assets when their FBX hashes change. It records saved assets and imported sight dimensions/pin coordinates. `install_config.py` activates the saved assets and revision 22 while retaining unrelated current catalog fields. `run_pipeline.ps1` builds, imports and activates without opening the editor or running the game.

Runtime destination: `/Game/Weapons/DarkBow20260925/SightContactV11`.
Report: `Docs/Weapons/dark-bow-sight-contact-v11-20260926.md`.
No gameplay or visual acceptance has been performed.
