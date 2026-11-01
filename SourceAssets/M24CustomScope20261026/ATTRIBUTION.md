# M24 Custom Scope - source attribution

The selected model is **M24 Sniper Rifle - Custom Scope**, by **M37_R**:
https://sketchfab.com/3d-models/m24-sniper-rifle-custom-scope-84b72eaf37a54ecb945017e3955455a0

Its rifle mesh and compatible first-person animation originate from
**sniper animated**, by **DJMaesen**:
https://sketchfab.com/3d-models/sniper-animated-b48999a250b2433da59f705c371a49b2

The custom optic originates from **Rifle Scope w/ Laser & Sight**, by
**MaximDeduytsche**:
https://sketchfab.com/3d-models/rifle-scope-w-laser-sight-d82ec237ad2f49a384d59f84fcde5429

All three source API records identify Creative Commons Attribution 4.0:
https://creativecommons.org/licenses/by/4.0/

Credit M37_R, DJMaesen, and MaximDeduytsche. No endorsement is implied.
The original archive license files and public metadata are retained in
`Original/` and `Donor/`. Download credentials and temporary signed download
URLs are not retained in these project files.

Local adaptations made on 2026-10-26:

- Converted the static remix to the original rifle's physical scale and pivots.
- Preserved the 14 selected model parts, their source UVs and material identities.
- Added explicit skeletal identities for the bolt carrier, rotating bolt handle,
  trigger, magazine, cartridge, suppressor, cheek rest, scope and optic accessories.
- Baked the author's object animation and hand skeleton onto one native source
  skeleton; retained the complete 201-frame timeline and five subsegments.
- Authored Unreal material graphs from the supplied PBR maps. Thin glass
  transmission is approximated with translucency.
- Kept the original arm appearance in a clearly named source viewmodel. This is
  not the FPSGAME V9 gameplay arm and is not registered as a playable weapon.

The downloaded original source archive does not contain the sounds mentioned
in its web description. No matching audio is included in this local batch.

Gameplay adaptation on 2026-10-27:

- Retargeted original rifle/hand motion to the project's installed V9 bare
  arms, retaining V9 rest geometry, UVs, skin weights and corrective shapes.
  Project V9 hands retain their existing project provenance; the Sketchfab
  license does not grant rights to those separately sourced hands.
- Added sight, muzzle, ejection and buttplate markers, and V9 forearm twist
  distribution (100% / 50%).
- Source motion supplies firing/cycling, magazine reload and empty reload.
  Equip, inspect and quick-melee transitions are newly authored adaptations,
  not animations advertised by the source artist.
- Gameplay audio reuses the installed SVD mechanical/shot assets and existing
  M4 suppressed-shot bank under their existing project provenance. These are
  project sound choices, not sounds from the downloaded M24 archive.
- Added a catalog icon generated from the selected textured rifle and existing
  project scope presentation configured to a fixed gameplay 6x zoom.
