# 201 fine finish R01

Production recipe continues the currently saved F50 family and D46/D47 drum.
It preserves current geometry (including R58 restored grips), UVs, authored
normal/AO sources, mixed-material masks, cloth/belts, animations and mechanics.

Entry points:

1. `capture_inputs.py`: current material inputs and actual slot bindings.
2. `produce.py`: technical 1024 RGBA grain map and explicit part recipes.
3. `apply_finish.py`: private source adapters, adjustable instances, scoped
   material binding and appended wet self mappings through `../../run_ue.ps1`.

The recipe contains 97 instances, 92 source graph adapters and 30 mesh binding
targets. These are production counts, not performance measurements. Historical
slots can remain in mesh material tables; this batch does not delete sections.

F50 original materials remain untouched. The adapters preserve source graph
details and add parameters for the fine finish. Per-role instances distinguish
receiver, cover, front, magazine, mounts, steel, furniture and rubber. Titanium,
optical special materials, cloth, cartridges, links and interiors retain their
current bindings. The drum remains polymer with separate metal hardware.

`Input/current.json` is the captured baseline; `recipe.json` is the production
plan. Existing target package backups go to `Before/`; `apply_receipt.json`
records actual saved assets. Only `complete=true` confirms completed saving.

Saved on 2026-10-01 after the user stopped PIE: 97 instances, 92 source adapters,
one grain texture, 30 mesh material tables and 97 added wet self mappings.
`apply_receipt.json` is complete. The existing editor bridge returned success;
log: `SourceAssets/WeaponSurface20260930/logs/apply_finish.20261001-155332-059.bridge.txt`.

`finalize_records.py` updates only the saved slot deltas in the current
`LMG20120260927/Material21/bindings.json`, preserving other revision notes.
The local `bindings.json` lists changed slots, not a geometry snapshot.
Continue from this recipe and the current UE assets. Do not rerun old F50
material-binding scripts over the new instances.

No editor was launched by this task. No game, screenshot, render or extra test
was requested or run. The user will assess the appearance in game.
