# Fine frost-eagle blade sigil

The user requested blade rune detail matching the existing wolf rune. The original `ProductionV1/Art/RavenSigil.png` consisted of broad feather polygons. The new `Art/RavenSigilFine.png` uses the accepted wolf blade sigil's ornamental density: a raptor brow and beak, layered feather channels, cutouts and a tapered lower flourish. It is a white/alpha engraving mask, distinct from the full-color HUD eagle crown. The original built-in `image_gen` output is preserved; `prompt.json` contains the prompt and original output path.

`fit_projection.py` uses the same source-mesh/BVH fitting method as the wolf refinement. It fits the actual visible sigil to both flat faces with an edge margin, retaining the source aspect ratio, and writes the six layouts both here and into `ProductionV1`. This is production placement work, not a gameplay test or visual acceptance render.

`install_surfaces.py` replaces the existing `/Game/Weapons/Kukri20261020/FrostRaven20261028/Textures/T_FrostRavenGlyph` and updates the six `M_FrostRaven_*` / `MI_FrostRaven_*` pairs: Factory, Swift, HeavyBack, FoldedBalanced, Hunter and Canine. It retains the blade's original PBR, normal map and vertex-to-pixel local-position interpolation. `FineRuneGlow.hlsl` retains the existing breathing timing and lowers the blue emission peak to keep negative spaces readable. HUD, icons, gameplay stats and replication are outside this edit.

`ProductionV1/import_assets.py` uses the new artwork, layouts and emission on replay; `ProductionV1/prepare_assets.py` routes fitting to this canonical fitter. `install-receipt.json` records actual compiled/saved assets. No game, screenshot or multiplayer acceptance run is started.
