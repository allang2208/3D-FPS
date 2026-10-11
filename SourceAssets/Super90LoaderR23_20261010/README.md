# Super90 R23 production sources

Saved runtime revision: [project record](../../Docs/Weapons/super90-speedloader-r23-wrist-support-clearance-20261010.md).

Production sequence: `prepare_clips.py`, `fair_bind_surface.py`, Blender `author_r23.py`, `run_r23.ps1`. The native support node is `Source/FPSGAME/Weapons/Super90SupportArmNode.*`; compile it with `build_r23.ps1` when modified. Asset import does not run a game.

`repair_core.py` is the matching offline support algorithm. `contact_poses.json` contains only the hand contact edits baked into eight FBX clips; `repaired_poses.json` additionally includes the runtime arm support for scoped diagnostics. Four `*_profiles.json` files preserve native grip adaptation.

Only `repaired` diagnostics represent this revision. `extended`, `rigid`, `upper`, `down`, `repair_core_iteration1.py`, and `repair_bind_surface.py` are investigation candidates, not production recipes. The latter transport hypothesis produces only float-scale differences; the actual geometry patch comes from `fair_bind_surface.py`.

`import_receipt.json`: 14 saved assets in the real runtime paths, including 2 local left-elbow mesh patches. `build_receipt.json`: Editor/Game succeeded. No PIE or game acceptance.
