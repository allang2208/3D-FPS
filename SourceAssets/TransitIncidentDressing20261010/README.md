# FacilityTransit incident dressing

Authored 2026-10-10 for the existing second concourse. See `../../Docs/Gameplay/transit-incident-dressing-20261010.md` for the saved scope and source attribution.

- `make_prints.py`: original administrative and caution-sign artwork; uses Pillow and NumPy.
- `author.py`: Blender 5.1 background mesh authoring; exports nine local-pivot props and `Authored/TransitIncidentProps.blend`.
- `materials.py`: scoped UE Substrate print/plastic/cotton materials, shared existing facility surface bindings.
- `recipe.py`: fixed incident clusters in UE centimetres, plus eleven scanned blood decals. Idempotent overlay for `FacilityTransit` only; no light edits or creature spawning.
- `install.py`: imports owned assets, derives support heights from actual reused mesh bounds, merges the currently saved formal catalog and saves the three existing maps.
- `run_background.ps1 -RenderShaders`: serialized background import or existing editor bridge; does not launch GUI or game.

Generated source geometry, artwork, manifests, placements and actual Unreal assets are saved. `Receipts/install.json` distinguishes asset and map stages. Do not overwrite a differing imported mesh; produce a new versioned mesh path for a revision. Respect the user rule against unsolicited tests, screenshots and gameplay runs.
