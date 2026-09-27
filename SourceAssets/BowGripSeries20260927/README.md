# Bow grip series V20

Three independent, fitted grip variants for the existing `grip` slot. Retained original green and waxed-linen options are not replaced.

Production order:

1. `py -3.11 author_textures.py`: original woven linen/leather BaseColor, ORM, normal maps.
2. Blender background `author_grips.py`: fitted editable geometry and FBXs in centimetres.
3. Blender background `render_icons.py`: production catalog PNGs from these meshes, not gameplay acceptance captures.
4. `run_import.ps1`: save meshes, materials, textures, and UI Texture2Ds using the existing UE batch mutex.
5. `py -3.11 install_config.py`: append catalog options and install PNG/cook references after actual asset save.

Source of mounting geometry: retained `../BowModular20260926/Bow_ModularParts.blend`, derived from the existing project wooden longbow. New grip topology, stitching, textile and leather texture artwork are locally authored. The retained bow source retains its original provenance/licence; this work does not publish or relicense it.

Editable model: `Bow_GripSeries.blend`, including hidden pre-join construction components. Icons have their own editable scene `Bow_GripSeriesIcons.blend`. Source parameters and modifiers: `series.json`; geometric production data: `authoring.json`; saved UE assets: `import-receipt.json`; installed choices: `install-receipt.json`.

UE folder: `/Game/Weapons/DarkBow20260925/GripSeriesV20`. No C++ modification or build is needed. No game test is run. Visual contact and balancing await the user.

Full Chinese design and integration record: [bow-grip-series-v20-20260927.md](../../Docs/Weapons/bow-grip-series-v20-20260927.md).
