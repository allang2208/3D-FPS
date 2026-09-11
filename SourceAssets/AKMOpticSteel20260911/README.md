# AKM optic metal material parity — 2026-09-11

Archive update (2026-09-11): superseded files mentioned below now reside under local `trash/akm-optics-workflow-20260911/SourceAssets/AKMOpticSteel20260911`. The per-file manifest is `Docs/Weapons/akm-optics-archive-20260911.json`. Final sources and accepted run folders remain in place. Historical failed iteration paths are evidence references, not active reproduction inputs.

Final acceptance: **274 runtime checks, 0 failures** across holographic (41), panoramic (58), prism (59), LPVO (116). All final logs contain no material compile fallback. Actual hip/ADS captures were visually reviewed, including the restored dark prism interior and LPVO body/ring. `acceptance.json` records final production asset hashes.

Audit found that the AKM bridges used Soviet AKM steel, but the holographic, panoramic, 2× prism, LPVO body and LPVO moving ring still used their M4 body materials. This revision supplies AKM-only mesh/material variants in `/Game/Weapons/AKMIntegration/SovietFab/OpticSteel` and updates only the AKM runtime references.

The original body material graph is retained. Its metallic output defines the metal replacement weight `clamp((metallic - 0.2) * 5, 0, 1)`. Metal regions use the same AKM steel base color, metallic and roughness textures as the bridge. Original nonmetal regions and original normal detail remain; glass and reticle material assignments are unchanged. The LPVO ring shares its AKM body material. Existing bridge materials are already consistent and remain unchanged. For prism/LPVO, a corner-color mask excludes inward-facing optical tube surfaces: inspection showed these must keep the original dark finish rather than become reflective gun steel.

`build.py` preserves vertex positions and UV0, adds a physical-scale UV1 for the AKM steel, saves editable `.blend` sources and exports FBX. This avoids sampling the AKM gun atlas through another model's UVs. Triangles remain identical to the formal source meshes. `geometry.json` and `slots.json` record geometry and source assignments; `import.json` records final assignments. Existing Fab AKM material provenance is reused; M4 assets are not edited.

Reproduction is `build.py`, `import.py`, then `import_interior.py`. These reconstruct only the new AKM variants. `import-corrected.log` and `import-interior-final.log` contain the successful import markers. Initial iterations exposed an editor-property name mismatch and then an unconnected clamp pin; these were fixed. Commandlet startup still reports the project's preexisting GameFeatureData/Toolset/HTTP errors, so its nonzero exit is not called a clean commandlet run.

`build-native.log` records successful native compilation. `run.ps1` supports holographic, panoramic, scope2x and lpvo, using the actual game map and isolated audit profiles. Final runs are holographic/panoramic `steel2` and scope2x/LPVO `steel4`; `steel1` is the rejected initial iteration. Runtime acceptance includes absence of material compile fallback as well as gameplay checks.

Restart the existing editor to load the changed AKM references and new material assets. No player save or inventory was modified by the isolated audits.
