# AKM UE migration source snapshot — 2026-09-09

This directory preserves the character implementation and asset conversion tools
from D:/FPS3D/FPSGAME. It is an integration snapshot, **not a standalone Unreal
project or a complete Godot weapon port**. The running UE project remains local.
Other active UI/weather work is deliberately outside this publication.

## Contents and use

- Source/FPSGAMECharacter.h and .cpp: matching FPSGAME module character pair.
  Integrate them in an existing UE 5.8 FPSGAME module with Engine/InputCore;
  configure the input actions named in SetupPlayerInputComponent and the game
  mode/pawn. These files are not a drop-in plugin.
- Tools: Blender conversion/bake checks, Unreal animation/audio import and
  Godot ADS probe. Scripts preserve their explicit local paths; inspect and adapt
  those paths before running on another machine. Import scripts replace the
  named destination assets, so use an isolated project for reproduction.
- Reports: historical conversion measurements and recoverable cleanup manifest.
- Preview/AKM_ADS.png: a 1280x720 runtime capture of the centered stationary ADS pose.

The local /Game/Weapons/AKM assets, editable blend/FBX files, maps, audio,
build products, editor settings and caches are not included. Third-party model,
animation and audio redistribution rights were not established by this task.
Existing source provenance: E:/3d/akm-classic-staging/akm-classic-unified.blend
and Godot assets/models/akm_classic/akm_refined_v2.glb. Conversion does not
grant a new license to the input assets.

## Implemented baseline

Godot AKM defaults: 0.12 s fire interval; 30 damage; 30/90 initial ammunition;
2.7 s normal and 3.466667 s empty reload. Weapon ADS smoothing is 9.985774,
camera smoothing 9; vertical FOV 75/55 is converted for 16:9.
Independent kick/jitter/flip springs, camera feedback, bloom and timed mechanical
audio cues are represented in the code. Ammo settles at reload completion.

## Validation and remaining differences

The previous task completed native compilation and a scripted standalone UE
run with six screenshots and AKM_AUDIT_COMPLETE. That flag calls gameplay
methods directly and logs states; it is not an assertion-based test and does
not validate physical input. Final audit ammo was 30/35 after staged reloads.
Audio import reported nine assets; listening/synchronization was not verified.

Known differences from Godot, retained transparently in this snapshot:

- ADS uses a fixed transform, not current animated rear/front sight alignment.
  A centered stationary screenshot does not prove alignment while firing.
- Equip starts reload_empty at 1.57 s; Godot blends idle for 0.18 s then starts
  the source action at 1.75 s. These motions are not equivalent.
- Damage is hitscan, not the source projectile with travel, muzzle obstruction,
  range and hit rules. ADS ray uses camera forward rather than the visible sight.
- UE Perlin replaces Godot simplex noise. Some flip/camera/FOV impulses do not
  yet include the source recoil-load multiplier. Camera control-rotation
  composition and mouse-velocity sway need measured validation.
- Audio uses overlapping PlaySound2D voices rather than restarting the source
  firing player. Input hold/resume, cadence on rapid clicks, automatic reload
  after the last shot and sprint-to-fire behavior remain to be compared.
- Muzzle flash, casing emission and full animation blending are not migrated.

Do not describe this checkpoint as perfect parity. The reusable migration
checklist is in ../../skills/ue5-cpp-gameplay/references/godot-weapon-migration.md.

## Cleanup and publication

Nine obsolete debug/backup files (8 PNGs and one .blend1) were moved locally to
D:/FPS3D/FPSGAME/trash/akm-migration-20260909. The manifest records original
paths, destinations, sizes and SHA-256; all moves were hash-verified. Restore by
moving an archived file back to its original path after checking for conflicts.
Final previews, .blend, FBX, import reports and reproducible tools were retained.

Publication uses a detached worktree based on origin/main under WORKFLOW.md
section 8. No unrelated local Godot commits or UI/weather changes are included.
Godot runtime code/assets are unchanged by this snapshot; its import/combat
suite is not evidence for UE C++ behavior.
