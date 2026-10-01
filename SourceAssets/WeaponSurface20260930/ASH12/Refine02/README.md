# ASH12 Refine02 — fine finish and region controls

Saved on 2026-10-01: 27 existing material instances, one 1024² RGBA linear BC7
grain texture, one private regional graph and three copied regional presets.
No mesh, slot binding, animation, normal texture or weather-table changes.

Production order: `capture_inputs.py`, `produce.py`, then `apply_finish.py`
through `../../run_ue.ps1` with the shared batch mutex. The runner uses an
already-running editor when available; it never launches a new interactive UE.

`Input/current.json` holds live source parameters, graphs, inheritance and
bindings. `recipe.json` describes the finish; `Before/` contains the 27 modified
instance packages before this revision. `apply_receipt.json` records actual
saves (`complete=true`, `tested=false`). Source parents and textures are intact.

The regional graph retains the original vertex-colour R/G/B masks: R furniture,
G bolt, B bore. Grain, mottling, cavity response, edge highlight and polymer
stipple now have independent region controls. Upper's R region remains rubber;
Lower's R region remains polymer. The bore is still dry, dark and non-metallic.

The original and extended magazines remain polymer. Both use matching finish
settings, while the extension keeps its existing UV1 alternate sample and
UV2-6 tangent-frame seam reconstruction. No normal graph was rewired.

Saved via the existing editor bridge. No new editor, PIE, screenshot, beauty
render or extra test. See `Docs/Weapons/ash12-finish-refine02-20261001.md`.
