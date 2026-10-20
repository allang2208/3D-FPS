# SVCH R7 grip and wrist

Final delivery: Editor and Game built at 2026-10-20T04:19:06Z. All five
profiles are saved; saved-glove native capture and saved-readback subframe
checks passed. Review frames 20, 68 and 70 were regenerated from the saved
native capture. Gameplay was not launched or accepted.

Current source order:

1. `author_grip.py`: own SVCH idle grasp, unchanged grouped finger locals,
   existing M870/SVD shoulder/elbow support; no mesh edits.
2. `bake_existing_handoff.py`: keep the R6 native gun/left-arm entry and recovery,
   carry the corrected right contact group with that same gun transform.
3. `encode_profiles.py`: encode against actual compressed samples with the R6
   dense subframe window. All quick-melee channels represent the baked handoff.
4. Build Editor/Game for the SVCH-only authored-ownership change, then guarded
   `install_profiles.py`. Only quick_melee is replaced in five profiles.
5. Requested scoped checks: `check_runtime.py saved-glove`, `check_dense.py`.

Do not run the handoff bake repeatedly without regenerating the author source.
Do not reuse the pre-ownership `native-before-entry-fix.json` as final evidence.
The initial candidate's excessive final wrist bend and repeated native blend
were diagnosed and superseded, not accepted baselines.

V9 geometry/weights/bind/morphs, hand size, source weapon motion, contact clock,
all other action entries and shared SVD sequences remain unchanged. Runtime
entry/recovery ownership is part of this delivery and requires the current DLL.

Asset save, builds and offline checks are separate from gameplay acceptance.
No interactive editor/game is launched by this task.
