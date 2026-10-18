# ST6 native body reset

`author_sleeves.py` restores the original 2026-10-06 sleeve donor across existing native rigs. `build_materials.py` makes rest-pose anchored cloth for the existing body. `recipe.py` owns only the ST6 equipment recipe. `import_sleeves.py`, `finish_assets.py`, and `publish.py` save assets and merge catalogs. `author_pickup.py` and `render_icon.py` make the display shirt and 3x3 icon. `build.ps1` builds Game or Editor without UBA after the observed compiler failures.

The native body mesh is never expanded or rebound to the first-person clavicles. The owner view uses material coverage instead of an extra torso mesh. Original sleeves retain their own material, UVs, geometry, and native animation binding.

No game/PIE or acceptance tests were launched. Use the saved receipts, not old shell authoring reports, to determine delivery state.
