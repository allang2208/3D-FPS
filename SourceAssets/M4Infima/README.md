# M4 + Infima FPS arms integration — 2026-09-09

## Sources
- User-selected Fab template: https://www.fab.com/listings/6a0af880-2b74-480c-a82c-8e597918dffe (Infima Games, Free FPS Template & Tutorial).
- Local archive: C:/Users/allan/Downloads/blender_source_files_freefpstemplate.zip. Original files extracted under Original/; retained without edits. Apply the source package's license; this record does not relabel it CC0.
- User-provided M4: D:/FPS3D/FPSGAME/Content/m4noskel.fbx and its textures. Selected Kmode handguard, classic stock, default grip, light magazine, straight trigger and flash hider.

## Runtime
- FPSGAMECharacter.cpp selects /Game/Weapons/M4InfimaV3/SK_M4_Infima and animations in the same folder.
- bUseM4Infima is exposed in class defaults; false restores the previous asset path. Previous character files are in trash/M4Infima-before-20260909.
- Arms use the Infima Manny mesh and source skin weights. Evaluated source animation is baked into an export skeleton; this is not a claim that the source control-rig hierarchy is unchanged.
- Mesh and animation are centimetre-normalized at runtime. Raw FBX animation track positions require a 100x factor in the existing ADS extraction helper; runtime projected-socket assertions verify this.
- Rear eye distance is 12 cm for this model. The rear sight aperture and front post coordinates were measured from the supplied M4 mesh.
- Existing 2.7/3.466667 second reload gameplay durations are retained; 94-frame/30 Hz source motion is linearly mapped to those durations.
- Existing gunplay damage, input, recoil, movement and audio assets remain in use. This is a visual/animation replacement, not a claim of physically measured M4 ballistics or new M4 recordings.

## Files and reproducibility
- M4_Infima_Candidate.blend: editable source-rig assembly.
- SK_M4_Infima_Export.blend: editable baked export. Source actions retained with fake users.
- build_candidate.py, export_candidate.py, import_candidate.py: assembly/export/import.
- FBXs and export_report.json: mesh, eight exported action assets, durations and source mapping.
- The source has no dedicated inspect or empty-reload clip. Inspect is disabled for this profile rather than playing a mislabeled idle. Empty reload reuses the template reload animation; no separate bolt-release sequence is claimed.
- Old M4Infima and M4InfimaV2 directories are intermediate candidates, not the selected runtime version. V3 avoids files held open by other UE processes.

## Validation
- build_v3.log: successful versioned Editor DLL build, suffix 2026090953. Existing editors were not closed; already-running editors need to reload/restart to use a new native module.
- ue_import_v3.log: M4_INFIMA_IMPORT_OK; all expected animation lengths checked. Commandlet process exit is 1 due to the project's pre-existing GameFeatureData asset-manager configuration error, even though the import script completed; this is distinct from asset validation.
- Saved/GunplayUpgrade/m4-infima-final/result.json: 42 passing assertions, zero failures, clean process exit, before the final physical-sight refinement.
- Final physical-sight run: Saved/GunplayUpgrade/m4-infima-sights/; inspect result.json and screenshots.
- One existing compile blocker was repaired with only `class UScrollBox;` in UI/ColdSteelHUDWidget.h.
