# AKM optics and muzzle reuse — 2026-09-11

Archive update (2026-09-11): superseded files mentioned below now reside under local `trash/akm-optics-workflow-20260911/SourceAssets/AKMOptics20260911`. The per-file manifest is `Docs/Weapons/akm-optics-archive-20260911.json`. Final sources and accepted run folders remain in place. Historical failed iteration paths are evidence references, not active reproduction inputs.

Historical integration record: the bridge geometry below was superseded by `../AKMBridgeRefine20260911`, and optic body/ring materials by the AKM-only variants in `../AKMOpticSteel20260911`. The counts below describe that earlier accepted run.

Integrated the production M4 panoramic red dot, machined 2× prism scope and 1–6× LPVO into the AKM gunsmith catalog. The optics reuse their actual production meshes and materials. Three dedicated AKM bridges accommodate their different mounting footprints and eye positions; optics remain at their authored physical size.

## Fit and materials

- `mounts.json` records root-space placement and support dimensions. AKM root uses meters; shared static meshes use centimeters, relative scale 0.01, and a 90-degree yaw to align their forward X with AKM forward Y.
- Bridge lengths are 72 / 70 / 84 mm, with individual longitudinal placement. Each bridge is 540 triangles, supported on the receiver and assigned the existing accepted `M_AKM_Soviet_MountSteel` material derived from the Soviet AKM Fab source. No new externally sourced texture or license is introduced.
- The original block-bridge Blend/FBX are archived; current editable assemblies and bridge exports are in `../AKMBridgeRefine20260911`. The superseded block-bridge builder and importer are archived; use `../AKMBridgeRefine20260911/build_mounts.py` and its importer for current production bridges. LPVO's moving ring remains the separate official runtime asset.
- Current suppressor, brake and titanium brake were already available on AKM. `import.json` verifies matching production M4 triangle counts and identical material asset assignments. Their existing AKM-aligned geometry is retained. Muzzle VFX/projectile origin now uses the bore center rather than an asymmetric mesh-bounds center.

## Runtime behavior

AKM selects the new optic and bridge together; removal hides the bridge, weapon teardown destroys it, and the LPVO retains its magnification ring and existing scope presentation. ADS calibration distinguishes the baked AKM holographic mesh (local Y forward) from these shared optics (local X forward). No hand animation assets or reload timing are changed by this task.

The new catalog entries use the existing inventory, icon, pickup, gunsmith draft/apply/save and attachment stats paths. The audit seeds isolated profiles; it does not edit the player's normal inventory/save.

## Verification and reproduction

Final acceptance: **502 checks, 0 failures** across seven successful runs. Panoramic write/reload: 58/54; prism write/reload: 59/55; LPVO write/reload: 116/112; three paired muzzles: 48. Optic center error is at most 0.0001 pixels in sampled LPVO zoom checks, actual zoom ratios are 1/2/4/6 as requested, and all three muzzle axis errors are 0.00000 cm at logged precision. Visually reviewed actual workbench, ADS and combination captures. This is rendered game-process validation, not validation of an already-open user editor.

`build-native-final.log` and `build-audit-pairs.log` record successful native builds. `import.log` contains `AKM_OPTICS_IMPORT_PASS`; the commandlet's unrelated startup errors are not treated as a clean process exit.

Run `run.ps1 -Kind panoramic|scope2x|lpvo -Run <unique-name>`, then the same invocation with `-Reload` for a fresh-process save load. Run `-Kind muzzle` for the three combinations: panoramic + suppressor, prism + brake, LPVO + titanium brake. All use the actual DayNight_Lighting game map, offscreen rendering, independent saves and 1600×900 screenshots.

Results and captures are in the three optic `<kind>-v1/` folders and `muzzle-v3/`. `collect_results.py` aggregates their completion records into `acceptance.json`. The audit retains historical `M4_GUNSMITH` log labels and screenshot filenames; `-AKMOpticAudit` selects AKM assets, ammo, instances and a separate output folder. These labels do not imply the screenshots are M4.

The initial `muzzle-v1` run exposed assumptions in the inherited M4 test: applying during AKM equip/reload was correctly rejected by gameplay, the old muzzle socket was not the Soviet mesh's calibrated bore point, and AKM uses `PlaySound2D` rather than the dedicated M4 audio component. The AKM audit now waits through its actual actions, uses its calibrated origin, and checks available audio assets/routing while retaining the gameplay recording. `build-audit-timing.log` records that audit correction; production action timing and sound playback are unchanged.

`muzzle-v2` passed 47/48 checks; the remaining check used a generic M4 extension limit of 15 cm. Source geometry in `../M4Muzzles20260910/build.json` specifies lengths 18.6 / 6.8 / 7.25 cm, mounted at AKM Y=57.7 cm against barrel tip Y=58.02467465 cm. The final audit compares against those independently measured dimensions within 0.05 cm, rather than increasing an arbitrary limit. Expected extensions are 18.27532535 / 6.47532535 / 6.92532535 cm. `build-audit-fit.log` records the final successful compilation.

An already-open editor must be restarted to load the rebuilt native module. Existing parallel source/data edits have been preserved; the original integration step did not commit or push; the later workflow publication is documented in `Docs/Weapons/akm-optics-workflow-20260911.md`.
