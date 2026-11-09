# M249 ADS obstruction investigation — 2026-11-08

Status: reproduced with the player's saved ST6 clothing, then corrected with M249-specific ADS eye distance. The LPVO and KV after-captures show clear centered apertures with the same worn equipment. Optic geometry, materials and rail mounting transforms were not changed.

## Root cause and correction

The shared rifle eye relief placed the M249 too far forward with its long rear eyepieces. The LPVO used 28 cm; KV calibrated at its initial 1x value used 26 cm. With the ST6 sleeve follower, this brings upper-arm cloth into the camera and covers the scope. It does not occur in the bare-arm diagnostic configuration.

`M249OpticCoordinates::EyeDistanceCM` now returns a fixed 16 cm for those two optics. `UpdateADSPose` uses this only for the M249. The resulting native rig forward offsets are approximately 15.8 and 16.7 cm, close to the clear prism/other optic poses (13–17 cm), instead of the obstructed 27.8 and 26.7 cm. The optic frame still aligns from its actual rear/front/up sockets. Weapon, hands and sleeve retain their shared pose and grip contacts. No arm/garment hiding or opacity workaround was added.

## Expanded checks requested by the user

- `all-optics-20261108_133454/`: 49 captures from 17 configurations: all 8 M249 optics (factory plus 7 common), LPVO 1/6x, KV 1/4x, thermal 1.5/3/8x, and 5 attachment combinations covering the 18 new common parts. Eight optics include entry, confirmed bipod deployment, release and re-aim frames. No large obstruction reproduced without the worn shirt.
- Read-only inspection of the latest `ColdSteelPlayer_PIE_0_B.sav` found the M249 configured with `prism_scope_2x`, and the character wearing ST6 sleeves, special duty backpack, smoke grey capri, casual sneakers and melee combat belt. The source was copied to `source_profile_readonly.sav`; original saves were not written.
- `outfit-before-20261108_134304/`: all 8 optics with those exact worn item records copied into a private profile. LPVO and KV reproduce the large cloth obstruction; the other six apertures remain clear.
- `outfit-after-20261108_134806/`: completed 8/8 with the same worn equipment after the ADS correction. All eight apertures were visually inspected; the LPVO/KV cloth obstruction is gone and their reticles remain centered. `capture.json` records `complete: true`, physical lens state and the worn skeletal mesh paths.
- `build_editor_receipt.json` / `build_game_receipt.json`: normal Editor and Game build receipts. These are compilation evidence, separate from the explicit visual captures.

## Initial captured condition

- Current project assets; M249 with factory body parts, stable ADS, standing, no bipod deployment or reload.
- LPVO at 1x and 6x, KV at 4x, and the native rear optic.
- Background `UnrealEditor-Cmd -game -RenderOffscreen`, separate temporary profile and UserDir. No editor GUI or user profile was opened or modified.
- `clear-background-20261108_132604/`: four completed screenshots and `capture.json`, looking toward clear sky to distinguish weapon obstruction from world geometry.
- The captured apertures are clear in this condition. Common optics report physical lens presentation active and all three native optic sections hidden. Native optic sections are restored for the factory case.
- Earlier `before-20261108_132014/` pictures face a circular practice target. Those world target rings are not evidence of an optic obstruction.

## Additional targeted observations

- Current optic meshes/material slots/sockets were exported read-only (`inputs.json`).
- Offline aperture rays found no opaque obstruction ahead of the LPVO/prism rear glass. KV rays close to the nominal aperture edge intersect its own shell; its center and the actual captured aperture are clear. This does not establish the reported fault.
- Bounding boxes of the 18 newly fitted common parts do not overlap the LPVO/KV eye-to-ocular region in the bind-pose calculation. This is not a check of every animated/loadout combination.
- No multiplayer, reload, every clothing type or exhaustive Cartesian attachment-combination regression was performed. The later scoped motion checks are listed above.

## Diagnostic support

`ScopeScreenshotAudit.cpp` accepts `-ScopeScreenshotAudit -M249OpticObstruction` for the 17 configurations. `-M249OpticEquipment=<copied sav>` instead selects the 8 worn-equipment cases and reads only equipped clothing/gear from that source. Captures record physical glass/native-section state, zoom, bipod state and visible skeletal meshes. The existing default cases remain intact; ordinary startup does not enable this tool. `capture.ps1` runs this explicit diagnostic with batch mutual exclusion.

All runtime captures ran offscreen with a separate profile and UserDir. The editor GUI was not opened. Final interactive acceptance remains with the user.
