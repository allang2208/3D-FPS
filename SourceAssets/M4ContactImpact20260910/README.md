# M4 contact and impact revision — 2026-09-10

## Diagnosis

The user's previous version was applied: editor PID 41756 loaded module 2026091071 containing the M4ReloadPolish path, and live ObjectTools read 505 keys / 2.1 seconds from the normal reload asset. This was not a stale-version explanation.

The previous insertion-only test missed hand withdrawal: normal frame 107 had ~12.87 mm magazine-envelope penetration. Empty-reload withdrawal and pre-strike lift also crossed the magazine. A support-palm overlap at the magazine rim existed at the idle reference and action boundaries. Faster local wrist velocity alone did not create a clear camera-visible impact.

## Final behavior

- Approach the magazine from below its base; keep the fitted grip while inserting and seating.
- Withdraw downward past the magazine base, then move outside before returning to the handguard or lifting for the slap. Avoid diagonal shortcuts through the magazine.
- Move the support grip forward along the handguard by 12 mm. Carry the identical offset into idle, aim, fire, aimed fire, equip and reload endpoints; the arm's internal authored joint relationships remain intact.
- Empty reload: visible 120 mm wind-up, fast final swing into the original frame-130 contact, one-frame arrest, receiver response of 8 mm sideways / 2 mm down / 3.5 degrees, followed by rebound. Standard empty-reload bolt-release sound is 1.25 times its previous volume at the same cue time.
- Normal/empty source and gameplay durations remain 2.1 / 2.7 seconds. Equip stays 0.72 seconds; its stretched, pitch-preserved audio remains from M4ReloadPolish.

## Runtime application

Final resources are in `/Game/Weapons/M4ContactImpactFinal/`. The earlier M4ContactImpact folder contains intermediate candidates and is not the final runtime path. Existing assets became locked by the open editor, so the final resource set was saved before changing native references.

`FPSGAMECharacter.cpp` loads all seven final animation clips, and logs `M4_CONTACT_IMPACT_ACTIVE` with the exact reload path and successful load status. Build `compile_final.log` succeeded (module 2026091083). Both fresh runtime recordings logged the Final paths with loaded=1. The user's editor still had module 2026091071 at the last check and must be restarted to use this revision.

The change adds no public Blueprint API or network behavior. Loaded clips remain owned by the existing character animation pointers. The existing single-player reload state machine, audio cue clock, ammunition transaction and action blending remain in charge. Standard and drum reload assets remain separate; drum clips were not rewritten.

## Validation

- Full reload hand/magazine triangle sweep at 120 Hz: 253 normal + 325 empty poses, zero intersecting triangle pairs (`triangle_contact_probe.json`). The hand triangles include faces touching selected left palm/finger vertices. This is not a whole-character / every-weapon collision claim.
- Post-insertion through final recovery at 480 Hz: 449 normal + 777 empty samples; zero tested glove vertices inside the magazine envelope. Grip-locked drift stays <= 0.3353 mm (`polish_validation.json`). The velocity comparison in that file uses the earlier M4HandMATRepair reference, not the immediately preceding polish revision; the comparison video uses the actual preceding polish revision.
- Actual receiver-side glove clearance at the strike: approximately 1.5 mm; catch surface distance approximately 1.42 mm (`surface_validation.json`).
- UE import kept 240 Hz action sampling and checked raw/compressed poses. The support clips are derived from the prior live UE clips by changing only the left clavicle translation track. The imported weapon root has scale 100, so the measured weapon-space offset is transformed with scale into UE centimetres (`publish.py`, `publish_report.json`).
- Real game input tests: `m4-contact-av60` 50 pass / 0 fail; `m4-contact-equip` 21 pass / 0 fail. Both test processes exited 0. Actual mixer recording identified all 11 reload cues, the fire attack, and stretched equip sounds; no clipped samples.
- MAT-compatible FK sequences: `CR_M4_ContactImpact`, `LS_M4_ContactImpact_reload`, `LS_M4_ContactImpact_reload_empty`, `LS_M4_ContactImpact_equip_charge`, 240 fps in the Final folder. Separate fresh-process readback verified 459045 / 589941 / 139077 stored keys (`mat_saved_validation.json`).
- The first MAT build required explicitly opening Sequencer. The successful bake helper later crashed during editor shutdown after saving. A separate fresh readback verified the saved sequences; future build script explicitly closes Sequencer before exit. This shutdown failure is not counted as a successful editor process run. Runtime game processes passed normally.

## Editable sources and previews

`M4_Hand_MAT_Editable.blend` and the three FBXs contain the final authored actions. `repair_authored.py`, `fitted_grip.json`, and `release_path_clearance.json` reproduce them from the retained authored source. `publish.py` imports actions and applies the matching support offset to the four UE base clips; `build_mat_sequences.py` creates editable FK sequences for MAT.

`Delivery/M4_插匣与拍击_前后对比.mp4` compares the preceding polish run on the left and this revision on the right at equal playback speed; audio comes from the current run. It cuts to insertion withdrawal and empty-reload impact. The two full runtime videos include actual mixer audio. They are 20 fps screenshot-based previews: missing screenshot indices hold the previous frame (5/284 normal action-preview frames, 10/144 equip-preview frames). See delivery manifests for exact time alignment. They are not FPS benchmarks.

## Reproduce

Run the Blender build, full-magazine/triangle/contact checks, UE publish, and native build. Use fresh labels with `run_validation.ps1` for audio/frame capture and equip checks. Run audio validators before creating delivery videos. Do not judge publication from commandlet exit status alone: this project emits pre-existing GameFeatureData errors; check save results and fresh readback. Avoid overwriting assets held by another editor.
