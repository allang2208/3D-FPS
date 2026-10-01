# AKM authored satin R02 — 2026-10-01

R01 user feedback: the visible difference was too subtle. R02 strengthens the project satin finish while retaining original decoration and structural normal inputs. Production status is recorded in `apply_receipt.json`; the recipe alone does not mean assets have been saved.

Production completed through the existing editor after the user stopped PIE. The bridge returned success with `WEAPON_SURFACE_AKM_R02_SAVED 38 graphs including 2 runtime overrides; 38 instances; same meshes and weather mappings; tested=False`. The receipt and current binding entry are saved.

## Revision

- Source roughness deviation weight: `.75` to `.28`. Original broad roughness therefore has less influence over the new part finish, while the authored variation remains present.
- Dry roughness centers: receiver `.31`, magazine `.29`, mount `.44`, muzzle `.46`, optic shell `.37`, furniture metal `.39`, accessory metal `.36`.
- Source tone is compressed around the original `.058` steel reference using a `.58` exponent and `.58/.60/.64` tone scale. The neutral reference remains about `.035` linear: the change is greater consistency across the body rather than repeated blanket darkening.
- The protected bright-wear range moves from `.085–.22` to `.12–.32`, and the high-chroma protection range moves from `.22–.55` to `.45–.95`. Subtle steel tint and medium-bright steel now participate more fully; distinctly colored decorations, nonmetal regions and bright wear remain protected.
- Roughness protection no longer excludes every bright metallic region. Authored bright wear retains a slightly smoother exposed response. The masks remain numeric, not semantic segmentation.
- No added noise normal or extra texture. Original maps, normal/AO/UV chains, weather layer, shader usage and material-slot identities remain in place.

## Production

`produce.py` writes `recipe.json` using the saved R01 addresses. `apply_refine02.py` replaces the existing two finish expressions, adds one scalar parameter, sets defaults/MI overrides, compiles and saves. It does not stack another coating over R01. The targets are 36 private adapters, 2 AKM-only runtime body materials and 38 instances; their existing 30-mesh bindings and 40 weather mappings remain applicable.

Before packages are stored in `Before/`. After a completed save, `../current_surface_bindings.json` becomes the common importer's current entry. R01 source and receipt remain historical; do not rerun its creation pass over R02. The existing R01 `rebind_current.py` can restore the unchanged slots after an explicitly requested mesh reimport and now uses the current revision metadata.

No game, PIE, visual render or additional test is part of this revision. The user evaluates the appearance after the save.
