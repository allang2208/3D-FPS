# Super90 quick melee — current R5 candidate

The current authoring folder is `LeftArmR5/`. Five production assets and five
editable timelines were saved; the user has not accepted the resulting motion.
R4 was rejected for continued left-arm twisting. Quick reload remains paused.

R5 retains the stronger R3 gun swing and installed palm/finger contacts. Its
`inputs.json`, `author_space.json`, and `camera_basis.json` are self-contained
copies of required earlier inputs, so retired revision folders are not needed.

Read `LeftArmR5/README.md` for the wrist-first authoring and native skin bases.
Authoring: `read_source.py` (UE installed state), `read_skin_basis.py` (Blender
V7 rest input), `author_motion.py`, `save_editable.py`, then `save_assets.py`
through the existing asset mutex. Preserve the local captured source datasets;
reading a new installed state changes the authoring baseline.

R1–R4, old backups and caches are recoverable under
`trash/super90-retired-20261009/SourceAssets/Super90QuickMelee20261008/`.
The public repository carries author recipes and documentation only; restore
licensed local assets and dense input datasets before running these scripts.
See `Docs/Weapons/super90-publication-20261009.md` for dependency and status details.
