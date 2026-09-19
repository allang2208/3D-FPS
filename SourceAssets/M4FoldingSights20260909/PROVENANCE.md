# M4 folding sights — 2026-09-09

User-supplied M4 geometry, derived from the currently integrated Kmode handguard and M4 Body. No external replacement art was downloaded. Existing source licensing remains applicable; this work grants no new license.

- Baseline editable rig: `../M4HK416AudioEmpty20260909/M4_EmptyReload_BoltRelease.blend`.
- Original topology reference: `../M4Replacement/m4_source_imported.blend`.
- Editable result: `M4_FoldingSights_Editable.blend`, saved with heads upright.
- Build script: `../../Tools/AssetPipeline/build_m4_folding_sights.py`.
- Import script: `../../Tools/AssetPipeline/import_m4_folding_sights.py`.
- Rear: 420 vertices (aperture, neck and stalk); front: 561 vertices (protectors, post and adjuster). Bases remain in the skinned receiver/handguard.
- Original and exported vertex coordinates are matched through an affine fit, residual below 0.00000006 metres. Head and retained vertex counts sum to the original counts. UVs/materials retained.
- Existing hand rig, magazine, trigger, bolt weights and animation assets retained. No bones were added. Original shared skeleton SHA256 remained `FC33E15DADC45C4107C3E1A1FC19CDC5EF95BB63C3AD53F989F01D5D71962F10` after import.
- Pivot placement and 90-degree folding are authored game presentation, not manufacturer mechanical specifications. Runtime performs a 0.18-second smooth transition; there is no hand-operated folding animation.
- `folding-sights.json` records the component-space hinge, axis and angle data used by `M4FoldingSights.cpp`. Static heads attach to WPN_root, preserving receiver motion during firing/reload.
- Original assets are retained. Scoped code backups are in `trash/M4FoldingSights-before-20260909`.

Import completed with `M4_FOLDING_IMPORT_PASS`. The commandlet also reports existing project GameFeatureData/HTTP configuration errors and a bind-pose fallback warning. Import exit status alone is not acceptance; actual rendered game checks and screenshots are recorded under `Saved/M4GunsmithAudit`.
