# Bow nock continuity V21

User-requested right-hand nocking refinement. Preserve 0.20 s quick entry, interruptible release/recovery, original hand/rig, arrows and ADS configuration.

Production: Blender background `author_actions.py` → `run_build.ps1` → `run_import.ps1` → `install_config.py`. The build updates the base Editor DLL; the import saves three independent animation assets on the current Bow skeleton. No game launch is part of these scripts.

`Bow_NockContinuityV21.blend` is the editable source. `Export` holds Nock, QuickNock and ChainNock FBXs, baked at 240 Hz. `authoring.json`, `import-receipt.json`, and `install-receipt.json` record authored and saved work.

The source retains V16/V15 anatomy, accepted V7 bare arms, fitted string hooks, and the existing licensed donor motion. New carry trajectories, wrist/finger timing and handoff logic are local edits; no new external motion assets were downloaded.

`inspect_motion.py` evaluates source contact continuity and adjacent endpoint poses for the specific reported issue, recording `motion-analysis.json`. It is not gameplay or visual acceptance. No game or acceptance render was run.

Full record: [bow-nock-continuity-v21-20260927.md](../../Docs/Weapons/bow-nock-continuity-v21-20260927.md).
