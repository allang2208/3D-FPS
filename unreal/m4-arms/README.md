# UE5 M4 arms, reload and MAT workflow

The current M4 uses the same visible magazine toss for normal and empty reloads. The left hand retrieves a replacement offscreen, wraps it, inserts and seats it. Normal reload returns directly to idle; empty reload retains the faster final slap and brief gun vibration. Equip/charge plays at the weapon's hip position.

This is a scoped source, tool and evidence snapshot from `D:/FPS3D/FPSGAME` (UE 5.8.2), published on 2026-09-10. It is **not a complete runnable Unreal project**. The Godot root remains a historical prototype; new FPS development targets UE5.

## Standards

- [UE5 weapon workflow](../../skills/ue5-weapon-workflow/SKILL.md)
- [First-person arms animation](../../skills/ue5-fps-arms-animation/SKILL.md)
- [Current M4 assets and timing](../../skills/ue5-fps-arms-animation/references/m4-baseline.md)
- [MAT editing and verified limitations](../../skills/ue5-fps-arms-animation/references/mat-editing.md)
- [Cleanup and publication](../../skills/ue5-weapon-workflow/references/publication.md)

Five old Godot weapon/hand standard entries were retired locally and replaced by redirects. The repo's corresponding entries now navigate to the UE standards. Other Godot references are historical, not current hand-model or timing defaults.

## Included material

`SourceAssets/` preserves the relative case-directory structure for authored scripts, fitted contact parameters and dated validation reports. Host identity and LF-normalized repository hashes are recorded in [source-manifest.json](Reports/source-manifest.json).

- [WrapGrip](SourceAssets/M4WrapGrip20260910/repair_authored.py): natural hand shape, magazine-space grip, entry clearance and valid whole-arm reference. The old normal/empty clips here have been superseded; equip remains in use.
- [SlapImpact](SourceAssets/M4SlapImpact20260910/author_slap.py): final approach 125–130 to 126.667–130 logical frames, 1.5x speed, contact at 130/60 s, small damped shake.
- [TacticalToss](SourceAssets/M4TacticalToss20260910/author_toss.py): normal reload reuses the accepted empty toss/retrieval and rejoins the normal recovery. Duration 2.1 s; events at 29/60, 76/60, 95/60 s.
- [Host function excerpts](Runtime/FPSGAMECharacter.weapon-functions.cpp.txt): reload timing, playback, active asset selection and mechanical-cue handling. These are reference excerpts, not a standalone translation unit or a replacement character file. Other tasks' UI/inventory changes were deliberately excluded.

## Host dependencies and reproduction

Start from the existing FPSGAME host and obtain its third-party assets under their original terms. Preserve current shared source and asset branches. Install/adapt the case directories under the host's `SourceAssets` tree; check every script's absolute source path and destination before running. Running a publisher unedited can write Unreal assets.

Required source chain:

1. `M4HK416Replica20260910/M4_HK416_Drum_Editable.blend` and `M4ContactImpact20260910/M4_Hand_MAT_Editable.blend`, plus the source rig/library files referenced by those blends, are inputs to WrapGrip. The fitted JSON inputs are included.
2. WrapGrip's retained final Blend feeds `author_slap.py`; SlapImpact's final Blend feeds `author_toss.py`. Do not delete earlier sources merely because a later animation is active.
3. The UE host needs `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416`, compatible skeleton/materials, `/Game/Weapons/M4ContactImpactFinal/CR_M4_ContactImpact`, `/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel`, the HK416 audio bank, FPSGAME's animation/input/profile systems and the validation map.
4. Author/check candidates, import only the target clip, independently read saved compressed poses, then update the matching normal/empty/equip route and test a fresh host process. MAT sequence edits require baking back to the runtime AnimSequence; saving the sequence alone does not update the C++ clip.
5. AV validation scripts use the local Blender, UE and ffmpeg paths and external licensed audio templates. Adapt those dependencies and use a fresh profile/label. Do not run the host game directly from this snapshot.

The M4 model was user-provided; hand/rig sources were from Infima's [Free FPS Template](https://www.fab.com/listings/6a0af880-2b74-480c-a82c-8e597918dffe). HK416 audio has separate source rights and is not covered by a model license. Model/texture/audio blobs, Blend/FBX/uasset files, engine plugins and video audio are not included in this publication. Licensed editable sources and final actual AV remain in the host case folders. No license is reassigned to third-party assets.

## Evidence and limits

- [Normal-toss runtime](Reports/m4-tactical-toss.json): 50 pass, 0 fail in the real host game; 253 hand/magazine mesh samples had no overlap, saved grip drift about 0.122 mm.
- [Empty-slap runtime](Reports/m4-slap-impact.json): 50 pass, 0 fail; modified contact segment checked, final approach speed and damped shake authored.
- [Equip runtime](Reports/m4-wrap-equip-final.json): separate 21-pass run, preserved .72 s runtime equip action.
- Each latest complete reload recording detected 11 mechanical cues. Correspondence is documented in the case audio JSON files. These are prior dated host runs, not tests rerun from this public snapshot.
- Current normal endpoints retain baseline hand/body surface contacts; empty slap also retains its documented baseline contact. A no-overlap magazine probe does not claim whole-model perfection.
- MAT helper shutdown after save still exhibited an existing Sequencer crash; saved sequences were independently read back and the game tests exited normally. No untested FK/IK or MetaHuman-specific feature is claimed.
- [Cleanup manifest](Reports/cleanup-manifest.json): 23 unreferenced Blender backups/silent mux intermediates, 903,772,493 bytes, moved to local trash after hash verification. Final sources, real AV and reconstruction inputs remain. Trash payloads are not published.

Publication checks are in [publication-validation.json](Reports/publication-validation.json). They cover script syntax, links, host/repository source hashes, skill metadata, archive integrity, staged changes and dependency boundaries, rather than rerunning unrelated Godot tests.
