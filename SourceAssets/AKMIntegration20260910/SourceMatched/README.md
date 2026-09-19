# Source-matched AKM candidate

This supersedes the wrist-only NativeBaseline candidate once runtime validation is complete.

## Motion

`build_source_matched.py` uses the existing AKM source actions in `ArmsRepair20260909/Integrated/SK_AKM_HandsRepair_Source.blend`. Actual source renders are in `../SourceReview`; reference gameplay was also reviewed. Preserve the 3.333333 s normal reload, 4.291667 s empty reload, and all other source clip durations.

Manny's 20,326-vertex M4 arm mesh, weights, rest skeleton and materials are preserved. Palm frames are derived from the wrist and MCP row to remove incompatible bone-roll conventions. MCP row alignment compensates palm-length differences. Each finger follows the animated source orientation relative to the palm with bind-axis correction; local rest translations preserve target finger lengths. The previous frozen M4 idle fingers are no longer used.

`AKM_MannyNative_Editable.blend` and ten FBX clips are reproducible authoring outputs. `retarget.json` reach errors prove the arm solve only, not surface-contact acceptance. Side and palm renders cover idle, magazine retrieval, insertion and empty-reload action. Runtime and compressed animation checks must be recorded separately.

## Fab metal

User requires Fab material assets. Use the already acquired Quixel Dirty Metal: https://www.fab.com/listings/17d58a5d-f1a8-4417-9e6f-f21ed6fc7031 . Acquisition and original files are documented in `../../ChestZiarat20260909/README.md` and its Source directory. This is an imperfection scan, not an author's AKM PBR pack or a complete steel basecolor set.

`../apply_fab_gunsteel.py` creates an AKM-only dark steel material using the acquired packed map: G roughness remapped to 0.28–0.48, R subtle contamination, metallic 0.95. It avoids M4's model-specific baked color and normal atlases, which do not match AKM UV islands. It leaves the existing redwood and M4 hand materials intact. `fab_material.json` records actual bindings after application.

Fab Real Materials Samples was also located, but browser acquisition timed out; it is not claimed downloaded or used. No ambientCG steel substitution was applied.

## Runtime validation

`runtime-akm-source-matched-fab-v1.log`: all gameplay assertions passed with clean process exit; 264 actual frames and mixer audio are preserved in Delivery. Both reload transition contact sheets were visually reviewed, as were full-resolution idle, magazine and bolt frames. `runtime-akm-source-matched-switch-v3.log`: preserved modified-M4 fixture passed body/sight visibility and repeated switching. Current player-save clone separately showed the complete AKM but did not contain the second equipped weapon required by this switching fixture.

`Saved/WeaponIcons/20260910233546-1280.log` passed the real model icon audit. The inspected `variant-4-1280.png` was copied to the AKM fallback icon. `AKM_Fab_SourceMatched_Editable.blend` includes the new motion with packed wood and Fab imperfection maps. Shader authoring is reproduced by the UE script and the Blender editable-source script; neither modifies the M4 source materials.
