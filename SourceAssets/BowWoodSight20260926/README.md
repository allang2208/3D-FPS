# Carved wooden bow sight V12

Original small open sight, adapted from the user-provided BV1jGdDBkEkc 33–48 s reference. The woodwork replaces V11's block clamps, metal adjustment bar and knob. No geometry or texture was extracted from the video. The retained wooden longbow's existing licensed texture set is reused within the same project; its original provenance remains in `SourceAssets/DarkBow20260925/WoodLongbow20260925`.

The authoring script reads the actual connected wooden riser shell, fits a curved feather-edged saddle into the unbound 12.1–19.3 cm region, and follows its real cross-sections with two fine three-turn twisted linen lashings. Swept support, rounded open aperture, and tapered aiming post are fused into a continuous wooden body. Two dowel end-grains and a small non-emissive pale wooden aiming insert finish the piece. The aperture's inner radius is approximately 1.48 cm.

Source: `Bow_CarvedWoodSight.blend`; export: `Export/SM_Bow_CarvedWoodSight.fbx`. The runtime coordinates are centimetres in the retained riser's local frame. Aiming insert centre is `(-3.5, -10.1, 16.5)`. `authoring.json` records the actual export triangle count and source texture information. Blender's Y axis is reflected during export using the same route as V11.

`import_assets.py` creates and saves a separate static mesh plus three materials under `/Game/Weapons/DarkBow20260925/WoodSightV12`. It reuses existing longbow textures without modifying them. Imported resources and FBX source hash are written to `import-receipt.json`. `run_import.ps1` waits for current background asset/build work, then uses the existing editor's bridge if one is running, otherwise the established headless commandlet and batch mutex. It never opens an editor window, runs PIE, or changes a live equipped weapon.

After asset saving, `install_config.py` activates revision 23, the physical aiming insert, ADS distance 75 cm (previously 78 cm), aim-in 0.24 s, and aim-out 0.20 s. Existing SmoothStep/Slerp assembly alignment keeps bow, arms, string and arrow on the same pivot. Arrow tail and arrow-rest constraints are retained; no stage-specific arrow teleport is introduced. The 3 cm movement is an authored adaptation, not a measured displacement from the reference video. FOV scale stays at 0.9.

The C++ official-part whitelist now includes V11 and V12 sight paths. This lets the normal inventory presentation migration replace an older shipped sight without treating it as a user-customized part. Custom third-party part mesh paths remain preserved by the existing rule.

Default delivery includes source, necessary build, imported saved assets, and catalog integration. Gameplay, renders, screenshots, and acceptance are left to the user as requested.

Delivered 2026-09-26: FPSGAMEEditor background build succeeded (`Saved/BowAudioStillNorth20260926/build-bow-wood-sight-v12-20260926.log`); headless import saved all four assets (`import-receipt.json`); catalog revision 23 and the cook directory were activated. The final mesh is 54,464 triangles including actual twisted cord geometry. No editor window, game, render, or gameplay test was started for acceptance.
