# Shared firearm scope ADS eye relief — 2026-11-08

Requested: use the M24 factory high-power ADS eye relief for magnifying scopes on all firearms.

- Shared camera-to-rear-sight distance: **9 cm**, taken from the existing M24 factory 6x setup.
- Applies through `UsesPhysicalScope()` to M24 factory/common scopes, LPVO 1–6x, KV 1–4x, prism 2x, native SVD and shared PSO 4x, DW715 2x and thermal 1.5/3/8x, on every supported firearm.
- Normal/right-hand and lone-left-hand ADS use the same constant. The selected zoom does not change the target distance. Bipod ADS uses the normal calibration path.
- Uses the installed rear/front/up sight sockets where present; legacy AimCenter-only optics keep their existing axis fallback.
- Retains the ordinary iron/red-dot/holographic framing and M24 upper-sight transition; bow aiming is separate.
- Supersedes Repair14's M249-only 16 cm LPVO/KV override. No model scale, mount, lens material, capture FOV, garment, animation asset, inventory or save-data edits.

Source backup files contain the pre-edit working copy, including existing parallel changes. No git reset or commit was performed.

Runtime/visual tests were not requested and were not run. Existing in-progress PIE can retain its calibrated pose until the weapon is re-equipped; new play instances use the new calibration. Build receipts record the actual build mode and completion separately from runtime acceptance.

## Delivered builds

- Normal `FPSGAMEEditor Win64 Development`: succeeded, 192 actions, 238.88 seconds; base Editor DLL updated (`build_editor_receipt.json`).
- Normal `FPSGAME Win64 Development`: succeeded, 670 actions, 625.13 seconds; `Binaries/Win64/FPSGAME.exe` updated (`build_game_receipt.json`).
- The existing editor exited during the initial object compilation. The subsequent bridge request found no editor and did not apply a Live Coding patch. The normal builds above supersede that attempt; delivery does not depend on a hot patch.
- Waited for the occupied build window without interrupting other processes. No editor/game was launched, and no runtime or visual acceptance was performed.
