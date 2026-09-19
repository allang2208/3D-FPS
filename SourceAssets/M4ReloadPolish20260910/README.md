# M4 reload and equip polish — 2026-09-10

This pass keeps the M4 mesh and accepted authored arm-chain deformation. It adjusts standard reload, empty reload, and equip only.

## Final runtime changes

- Empty reload: faster last approach to the bolt release, short contact arrest and faster rebound. Contact remains at source frame 130/60 = 2.166667 s. The final 9 source frames now play in 4 frames (66.7 ms). A small receiver reaction (2.5 mm and 0.8 degrees) moves the complete rig coherently.
- Magazine insertion: shift the grasp 8 mm toward the magazine base, curl left index MCP/PIP by 40/20 degrees relative to the former grasp, adjust thumb PIP by -3 degrees. Maintain grasp through seating; preserve the authored internal arm relationships and finger lengths.
- Bake fractional keys at 240 Hz to stop hand/magazine slipping between source poses. Keep this sampling rate when reimporting; 60 Hz resampling reintroduces transient insertion errors.
- Equip: gameplay duration 0.62 -> 0.72 seconds (16.1% longer). Source animation remains 0.633333 seconds and is played at source length / gameplay duration. HK416 equip audio is stretched with pitch preserved. It still starts at the weapon's own hip position and ends directly in idle.

## Runtime and editable resources

Production animation/audio references now point to `/Game/Weapons/M4ReloadPolish/`. The old files were locked by the user's open editor, so they were retained unchanged and the new assets were saved to this separate folder. This is the folder used by the updated native module, not an unconnected candidate.

- `A_M4_HK416_reload`: 2.1 s, 505 sampled keys.
- `A_M4_HK416_reload_empty`: 2.7 s, 649 sampled keys.
- `A_M4_HK416_equip_charge`: 0.633333 s source, 153 sampled keys.
- `S_HK416_Equip`: stretched equip sound, FORCE_INLINE.
- `CR_M4_Polish` and `LS_M4_Polish_reload`, `LS_M4_Polish_reload_empty`, `LS_M4_Polish_equip_charge`: editable FK Control Rig sequences for MAT, display rate 240 fps. Empty-reload strike is frame 520 in these sequences.
- `M4_Hand_MAT_Editable.blend`: editable authored source. `repair_authored.py` and `fitted_grip.json` reproduce the three exported FBXs. Blender timeline stays 60 fps with quarter-frame keys.

MAT uses the custom FK controls established in the earlier hand repair. This pass does not claim MetaHuman-specific IK/finger automation. Authoring and numeric contact correction are retained in the Blender source, with the final curves baked into MAT-compatible sequences.

## Evidence

The first AV capture (`m4-polish-av60`) had a multi-second stall and failed waveform validation. It was rejected for delivery. The fresh `m4-polish-av60-final` run passed both gameplay and waveform checks; delivery uses this run.

- Native build `compile3.log`: Succeeded, module 2026091063.
- Fresh editor reloaded saved animation assets and asserted all sampled-key counts before baking sequences: `mat_build2.log`, `mat_sequences.json`.
- Real rendered game, isolated validation map, simulated input: `m4-polish-av60-final` 50 checks passed; `m4-polish-equip` 21 passed; zero failures. Equip audit includes the new 0.72-second duration and hip/switch/interruption checks.
- `polish_validation.json`: insertion sampled at 480 Hz, 249 normal and 193 empty samples; maximum locked wrist drift 0.3353/0.1045 mm. No tested glove vertices entered the sampled magazine outer envelope. This is a vertex/envelope check over insertion, not a universal triangle collision proof.
- `surface_validation.json`: final slap receiver-side clearance minimum 0.4300 mm; at contact, side clearance 1.5002 mm and catch-surface distance 1.4214 mm.
- `publish_report.json`: raw-versus-compressed sampled bone error below 0.01 cm; correct persisted asset hashes.
- Actual mixer recordings correlated against HK416 source cues and stretched equip sound: `audio_validation_m4-polish-av60-final.json`, `equip_audio_validation.json`. Eleven reload cues identified, fire attack identified, no clipped audio samples.
- `Delivery/`: actual runtime videos with audio from the same runs. Export is 20 fps; missing screenshot indices hold the previous image (exact counts are listed in the manifest). These are visual/audio previews, not an FPS benchmark. Frame and audio origins are recorded in `preview_manifest.json`.

The old user editor was kept open. Restart the UE editor to load the new native module and resource paths; an already-open editor continues using its loaded module.

## Reproduce

1. Run `repair_authored.py` in Blender 5.1 with factory startup, then `validate_polish.py` and `validate_surface.py`.
2. Run `publish.py` through UE Python; check every save result. Import sample rate is 240.
3. Run `build_mat_sequences.py` in a full editor (Sequencer/Control Rig requires Slate).
4. Build the native module and run `run_validation.ps1` with fresh labels; use `-EquipPreview` for equip acceptance.
5. Run audio checks and `make_delivery.py` for the corresponding recorded labels.

`Before/` contains the scoped original native files and old assets. `import.log` records the rejected overwrite attempt; `import2.log` is the successful separate-folder import. Commandlet exit status includes unrelated pre-existing project GameFeatureData errors, so persistence was independently verified by fresh full-editor readback and runtime tests.
