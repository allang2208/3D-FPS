# M16A2 source attribution

The gun mesh and PBR textures are reused from the user's existing local Godot asset source, not newly generated assets.

- Gun model: **M16 A2 Rifle**, **Luchador**. Original model linked by the animated source listing: https://sketchfab.com/3d-models/m16-a2-rifle-20c4bb925ca349c6b33aca176b8affba
- Animated source package: **M16 A2 Assault Rifle - Animated**, **user77**: https://sketchfab.com/3d-models/m16-a2-assault-rifle-animated-bd4ff595b593447f9a7f1d95f501fb6c
- The animated source listing credits **DJMaesen** for arms and animations, linking https://sketchfab.com/3d-models/fps-animated-carbine-62977bb4c53047a185b9f3a0cdf56b87 . Those arms and animation clips are not included in the migrated UE assets. The original FBX is retained locally for provenance.

The animated source listing is indexed as **CC Attribution** on 2026-09-19. Creative Commons Attribution reference: https://creativecommons.org/licenses/by/4.0/ . Direct page retrieval returned HTTP 403 during this task; the listing's indexed text supplies the author credits and CC Attribution label. The local source ZIP has no standalone license file. This record preserves the source chain and does not assert new redistribution authorization for the complete archived package. The initial migration did not publish the package. The 2026-09-20 publication contains project source recipes and this attribution only; the source package, meshes, textures, animation samples and derivatives remain local.

Changes by the project: original Godot modular separation retained; gun-only mesh extraction; shared centimetre and axis conversion; mechanical root/hierarchy and independent furniture bones; separate local-pivot part exports; UE PBR material with normal green-channel conversion; UE skeletal/static mesh import. No replacement gun geometry or third-party hand model was added.

Keep the authors, source links, license reference and modification notice with redistributed derivatives.
