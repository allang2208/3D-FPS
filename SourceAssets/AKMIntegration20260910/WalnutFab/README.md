# AKM Fab walnut upgrade

Source: Quixel Walnut Veneer, https://www.fab.com/listings/67d7d60c-e92a-4fd9-8994-787f121aeaf9 . The selected Fab listing was shown free. Complete 4K files were found in the existing Epic launcher VaultCache `FabLibrary/Walnut_Veneer-67d7d60c/texture-set`; no alternate-site texture was substituted. Source metadata and original scans are retained in `Source/`, with SHA256 in `applied.json`. These are licensed project dependencies, not public source-package redistribution.

`build.py` edits only wood-face UV loops. Stock and handguard use separate cylindrical centers and offsets, with grain aligned along the weapon axis and the seam underneath. Body vertex coordinates are hash-checked unchanged. M4 arm geometry/weights, rig rest pose and all animation tracks are retained. Metallic, Bakelite and both hand slots remain unchanged.

The roughness range is 0.30–0.42 and normal strength 0.06. `refine_tone.py` applies the final linear tint (0.8, 0.38, 0.25) through `MI_AKM_RedBrownWalnut`, removing the first version's orange cast in daylight. This uses a Default Lit satin dielectric surface, not a separate clearcoat layer. `AKM_WalnutFab_Editable.blend` contains packed maps and the corresponding authoring finish.

Reproduce with Blender `build.py`, UE `import_apply.py`, UE `refine_tone.py`, then `verify_final.py`. Run import scripts with game test processes closed; a live process can lock the runtime mesh package. Runtime now selects `/Game/Weapons/AKMIntegration/WalnutFab/SK_AKM_MannyNative`; animations retain the SourceMatched path. The previous mesh is backed up as `/Game/Weapons/AKMIntegration/WalnutFab/SK_AKM_BeforeWalnut`.

The open editor locked the earlier SourceMatched mesh and material during final tint application. The final revision therefore uses the separately saved WalnutFab mesh and its verified material instance. `verify-final.log` confirms the serialized final tint and mesh binding, with `AKM_WALNUT_FINAL_BINDING_PASS`; `build-final-module.log` confirms the runtime-path build succeeded. The editor was not forcibly closed.

The initial UE clearcoat property binding was unavailable through Python; it was removed before successful import. A subsequent import encountered a concurrently rebuilt module; rebuilding and rerunning produced `AKM_WALNUT_FAB_PASS` in `import-v3.log`. These failed attempts are not reported as completed imports. `runtime-akm-walnut-fab-v1.log` passed the UV/material revision's firing, ADS, reload and inventory checks with clean exit. Final color validation is recorded separately.

## Final acceptance

`runtime-akm-walnut-final-v3.log` passed with zero failures and clean exit after the final WalnutFab runtime reference was compiled. Daylight frames were inspected, including frame 0060 showing the exposed handguard. `Saved/WeaponIcons/20260911000259-1280.log` passed the rendered inventory icon checks. Its inspected AKM image is `after.png`, also copied to `Content/ColdSteelData/Icons/ue_akm.png`; `before.png` preserves the previous material appearance. `render-final.log` and side/oblique renders refer to the final editable source tint. The already-open editor requires restart to load the changed native reference and refresh loaded resources.
