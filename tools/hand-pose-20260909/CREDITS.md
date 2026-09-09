# Fitted first-person hands — free_fitted_v1

Hand source: **Realistic human hand model**, by **NadevayNoski**.

Source listing: https://www.cgtrader.com/free-3d-models/character/human-anatomy/realistic-human-hand-model

Downloaded by the signed-in user on 2026-09-08. The recorded listing label is **Royalty Free License (no AI)**. This is a third-party licensed asset, not CC0; this notice does not replace or broaden the original license. Original source and downloaded texture archive are retained in the local source directory below. No generative AI service was used to process this model.

Project modifications: mirrored left/right hands; per-weapon fitting to the existing bind table; rebuilt continuous palm volume and thumb-root weights; finger fitting; fingerless glove material and rounded opening hems; baked skin/nail textures; retained original weapon-specific sleeves. Original weapon meshes, sleeves, rigs and animations retain their existing provenance and licenses.

The six `.res` files are mesh-only resources with embedded textures. `scripts/fitted_player_hands.gd` selects the correct mesh; `scripts/infima_viewmodel.gd` installs it on the existing skinned mesh. No new skeleton or replacement animation library is installed. Grip and drum motion corrections remain in the existing runtime pose layer.

Local editable delivery: `E:/无尽轮回/3d/free-hands-20260908/editable-v6/` — six weapon-specific GLBs and packed Blender files, each saved and reopened successfully. These contain source clips; procedural grip/reload adaptation is implemented in the Godot scripts.

Local acquired source: `E:/无尽轮回/3d/free-hands-20260908/source/`.

Reproduction sources: `fit_hands_v6.py`, `export_hand_rigs.gd`, `assemble_hands_v3.gd`, `export_editable_hands.gd` in `E:/无尽轮回/3d/free-hands-20260908/`. The assembler's `v3` filenames are historical: the current input meshes were produced by the v6 generator. Export rig landmarks with `fitted_hands_enabled=false` so new meshes are never used as the original sleeve source.

Verification and preview index: `E:/无尽轮回/3d/free-hands-20260908/HAND-REPLACEMENT-REPORT.md`.
