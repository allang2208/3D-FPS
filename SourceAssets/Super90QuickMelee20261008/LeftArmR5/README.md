# Super90 quick melee: left arm R5

R4 was rejected by the user: the left arm still twisted and looked ergonomically
wrong. Its low wrist-angle objective did not make the arm support appropriate.
It inherited the donor shoulder at camera Y=-30 cm, while the elbow at impact
could lie around Y=-15 cm, on the inner side of that shoulder. It also allowed
roughly 160 degrees of elbow-circle swivel. R4 is not an accepted reference.

## Authoring approach

R5 retains the installed gun/right arm, hand world transforms, fingers, duration,
contact time and the five separate installed grips. Only the seven left-chain
tracks and their quick-melee profile deltas change.

The chain is built from the held wrist back toward the body's idle shoulder:

- A bounded cone defines forearm direction relative to the held hand. During
  the core strike its maximum authored axis angle is 35 degrees. The accepted
  idle orientation is carried into and out of this correction continuously.
- Place the elbow one original forearm length behind the wrist. Select the
  upper-arm direction from the elbow toward the actual idle shoulder anchor.
  Keep 35–125 degrees of elbow flexion; allow at most 40 degrees of upper-arm
  swivel, with an objective favouring a small shoulder displacement and the
  elbow outside/below the left shoulder and wrist.
- Position the shoulder exactly one original upper-arm length from that elbow;
  move its clavicle by the same amount. The R3/R4 fixed donor shoulder is unused.
- Derive separate upper/forearm skin hinge bases from the actual V7 source rig
  and the native mesh conversion matrices. These differ from the nearly straight
  native bind hinge by about 12.7 and 6.8 degrees respectively. No PKM-specific
  20-degree crease offset is copied.
- Keep the proximal forearm aligned with the elbow, distribute pronation at the
  native 0, 1/3 and 2/3 stations, and compensate hand_l locally so its world grip
  remains fixed. First/last installed poses are preserved exactly.

The limits above are authoring controls and bone-axis measures, not medical
joint-angle measurements or evidence of visual acceptance. Source controls are
recorded in `authoring_controls.json`; final appearance remains for user testing.

## Files and status

`read_source.py` reads the installed sequence/profile input. `read_skin_basis.py`
reads the V7 source rest matrices in background Blender. `pose_io.py` handles
native coordinate conversion. `author_motion.py` emits `animation_patch.json`.

`save_editable.py` has saved five editable timelines in
`Super90_QuickMelee_Editable.blend`. `save_assets.py` changes only the seven
left-chain tracks and matching profile entries, preserving unrelated data and
retained animation references. Original production assets are backed up in
`Before/` when saving starts.

All five production assets are saved. The editor closed before the bridge could
connect, so the existing mutex-protected background commandlet performed the
save. `save_receipt.json` records completion and all five paths;
`save_background.log` records the execution. No GUI editor was launched.
No gameplay, screenshots, renders, regression or acceptance tests were run.
