# Gunplay delivery validation — 2026-09-09

Project: `D:/FPS3D/FPSGAME`, Unreal Engine 5.8.2, Windows Editor Development module.

**Follow-up supersedes the original hand-quality conclusion:** the user correctly reported palm collapse during reload/charge. `../ArmsRepair20260909/README.md` records its repair, rejected intermediate meshes, remaining small close-up defects, and normal-time/hitch validation. The original fixed-step runs below did not detect either the deformation or all real-hitch timing defects.

## Build and saved assets

- `build-editor-exposure-delivery.log`: **Result: Succeeded**, exit 0, final weapon-FX compilation and module linking, 4.23 seconds. `build-editor-delivery.log` also records the successful Character build including the first-person motion-blur override.
- `build-shared-editor-success.log`: successful native module build including the animation graph, FX component and extended input audit. A prior shared-workspace link attempt caught unfinished UI timeline functions; the owning task completed them before this successful build. No UI stubs or reversions were added by this task.
- `../AKMReplacement/akm_runtime_materials_readback.json`: independent saved-asset readback passed for the final game mesh, all seven skeletal-compatible materials, shared skeleton and all ten clips.
- `build-flash-exposure-versioned.log` records `GUNPLAY_FX_BUILD_COMPLETE` after successfully saving `M_GunFlash_Exposure`. Its EyeAdaptationInverse material node compensates for scene exposure. A separate named asset avoids editing the earlier material held by the open editor. The commandlet's exit 1 reflects the existing GameFeatureData configuration error; the saved asset and subsequent rendered game runs are the validation evidence.
- The game logs identify `/Game/Weapons/AKMReplacement/Rendering/SK_AKM_Replacement_Game` as the actual loaded mesh. The final captured runs contain no missing-skeletal-usage/default-material fallback warnings.
- Actual screenshots show the replacement AKM, olive sleeves, charcoal gloves and steel/wood color separation. The supplied FBX references twelve absent texture images; the current material finish is locally authored PBR color/roughness/metalness, not recovered original textures.

## Standalone input runs

Each run starts a separate `UnrealEditor.exe -game` process and routes key press/release events through `APlayerController::InputKey`. Only ammunition setup and a temporary query wall are test fixtures. The audit does not force poses, movement velocity, ADS factors or recoil values to their expected result.

| Run under `Saved/GunplayUpgrade/` | Fixed simulation step | Viewport | Passed | Failed | Exit |
| --- | --- | --- | --- | --- | --- |
| `fps30-delivery` | 30 Hz | 1440 × 1080 | 42 | 0 | 0 |
| `fps60-delivery` | 60 Hz | 1280 × 720 | 42 | 0 | 0 |
| `fps144-final` | 144 Hz | 1280 × 720 | 42 | 0 | 0 |

Every row has `result.json`, `assertions.log`, named screenshots and a matching `runtime-<run>.log` in this directory. All have an explicit `GUNPLAY_ACCEPTANCE_COMPLETE failures=0` marker. The 30 and 60 Hz delivery runs include the final cosmetic FX tuning and exposure material. The 144 Hz run preceded those cosmetic changes; firing, input and animation timing logic is identical. Earlier successful runs are retained for before/after visual comparison. `fps60-fx` used a stale module after a file-lock build failure and is not delivery evidence.

These are timing and input correctness checks at fixed simulation steps, **not measured rendering FPS benchmarks**.

Covered behavior:

- Equip gates held ADS, which resumes automatically after equip; aim pose calibration uses the replacement sight bones.
- Rear sight at 42.00 cm and front sight at 79.61 cm align to the camera. Measured transverse errors were at most 0.00001 cm; pixel error rounded to 0.000 in both tested aspect ratios.
- Controlled ADS burst, 0.1200-second fire interval, finite camera/weapon transforms, bounded bloom/recoil and cosmetic FX activity.
- Reload can coexist with sprint, slide and slide-jump; firing remains blocked during reload. At 60 Hz the slide sample reached 1146.22 cm/s and the slide-jump sample retained 749.37 cm/s horizontal movement.
- Normal reload settles 15 + 20 to 30 + 5 exactly once; limited-reserve empty reload settles correctly; dry empty state does not repeatedly reload.
- Holding the trigger through the last round and automatic empty reload resumes firing until the fixture reserve is depleted.
- Releasing and pressing again produces one initial shot, observes the full fire interval, and stops after release.
- Sprint-to-fire gate, near-wall muzzle obstruction and finite-lived FX cleanup.

## Visual evidence and scope

`Saved/GunplayUpgrade/fps60-delivery/` contains the final actual game captures. `07_EmptyReload_Charge.png` shows the restored magazine grip without motion-blur smearing. The `Frames` directory samples ADS, firing, reload movement, empty reload and hip fire at 10 captures per simulated second, from 2.8 to 17.0 simulated seconds. Preview derivatives in `SourceAssets/GunplayUpgrade/Preview/` are generated by `Tools/AssetPipeline/render_gunplay_preview.py`; repeated frames fill missing screenshot indices to preserve the original timeline. They are silent previews.

Final visual checks found a short pale-orange muzzle flash and sparks in hip-fire frame 0127, a reduced flash around the sight in ADS frame 0013, and rising smoke in frames 0024 and 0134. Smoke is a translucent wisp, not a dense screen-covering cloud. The original smaller FX were numerically active but too weak to identify; the final version increases the outer lobe to 21 cm, uses a 0.78 ADS scale, and raises smoke at 22 cm/s with 9/7 cm initial sizes. Flash lifetimes remain 45/65 ms and the pool remains capped at 64.

The final MP4 and GIF each contain 142 frames at 10 FPS (14.2 seconds). MP4 full decoding completed successfully; Pillow read back all 142 GIF frames at 720 × 405. The 2 × 2 comparison was visually inspected. The absent screenshot index 20 is held from index 19, without speeding up the action.

The motion source was inspected before adaptation; contact timing and left/right action asymmetry were retained. The arm asset is a smooth stylized CC0 WRAD adaptation, not a scanned photorealistic hand. Editable Blender sources, original licenses and import scripts are preserved in the two asset source directories.

No human mouse/keyboard playthrough, audio listening review, multiplayer validation or packaged Shipping build is claimed. The current weapon remains the existing single-player UE hitscan implementation.

Unrelated existing startup logs still report the missing GameFeatureData asset-manager rule and experimental editor Python toolset classes unavailable in `-game` mode. They did not prevent these runs from completing and were not modified as part of gunplay work.
