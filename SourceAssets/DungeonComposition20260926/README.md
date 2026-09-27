# Dungeon Composition 2026-09-26

Project-authored door seal and compatible room recipes. Existing project room meshes and approved corridor materials are reused. No GitHub code or example art was imported; the research references describe graph/embedding concepts only.

- `Scripts/author_seal.py`: Blender production source; original 312 × 287 cm doorway closure with concealed jamb/lintel overlap.
- `Authored/`: editable Blend file, three FBX groups, source manifest.
- `Scripts/import_assets.py`: new package import, existing material binding, Nanite and collision build, per-mesh save receipts.
- `Scripts/extend_catalog.py`: two shared ventilation shells, three compatible equipment recipes, three legal door pairs, two three-door junction recipes.
- `Scripts/install.py`: reads the current dungeon generator, preserves its previous JSON, installs incremental catalog/asset references and saves its external actor package.
- `Scripts/background_install.py`: import and installation commandlet entry. Does not generate a dungeon or run a game.

`Receipts/import.json` must say `meshes_saved`; `Receipts/install.json` must say `map_saved` before treating this pack as installed. The saved actor packages are listed in the latter receipt. Neither receipt is runtime or visual acceptance.
