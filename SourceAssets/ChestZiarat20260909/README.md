# Warehouse chest material replacement — 2026-09-09

Applied to `Content/ColdSteelData/warehouse_assets.json`; no C++ or gameplay changes.

## Source and ownership

User explicitly acquired and requested both Fab assets. Copied from the existing Epic launcher VaultCache, without downloading from alternative sources.

- Quixel Megascans, Ziarat White Marble: https://www.fab.com/listings/3a50ef74-5bf8-442a-ad74-37e31c53683c
- Quixel Megascans, Dirty Metal: https://www.fab.com/listings/17d58a5d-f1a8-4417-9e6f-f21ed6fc7031
- Fab Standard License shown in downloaded listing metadata. Assets retained as licensed project dependencies, not for standalone redistribution.
- Original files and Quixel metadata are in `Source/`. Original marble source SHA256 and actual image dimensions are in `source_report.json`.

## Implementation

- White_Marble_PBR -> MI_Chest_Ziarat_4K. 4096×4096 BaseColor, Normal, Roughness, Specular and Cavity. Color/specular sRGB; roughness, normal and cavity linear. Normal uses BC5. Source roughness is approximately the inverse of linear gloss. Specular F0 is converted to UE's normalized specular input using 12.5.
- Marble UV tiling 1.8: measured existing atlas density approximately 0.27–0.29 UV/m, matching the source's 2 m scan approximately. Existing mesh UVs follow the lid animation.
- Gold_PBR, Brass_Frame, Brass_Hardware and Brass_Strap -> MI_Chest_DirtyMetal_Brass.
- Dirty Metal is an imperfection asset containing a packed map, not a full basecolor/normal material. Its glTF explicitly binds G as roughness; R carries the source dirt mask; B is constant white. Kept original brass base tint (0.64, 0.36, 0.075), applied R×0.8 to darken dirt and reduce metallic response, and used G roughness. UV tiling 3.6. Did not import the glTF's unrelated preview plane or its metallicFactor=0 placeholder.
- Both masters support skeletal meshes and both instances explicitly override Two Sided=true. Master-only two-sided state produced missing lid faces in the first runtime capture; explicit instance overrides resolved this in a new runtime capture.
- New assets live under the existing always-cook Warehouse20260909 directory. The mesh, 0.9 s opening clip, 0.7 s closing clip, velvet, sapphire and blue interior material paths are preserved.

## Validation and limitations

- Both material import scripts emitted their PASS markers; serialized material dependencies were loaded in a separate UE process (`surfaces_verified.json`). Five marble maps plus one metal map resolved.
- Commandlets exited 1 due to the project's pre-existing GameFeatureData asset-manager rule errors; this is not reported as a clean commandlet exit. No new material shader compilation failure was found.
- Final standalone preview: `ziarat_dirty_twosided-1280-chest.log`, exit 0, `WarehousePreview: COMPLETE bounds=X=105.110 Y=90.624 Z=107.616`. Visually checked the complete closed lid and open lid/interior at 1280×720.
- Runtime still logs pre-existing original GLB material usage warnings before the actor applies its runtime material overrides; the new surfaces render successfully. Existing experimental engine Python toolset initialization errors remain outside this change.
- No packaged build or inventory regression suite was rerun for this material-only change.

## Preview and rollback

- Final screenshots: `After/chest-closed.png` and `After/chest-open.png`.
- `Before/warehouse_assets.json` and `Before/chest-*.png` preserve the earlier references and appearance. Restore only the five entries listed in `applied_slots.json` when rolling back, to preserve any concurrent unrelated manifest changes.
- `import_material.py` and `import_dirty_metal.py` are one-time candidate creation scripts; they intentionally reject existing master assets rather than overwrite them.
- Restart the current play session to create a chest with the updated manifest.
