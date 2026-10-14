# Third-person laser and sword repair — 2026-10-06

Requested scope: disconnected aiming laser, twisted whirlwind, dash overhead
and uppercut. This batch does not change attack damage, movement, hit windows or
the accepted ordinary combo mapping.

## Native changes

- `TacticalDeviceComponent.cpp`: wait for the world body and its mesh before
  sampling the visible attachment; refresh attached transforms; third-person
  pistol ADS now uses the actual barrel axis, like third-person rifles, instead
  of steering the laser independently toward the first-person camera target.
  The beam still starts at the visible attachment's Emitter socket and uses the
  same trace as the impact spot. First-person ADS convergence is retained.
- `FPSBodySwordPose.inl`: anchor the authored chest in component space relative
  to the blended hip. Running still supplies the legs without adding its pelvis
  yaw/roll to the attack's shoulders and head a second time.

## Authored replacements

`author_actions.py` writes `authored-actions.json`. It reuses the project's Kevin
two-hand carry and existing authored two-step foot pivot helpers. The attack
paths and arm fitting are new authoring; these are not untouched motion-capture
takes, and the composite is not claimed as CC0.

- Overhead / DashOverhead: high front preparation, downward cut and recovery.
- Uppercut: low preparation, rising cut and recovery.
- Whirlwind: complete-pose entry, periodic stable two-hand hold with foot pivots,
  and complete-pose exit. Gameplay supplies rotation; no extra root spin is baked.
- Preserve Jason's reference bone translations and scales. Fit both wrists from
  one hilt, keep elbows away from the folded-arm singularity, and use solved
  anatomical poses for preparation/recovery instead of twisting the hilt back
  through an incompatible wrist orientation.
- Blade convention during the cutting segment: +Z length, XZ face, -X edge.
  Contact/Release markers retain the gameplay-to-animation timing mapping.

Final packages are created under
`/Game/Characters/JasonPlayer20261003/CombatRepair20261006V3/Animations`.
`Tools/PlayerBody/save_combat_repair_v2.py` saves all six packages before updating
the corresponding entries in `Content/ColdSteelData/player_body.json`.
The V2 DashOverhead package is an earlier incomplete PIE save and is not published
by this final batch. It is retained to avoid touching the open editor's old package.

## Delivery boundary

- Editor build succeeded: `Saved/BuildEditor/build-20261006-214553.log`.
- All six final animation packages saved and their runtime references published
  at 22:07 on 2026-10-06. The background Python commandlet exited with code 0.
  Receipt: `assets-saved.json` (written by the actual save operation).
- `authoring-joint-motion.json` contains offline curve-fitting measurements used
  to correct the reported joint flips. It is not a rendered/runtime acceptance.
- No game launch, PIE test, capture, render, regression or visual acceptance was
  performed by this batch. The user reviews the result in game.
