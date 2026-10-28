# Unified sapphire eagle crown

2026-10-28: the user identified a style mismatch in the game screenshots. V2's silver feather rims, metal beak and ring/jewel pedestal differed from the transparent blue energy column; adding a local socket shader did not resolve that original art direction.

The built-in `image_gen` edit in `Art/FrostRavenCrystal.png` follows the accepted ruby wolf's carved crystal material language in blue. The eagle silhouette remains recognizable, but the metal collar and separate jewel are removed; the feathers continue into an integral crystal throat. Original generated RGBA pixels are preserved. `prompt.json` records the full prompt and original output location.

`compose_head.py` uniformly fits the feather shoulders, centers the throat, and blends its lower section into the unchanged glass column. `CrystalComposite.hlsl` tints bright facets blue and replaces V2's added socket geometry. No new particle system, world geometry, gameplay code, numbers, rarity or viewport-anchor change is included. Right-side placement and legendary classification remain in the existing native code.

`install_head.py` imports/saves only `T_FrostRavenCrown` and compiles/saves `M_FrostRavenEnergyHud` at their existing runtime paths. It stops before edits if PIE is active or either owned package has unsaved changes. `install-receipt.json` records actual results; it does not claim visual or gameplay acceptance. `ProductionV1/prepare_assets.py` and `import_assets.py` now use V3 as the canonical crown.

V2 source files are archived under `trash/kukri-refinements-retired-20261028/SourceAssets/KukriFrostRaven20261028/CrownImageV2`. Do not replay their installers over V3. User-supplied screenshots are the visual diagnosis evidence; this artwork revision did not run gameplay, screenshots or acceptance tests. Later scoped audit evidence is recorded separately in `CompletionAudit/result.json`.

## Lower throat width fit

The user requested the connection match the column width. The source throat at row 1125 was 333 px wide, while the shoulder used for the uniform head scale was 423 px wide. The lower throat therefore covered only 78.7% of the 182.04 HUD-pixel column. `compose_head.py` now applies a local horizontal scale of 423/333 to the lower throat, smoothly introduced from source row 1000 to 1125; the upper portrait projection is unchanged. The width fit is centered on the same measured throat midpoint. Root fade begins at HUD row 520 so the full-width connection stays visible before blending into glass. This is a targeted HUD projection adjustment; the source RGBA image is unchanged. `install_layout.py` saves only the HUD material and records the outcome in `width-fit-receipt.json`.
