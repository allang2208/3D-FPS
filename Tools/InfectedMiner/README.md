# Infected miner: CMU human motion capture

Use `D:/FPS3D/FPSGAME`, UE 5.8.2 and Blender 5.1. The current route starts from the local user-accepted hand snapshot and replaces the attack only. See [delivery notes](../../Docs/InfectedMiner20260912.md) for provenance, timing, dependencies and recorded evidence.

## Current production route

1. `fetch_realistic_mocap.py` obtains the cached CMU BVH candidates, index and conversion terms. The selected file is `02_07.bvh` (120fps); exact SHA-256 is in `Reference/CMU/sources.json`.
2. `review_cmu_sources.py` renders source joint motion before retargeting; `package_cmu_review.py` packages it. `inspect_cmu_motion.py` records source motion and `inspect_cmu_contact.py` records the target tool path.
3. In Blender background mode run `retarget_cmu_strike.py`. It reads `Review/Hand_UserAccepted_20260912/InfectedMiner_Editable.blend`, preserves mesh/skin/grip, mirrors the original right-hand capture to the left hand and retains the first 2.2s of captured timing. Output: `Candidates/CMU02_07`. No new attack IK or replacement key poses.
4. `review_grip.py -- --cmu --attack --whole-only` renders the actual candidate. `validate_fbx_preview.py -- --cmu --attack-only` combines FBX checks and rendering; run only when the user requests validation. `package_cmu_miner.py` packages existing rendered GIF/MP4 frames without launching tests.
5. Adopt the candidate by copying its editable blend, attack FBX and `attack-authoring.json` into `Delivery`. The hand mesh and other clips stay unchanged. Existing `SK_InfectedMiner_UE.fbx` only selects the authored forearm color layer and is already imported.
6. Build native source if changed. Run `import_mocap_strike.py` in UE Python to import only `A_Miner_CMUStrike`, preserve mesh/materials/physics and save the existing BP attack reference/timing. Assets go to `/Game/Monsters/InfectedMiner/CMU02_07/`.
7. `finalize_mocap_delivery.py` packages hashes and previously recorded evidence. It does not run tests or overwrite Markdown. Old `write_manifest.py` / `write_delivery_docs.py` names now delegate to this packager.

The accepted blend, base-animation FBXs, Manny/VRE references and Fab content are local dependencies, not published binaries. Initial generation/topology scripts do not replace those inputs.

## User testing and optional diagnostics

`Open-MinerVillage.cmd` opens the village. `Open-MinerVillage.ps1 -Isolated` opens the independent scene. Restart an old editor/game process to load new assets. The village spawner is already saved, so an attack update does not require resaving the large map.

Follow current AGENTS: testing is user-operated unless explicitly requested. Optional tools: `validate_accepted_hand.py -- --cmu`, `check_attack_roundtrip.py -- --cmu`, `check_ue_mesh_export.py` and `Open-MinerVillage.ps1 -Audit` (optionally `-Isolated`). `-Audit` uses an isolated save, captures screenshots, writes `Saved/InfectedMiner/acceptance.json` / `play.log`, and exits. Archive reports by the actual animation version; never reuse KayKit passes as CMU evidence.

## Historical files retained locally

`export_donors.py`, `inspect_generated.py`, `build_topology.py`, `rig_animate.py`, `fit_authored_forearms.py` describe initial body/skin construction. `import_assets.py`, `finalize_test_assets.py`, `place_village.py` are initial integration helpers.

`author_attack.py`, `author_power_strike.py`, `refine_grip.py`, `retarget_authored_chop.py`, `update_attack.py`, `restore_previous_attack.py`, `restore_attack_in_ue.py` and `import_power_strike.py` belong to rejected or superseded stages. Do not run them over the current delivery. `fetch_motion_donors.py` and `review_motion_sources.py` refer to the rejected KayKit experiment.

Publish exact source/documentation paths. Do not stage donor checkouts, BVH files, Fab/Epic binaries or previews by directory.
