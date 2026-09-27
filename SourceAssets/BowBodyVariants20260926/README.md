# Three wooden bow bodies · V14

Production source for 游隼 (swift_limb), 磐木 (heavy_limb), 静枝 (steady_limb).

Editable source: `Bow_ThreeBodies.blend`. The three FBXs in `Export/` use centimetres, the original bow pivot and no object scaling. Each contains only the continuous wood body (4,767 source vertices / 9,216 triangles). Grip wrap, string, arrow rest, sight and arrow remain separate runtime parts.

The fitted centre and end string notches are copied from `../BowModular20260926/Bow_ModularParts.blend`; the donor is the user-provided Sadra Medieval Wooden Longbow, described in `../../Docs/Weapons/dark-bow-wood-longbow-20260925.md`. These are local derivatives of that model, not wholly original geometry. No Meshy job, upload or credits were used. New grain/roughness/normal/laminate maps were authored locally by `make_textures.py`. The existing atlas remains in the material at the protected mounting surfaces.

Production order:

1. Blender background `read_donor.py` extracts source shell membership and cross-section inputs for authoring.
2. Python 3.11 `make_textures.py` creates nine 2048 px PBR maps.
3. Blender background `author_bodies.py` creates the three continuous body variations, FBXs and editable blend.
4. Blender background `render_icons.py` produces three actual part icons (1024 px RGBA, installed orientation, 84% fill). This is catalog artwork production, not gameplay acceptance rendering.
5. `run_import.ps1` saves the models, materials, textures and icon Texture2Ds, then executes `install_config.py` to add only these riser options to the current catalog and copy the three PNGs.

`import-receipt.json` records saved UE assets; `install-receipt.json` records the applied options and PNGs. `authoring.json`, `texture-authoring.json` and `icon-authoring.json` describe the production inputs and outputs. The first import created the assets; the follow-up explicitly disabled generated lightmap UVs to retain authored timber UV1 before catalog activation.

Texture UV0 and positions at the central attachment surfaces are retained. UV1 follows longitudinal timber and flush laminate layers. Vertex red controls the continuous blend into the retained original wood. UE preserves imported vertex colours and derives a UV1 tangent basis for the added normal map. Automatic lightmap UV generation is disabled because UV1 is used by the material.

The wrapper uses the existing UE batch mutex. It uses an existing editor bridge when appropriate, otherwise a background NullRHI commandlet. It does not start an interactive editor or gameplay. This pass adds data/assets only and does not require a native DLL rebuild. In-game appearance, ADS fit and balance remain for the user to test.

Integration record: `../../Docs/Weapons/bow-three-body-production-v14-20260926.md`.
