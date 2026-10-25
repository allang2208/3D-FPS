# Backpack fit producer

Production: `run.ps1`, called after clothing publication by the workwear and waist workflows. See `Docs/Characters/backpack-contact-workflow.md` for source requirements, authored/saved/published receipts and the distinction from gameplay acceptance.

- `pending.py`, `prepare.py`: current catalog/body/clothing routes and dependency selection.
- `capture.py`: saved UE geometry and native binding frames, with content-hash reuse.
- `classify_cargo.py`, `sample_shells.py`, `surfaces.py`: cargo topology and actual triangle contact fields.
- `author_contact.py`, `fit_geometry.py`, `fit_sling.py`, `preserve_sections.py`: current production authoring.
- `save_assets.py`, `publish.py`, `register.py`: new packages, scoped config publication and dependency receipt.
- `analyze.py`, `preview.py`, `render_contacts.py`, `run_stage.ps1 -Stage contact`: requested diagnostics only; production does not invoke these automatically.

The unpublished R2 whole-carrier lift/tilt experiments (`author.py`, `refold_sources.py`, `solve_mounts.py`) are archived in `trash/backpacks-belts-retired-20261025/Tools/BackpackFit/`. Restore only for historical investigation; use `author_contact.py` for production. The publication retirement manifest records their hashes.

R2 Authored/Preview, mount outputs and failed authoring logs are archived with those experiments. R2 Capture remains a live input referenced by R3 captures. Standalone helper defaults now select ContactFitR3; the production wrapper still supplies its explicit revision.
