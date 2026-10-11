# Super90 R22 camera strength

Camera-only follow-up to R21, calibrated from the current ASH-12 / PKM reload contact response. Keeps R21 weapon/right-arm/grasp assets and all source timing.

`prepare_camera.py` retains R16 measured background curves without R21's baked contact overlay. Runtime contact impulses in `WeaponActionCameraComponent.cpp` now use the shared impact gain. The exact changed-source baseline is saved under `Before/Source/`.

Run `build_r22.ps1` for background Editor / Game builds through the existing UE batch mutex. No animation imports or runtime tests are part of this revision. See `Docs/Weapons/super90-speedloader-r22-camera-strength-20261010.md` for amplitudes and completion status.
