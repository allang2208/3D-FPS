# M4 holographic attachment

Uses the two source assets already supplied in this UE project. No new external asset was downloaded.

- Optic source: `Content/holographicpacked.fbx`, SHA256 `74F035EF51090A65B335BB7B6E638016C3362D79EF53441CAE4B19BE54995D5D`.
- M4 source: `Content/m4noskel.fbx`, SHA256 `51CD3308506C4EE404800B84C726599592FDFEFE5B03798E066A85CC77B719F5`.
- Runtime M4 remains `/Game/Weapons/M4InfimaRigV4/SK_M4_Infima`, including its existing ReloadFinger clips. No skeleton or animation package was changed by this task.
- Editable optic: `M4_Holographic_Editable.blend`; normalized export: `SM_M4_Holographic.fbx`.
- New UE packages: `/Game/Weapons/M4Holographic`. Original texture packages are preserved. `T_HoloORM` corrects the copied packed map's mistakenly assigned normal-map compression.
- The original base-color alpha makes the lens window transparent; the original red-ring texture supplies the luminous masked reticle. This is a finite-distance reticle, not an optical collimation simulation.
- Source license documents were not included with these two root FBX files; this task preserves the project's existing asset provenance and does not assert a new license.

Rebuild with `Tools/AssetPipeline/prepare_m4_holo.py` in Blender and `Tools/AssetPipeline/import_m4_holo.py` in the UE Python commandlet. Import commandlets currently emit existing project GameFeatureData/HTTP-listener errors independently of the `M4_HOLO_IMPORT_PASS` marker; verify the saved packages in the rendered runtime audit.
