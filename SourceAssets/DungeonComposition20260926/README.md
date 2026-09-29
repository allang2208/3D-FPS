# Dungeon Composition 2026-09-26

Project-authored door seals and mission routing. Existing project room meshes and approved corridor materials are reused. No GitHub code or example art was imported; the research references describe graph/embedding concepts only.

- `Scripts/author_seal.py`: Blender production source; original 312 × 287 cm doorway closure with concealed jamb/lintel overlap.
- `Authored/`: editable Blend file, three FBX groups, source manifest.
- `Scripts/import_assets.py`: new package import, existing material binding, Nanite and collision build, per-mesh save receipts.
- `Scripts/extend_catalog.py`: two three-door junctions and mission-routing settings. Original independent rooms are left unchanged.
- `Scripts/install.py`: reads the current dungeon generator, preserves its previous JSON, installs incremental catalog/asset references and saves its external actor package.
- `Scripts/background_install.py`: import and installation commandlet entry. Does not generate a dungeon or run a game.

`Receipts/import.json` must say `meshes_saved`; `Receipts/install.json` must say `map_saved` before treating this pack as installed. The saved actor packages are listed in the latter receipt. Neither receipt is runtime or visual acceptance.

2026-09-28: Shared ventilation shell/interior permutations were retired. This pack retains only junction seals and mission routing. Room authoring now uses one complete definition per distinct room.
