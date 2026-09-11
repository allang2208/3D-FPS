# AKM side bridge refinement — 2026-09-11

Archive update (2026-09-11): superseded files mentioned below now reside under local `trash/akm-optics-workflow-20260911/SourceAssets/AKMBridgeRefine20260911`. The per-file manifest is `Docs/Weapons/akm-optics-archive-20260911.json`. Final sources and accepted run folders remain in place. Historical failed iteration paths are evidence references, not active reproduction inputs.

Final result: **233 runtime checks, 0 failures** (panoramic 58, prism 59, LPVO 116), plus three FBX geometry checks. Actual final side views and ADS captures were visually reviewed. `acceptance.json` records production asset SHA-256 hashes and the three successful game-process logs.

Replaces the three block-shaped optic bridges with a tapered, windowed side bracket, thin rail carrier, recoil grooves and recessed hex clamp screws. Source positive-X is the receiver face opposite the selector and ejection mechanism; the side bracket mounts there. No optic, firearm, hand animation, transform, stats or catalog code changes are included.

The mounting surface remains at root Z=0.113 m, with the same individual fore/aft positions and physical optic size. The three production asset names under `/Game/Weapons/AKMIntegration/SovietFab/Optics` are preserved, so all existing saved configurations use the refined geometry. Material remains the accepted `M_AKM_Soviet_MountSteel` from the AKM Fab source. New geometry is authored locally; existing asset provenance remains applicable.

`build_mounts.py` produces three editable full-assembly `.blend` files, FBX bridge exports and actual-model close-up renders. `validate_geometry.py` checks FBX readback for degenerate faces, nonmanifold edges and UV availability. All three pass; the short bridges have 4480 triangles each, the LPVO bridge 5048. `geometry.json` records source hashes. The prior production rollback assets from `Before/` are now in the corresponding archived `Before/` directory listed in the manifest.

`import-final.log` is the final import record. The intermediate import encountered a file lock from our running LPVO audit; after that process finished the import was repeated. Commandlet startup includes existing unrelated Toolset errors and exits nonzero, so the import PASS marker, readback and new game-process results are reported separately.

Final runtime captures and logs are in `panoramic-bridge2`, `scope2x-bridge2`, and `lpvo-bridge2`. The earlier `bridge1` runs are intermediate iterations, not final visual acceptance. Run `run.ps1 -Kind panoramic|scope2x|lpvo -Run <unique-name>` to reproduce an isolated rendered game audit with actual gunsmith, save, pickup/icon, ADS, shooting, reload and LPVO zoom coverage. Historical M4 filenames belong to the shared audit; the selected weapon is AKM.

Reload the editor/project if it still holds the previous mesh in memory. No native rebuild is required for this geometry-only revision.
