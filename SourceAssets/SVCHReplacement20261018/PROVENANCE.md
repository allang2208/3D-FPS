# SVCH selected replacement, 2026-10-18

- User-selected page: https://sketchfab.com/3d-models/chukavin-sniper-rifle-b3bb922bdf1a481a96b9e2940b2d26fc
- Platform title: Chukavin Sniper Rifle.
- Uploader: FamousUnityHubSoldier, https://sketchfab.com/FamousUnityHubSoldier
- API license metadata: Free Standard (`free-st`), https://sketchfab.com/licenses . This is different from the old TastyTony asset's CC BY 4.0 license.
- The archive internally identifies `call-of-duty-mwiii-2023-kv-inhibitor`, with `KV Inhibitor.blend` and FBX. Record this game-asset origin separately from the uploader's title/license metadata. Underlying third-party rights have not been independently established; no public distribution was performed in this task.
- Original archives and GLB are retained in `Download/`; original Blender, FBX, color and normal images are retained under its extracted subtree.
- Source payload hashes are recorded in `download_receipt.json`. Credentials and expiring download URLs were not persisted.

## Production selection

Use the main receiver/grip, standard barrel, standard magazine, matching cartridges and stock. Keep the alternate barrel, extended magazine and scope in the untouched download archive. The user explicitly selected mechanical sights instead of the included scope; the replacement includes locally authored open-aperture rear and protected front sights.

Preserve the source UV and topology, including its rigid mechanical separation. The source supplies color and normal maps, not a complete metallic/roughness texture set. Local materials retain the source maps and add separately authored roughness/metallic values; do not describe these scalar values as original PBR maps. Color alpha is not treated as transparency. Source-engine normals are interpreted as DirectX normal maps.

Uniform source-unit registration is recorded in `registration.json`. `contact_geometry.py` makes two local changes to accommodate the approved hand shapes: the lower pistol-grip thickness scales to 0.69 and the lower handguard to 0.75, blending back into their original interfaces. UVs remain unchanged; custom normals use the deformation Jacobian. No global subdivision or procedural grain replaces the selected source detail.

The old R8 assets, old R11 contact profile, shared SVD animation sequences and native V9 hand mesh remain available. `profile_replacement.json` adds only whole-arm registration at the clavicles to the R11 profile; finger/wrist/arm-joint local poses and source clocks are retained. Geometric fitting is authoring work, not visual or gameplay acceptance.
