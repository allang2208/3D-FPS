# PKM surface, hand and reload revision 06

Scope: user requested realistic materials, idle/reload hand bones and weights,
receiver roll correction, and flexible reload belt motion. This continues the
accepted RestFix05 closed-cover/closed-box source. No Meshy call or generation fee.

## Source and production

- Existing PKM geometry and private skeleton remain the basis. Source license
  remains in `../SOURCE.md`; no source model was uploaded to a generation service.
- Wood uses the existing AKM's local ambientCG Wood051 CC0 texture set.
  UVs follow the stock's long axis at a metric 18 cm tile scale. PKM tint and
  satin roughness are independent of the AKM material asset.
- Grip shell and panels use a black polymer surface authored with the same fine
  grain / dielectric / roughness approach as QBZ191Hero. This reuses the finish
  method, not QBZ atlas pixels. Steel and painted ammo box keep their own finish.
- 0.3 mm metal / 0.5 mm wood-grip local bevels, three segments, clamped overlap,
  weighted normals. This improves edge highlights; it is not a high-poly rebuild.
- Remove measured donor idle roll (-4.882376 degrees) at the assembly level, with
  every mechanical bone and sight marker following the corrected weapon frame.
- Reposition rear grip 25 mm upwards and 4 mm forwards. Place left support on
  the reachable forward receiver flank, with fingers curling toward the gun.
  Correct palm-facing directions for box, cover, belt and charging contacts.
  Five fingers receive separate front-edge contact targets, preserving phalanx
  lengths rather than rotating the entire palm to conceal finger penetration.
- Keep arm segment lengths; remove target-dependent shoulder teleportation.
  Distribute axial wrist twist across forearm twist bones and rebalance existing
  forearm influence mass (1,710 vertices per side). Hand/finger influence mass,
  Manny topology and runtime Manny materials are preserved.
- Reload belt uses deterministic 240 Hz world-space integration with gravity,
  damping, fixed-link constraints, pinned handled tip/inlet and simplified
  receiver shelf / box collision. Stored rounds remain inside the rigid box.
  The chain seats back into its authored feed path before cover closure.
  **This is baked secondary motion, not runtime Chaos physics**; it does not
  respond independently to unpredictable player movement or world collisions.
- Preserve 6.5 s normal / 7.5 s empty timing, sounds/round accounting, old/new prop
  material section identities, and the private PKM skeleton.

## Reproduce

1. Blender background: `read_fingertips.py`, `author_reload.py`, then `author_gameplay.py`.
2. UE bridge: `import_surfaces.py`, then `integrate.py` (one mutex batch each).
3. Authoring source: `PKM_Gameplay_Editable.blend`; game exports: `Exports/`.

Targeted source diagnosis and contact renders are in this folder. Full gameplay
acceptance is left to the user. Import receipts record actual saved assets.

Final integration saved at 2026-09-22 14:26 local time. Mesh, private skeleton,
12 clips and the new surface bindings are saved in the existing PKM runtime path.
`integration_complete.json` records the final source revision timestamp.
No native code changes or gameplay test were performed in this revision.
