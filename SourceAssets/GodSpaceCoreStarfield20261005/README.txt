GodSpaceCore starfield upgrade — 2026-10-05, accepted V2

Installed asset identity:
  /Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceCore
Dedicated textures/materials:
  /Game/Props/GodSpaceCoreStarfield20261005

Authoring:
  Scripts/generate_textures.py (standalone Python with numpy/scipy/Pillow)
  Scripts/author_core.py (Blender background)
  Authored/GodSpaceCore_Starfield_Editable.blend
  Authored/SM_GodSpaceCore_Starfield_V2.fbx
The concept image supplies design direction only; no concept-board pixels are
used as sphere texture. Starfield and stars are separate original equirectangular
textures. The gold atlas uses UV0 in the final FBX and UE render data.

Regeneration/integration:
The original GodSpaceLayout20260927/Integration/export_accepted_layout.py now
authors this dedicated core last and copies its FBX to the original import path.
The original import_assets.py routes the core through Scripts/install_formal.py,
which uses the original UE mesh identity, dedicated materials, and retained
collision settings. It removes old unused FBX material slots by section name.
The old layout .blend remains an unchanged historical layout source; its old
core geometry is no longer the canonical core exported to UE.

Geometry: 300 cm sphere, exactly two rings, original pivot and placement.
Nanite remains disabled; component collision remains NoCollision. AABB matches
the original. UE's conservative culling sphere radius is larger after bounds
extension (237.500181 -> 380.800883 cm); this is not the physical sphere radius.

Delivery status:
Formal mesh saved at 2026-10-05 12:03 UTC; accepted V2 candidate was reviewed in
actual Hub and neutral light. The galaxy is more concentrated/cyan than the
concept, so the result is an approximation, not an exact reproduction.
Final map reload, formal screenshots, seam/pole visual checks and native altar E
verification were blocked because the owned editor process disappeared and the
bridge reported no connectable editor node. No full expedition/performance test.
No map/shared-material/default-save changes, commit or push.

Evidence and rollback:
  Receipts/formal_install.json
  Receipts/final_validation.json
  Receipts/protected_hashes.json
  Receipts/authoring_chain.json
  Backups/BeforeInstall/manifest.json
Only restore explicit backed-up files if rolling back; do not overwrite unrelated
project work or default player saves. Original default-save copies remain in the
task workspace backup, not duplicated into this source package.
