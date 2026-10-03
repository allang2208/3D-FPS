# Pit Viper 2011 fire production

Reuses M1911's full native firing motion, blended in local bone space before the Pit Viper grip/contact adaptation. Eight sequences cover single hip/ADS normal/last-round fire and both dual hands' normal/last-round fire. The original V7 rigs, mesh/material assets, and quick-combat delta profiles remain on their existing paths.

Production order: `run_authoring.ps1`, `publish_sources.py`, `import_fire.py` through the project's existing gated background/bridge launcher, `build_editor.ps1`, then `finalize_delivery.py`. Authoring exports eight fire FBX files and three editable Blender scenes. Publishing merges only fire rows into the original full family and keeps prior sources under `BeforeSources`; importing preserves native skeletons and keeps replaced packages under `BeforeAssets`.

Full-family rebuilds use the corrected canonical `author_pit_viper.py`, `prepare_authoring_recipe.py`, and `fire_motion.py` in `../PitViper2011Integration20261002`.

Hip and dual motion duration is 0.35 seconds, ADS is 0.30 seconds. Local-pose gains are 0.62 for single hip, 0.32 for ADS, and 0.95 for dual. Base shot interval remains 0.15 seconds. The native fire clock and dual 8 ms entrance require the regular Editor DLL build. See the production receipts for actual import/build status. No runtime test or acceptance render is performed.

Final production: all eight current fire sequences were reimported and saved by the headless commandlet (exit 0). The regular Editor build returned `Succeeded` with the target up to date; corresponding objects and the base DLL were saved after the source changes. Last-round top-round hiding uses 0.0001 scale to avoid singular FBX transforms. Delivery is complete for sources, assets, and native build; gameplay/visual testing remains for the user.
