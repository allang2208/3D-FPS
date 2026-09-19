# AKM gunplay upgrade — 2026-09-09

Target: `D:/FPS3D/FPSGAME`, UE 5.8. Reference only: `E:/3d/3-dfps`.
This is a single-player implementation. The existing weather, UI and maps are owned by other tasks.
Before-edit Character and input configuration copies are in `backup-20260909/`.

Follow-up to the user's palm-collapse and frame-time feedback: see `../ArmsRepair20260909/README.md`. The current default mesh is `/Game/Weapons/AKMReplacement/HandsRepair/SK_AKM_HandsRepair`; it replaces the initial WRAD fit described below. Continuous-fire catch-up, action/ADS clock starts and FX integration were also repaired. Earlier delivery tests are historical evidence, not acceptance of the reported hand deformation.

## Runtime behavior

- Native pose graph blends idle and aim continuously, with a separate action layer. Actions have 35 ms entry / 100 ms exit blending; the 100 ms mechanical fire clips use shorter 8/28 ms envelopes.
- ADS enters in 240 ms and exits in 180 ms. Camera and weapon share a reversible smoothstep transition. Vertical FOV remains 75 / 55 degrees (107.512 / 85.566 horizontal at 16:9).
- ADS alignment evaluates both actual sight bones from the aim clip once and solves the complete weapon transform at 42 cm rear-sight eye relief. Moving bolts are not used to counter-animate the hands. Every ADS shot snapshots the visible front sight before applying its next recoil impulse.
- Camera control aim and visual recoil are composed explicitly. Predictable climb remains player-controllable; a separate spring supplies kick and recovery. ADS lateral shake, FOV punch and walking camera bob are reduced for target visibility. Landing has a short damped response.
- Raw mouse input has no engine smoothing or duplicate FOV scaling. ADS sensitivity follows tangent-of-FOV magnification and exposes a multiplier.
- The first-person camera overrides motion blur to zero so sight edges and mechanical contacts stay readable during turns and reloads.
- Fire cadence uses one monotonic clock, including repeated clicks and held fire across actions. Sprint-to-fire is 180 ms. ADS movement is 300 cm/s standing and 220 cm/s crouched.
- Reload and sprint remain independent; reload can continue through C slide and slide-jump. Holding aim through a reload re-enters ADS when the action completes. Magazine/reserve settlement occurs once at completion.
- Reload retains 2.7 / 3.466667 second gameplay lengths. A monotonic source-time map accelerates approaches and settles at the original mechanical contacts. Sounds use the inverse of that same map; seating and bolt release add small whole-weapon impulses.
- A camera target ray and camera-to-muzzle obstruction check prevent firing through cover. A near-wall pose retracts the gun. Existing UE hitscan damage is retained; this does not port Godot's 90 m/s projectile simulation.
- Short layered muzzle flashes, 45 ms warm light, sparks, heat-dependent world-space smoke and ejected brass are provided by `FPSWeaponFXComponent`. A bounded 64-slot pool owns finite-lived cosmetic components. Impact classification recognizes metal/wood labels with a generic fallback.
- `M_GunFlash_Exposure` uses UE's inverse-exposure node to retain a readable short flash in daylight. The outer lobe and rising smoke were tuned against actual hip-fire/ADS captures; ADS still reduces the effect scale.

## Assets

`../AKMReplacement/` retains the user-supplied `D:/迅雷下载/akm.fbx` source identity, conversion scripts, editable blend, exported clips, sight markers and actual previews. Its referenced 12 texture images are absent; replacement PBR steel/wood/bakelite materials are authored locally. The new mesh needed small usable rear/front aiming elements, documented in its conversion report.

The runtime mesh is `/Game/Weapons/AKMReplacement/Rendering/SK_AKM_Replacement_Game`, with seven saved skeletal-compatible materials. It shares the ten clips and skeleton in `/Game/Weapons/AKMReplacement/`.

`../ArmsReplacement/` records the free CC0 WRAD arms, anatomical weight adaptation, smooth full-finger gloves and olive sleeves. This is a rounded stylized tactical model, not a scanned hand. The Fab PolyOne free mesh was separately added to the library; a browser download completion did not yield an accessible local source and it is not the runtime arm asset.

`../GunplayFX/` contains original procedural material source, build script and import report.

## Design references

These inform the tuning direction; no claim is made to reproduce proprietary COD/Apex internals or exact weapon statistics.

- COD's aim-sway/visual-recoil discussion: https://www.callofduty.com/patchnotes/2024/11/call-of-duty-black-ops-6-season-01-patch-notes
- Apex's iron-sight visibility/fairness discussion: https://www.ea.com/en-gb/inside-ea/news/iron-sight-update
- Apex PC aiming settings: https://help.ea.com/en/articles/apex-legends/best-settings-pc/

## Validation

Asset reports distinguish finite geometry / animation durations from visual contact checks. The opt-in `-GunplayAudit -GunplayLabel=<run>` route exercises the PlayerController input path and emits explicit `GUNPLAY_ASSERT PASS/FAIL` and `GUNPLAY_ACCEPTANCE_COMPLETE failures=N`, with screenshots below `Saved/GunplayUpgrade/`.

Final build, runtime and measured results are recorded in `validation.md` after execution. Editor input simulation is not a claim of a human mouse/keyboard playthrough or completed listening review.

Reproduce a separate fixed-step run with `Tools/AssetPipeline/run_gunplay_acceptance.ps1 -Fps 60 -Label <new-label> -CaptureFrames`. The script refuses to overwrite an existing run, creates its own hidden standalone game process, and requires both explicit assertion results and the zero-failure completion marker. The 30/60/144 Hz settings test timing behavior, not rendering throughput.
