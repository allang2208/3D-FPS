# Isolation ward asset provenance

This publication includes original authoring scripts, configuration and runtime handoff text. It does **not** redistribute meshes, texture atlases, UE packages, downloads or source exports.

| Asset | Creator / source | License record and local adaptation |
|---|---|---|
| Hospital Bed | [loxfear](https://sketchfab.com/3d-models/hospital-bed-f8c13a19e84343e7b644c19f7b9488d3) | CC BY 4.0; local `SourceAssets/HospitalBed20260929/license.txt`. Fitted collision, 1.5× scale and resting poses. |
| Rusty medical cart | [CarlosTorresVFX](https://sketchfab.com/3d-models/rusty-medical-cart-508d17d0d77c4d10a3a9ddc043241d31) | CC BY 4.0; local `SourceAssets/MedicalCart20260929/license.txt`. Fitted collision and dimension fitting. |
| Crutch and IV Drip | [Matt LeMoine](https://sketchfab.com/3d-models/crutch-and-iv-drip-5cc65c6aed374220b67f7d60e679153e) | CC BY 4.0; local `SourceAssets/IVDripCrutch20260929/license.txt`. Nonblocking derivative with visual occupancy. |
| Hospital Waiting Bench | [AshenCut](https://www.fab.com/listings/05f7dccc-ecee-4bd4-9cc1-189ab2f42cc5) | CC BY 4.0 per retained local import/source record; reused mesh and materials. |
| Blood Stain, sgfjdepc | [Quixel / Fab](https://www.fab.com/listings/765d43e1-45ef-42f2-80a5-43d6214aa1d3) | User-downloaded licensed asset, local metadata retained in `BloodScan20260929/Source/fab-metadata.json`. Use the user's acquired license; no independent entitlement or redistribution grant inferred. |
| Soviet Hospital / HospitalCorridor posters | User-imported `/Game/HospitalCorridor` pack | Existing pack license is required; 36 original poster/sign meshes and two atlases reused, not included here. No new license grant claimed. |

CC BY 4.0 terms: https://creativecommons.org/licenses/by/4.0/ . Preserve attribution with distributed derivatives.

Glass architecture and fracture geometry are original local precision/Voronoi authoring. [Niagara Destruction Driver](https://github.com/eanticev/niagara-destruction-driver) was reviewed at commit `881c350b0670a3a99dfe240ffdf284e1df6d9a86` (MIT); only its separation of intact collision and cosmetic shards informed this solution. The plugin and its runtime code were not copied or enabled. Existing project glass impact Niagara/audio and corridor materials keep their original project licenses. Local NDD reference checkout/license and provenance remain recovery references, not discarded experiments.
