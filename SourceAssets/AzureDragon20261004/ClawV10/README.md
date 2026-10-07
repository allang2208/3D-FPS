# Azure Dragon Claw V10 (live: Fab claw, revision 10.14)

Live: the library Fab Dragon Claw (CaptainHC) repaired and re-rigged, driven on the sword's own source
clock, with a spirit glass material that keeps the Fab normal atlas, arm-end flames, five talon rift
scars and the expiry dust. The user accepted the effects and the claw-tip reach on 2026-10-07; later
revisions (10.12-10.15) are built and saved but not yet experienced. Contracts and reusable methods:
`skills/ue5-weapon-workflow/references/azure-dragon-pending.md`; history: `Docs/Combat/enchant-azure-dragon-v10-20261006.md`.

Restore order (also chained by the root `run_install.ps1` → `install_current_ue.py`):
`../install_ue.py` (shared normal atlas) → `install_textures_ue.py` → `../HudV10/install_hud_ue.py` → `install_fab_ue.py`.

- `author_fab_claw.py` — Fab mesh from `../AzureDragonClaw.blend` and `../Export/finger-landmarks.json`:
  weld/close/flip repair, sculpted palm, one refinement level (talons kept sharp), five digits + tip leaves,
  forearm twist bone, smooth knuckle weights, vertex colour (along / talon / forearm fade; A = 0 on the palm),
  UV1-3 rest pose + joint ring, gesture (frames 0-36 rake with overshoot, 36-276 = 4 s idle loop). Output `ExportFab/`.
- `author_scale_detail.py` → `Export/T_AzureDragonClawScaleDetail.png` (tiling pebble-scale height).
- `author_textures.py` → `Export/T_AzureDragonClawVeins.png`, `T_AzureDragonClawSmoke.png` from the Bailian
  claw sources (`../HudV10/Generated/claw_001.png`, `claw_002.png`); `install_textures_ue.py` imports both to
  `/Game/Weapons/AzureDragon20261004/ClawV10/Textures` (the veins feed the claw glass; smoke is retained).
- `install_fab_ue.py` — imports/saves everything under `/Game/Weapons/AzureDragon20261004/ClawFab`:
  - `AzureDragonClawFabV10.hlsl` → `M_AzureDragonClawFabV10` (custom-depth front-surface test with 4 sub-pixel
    taps, near occlusion, scale-detail bump, V10.14 wind-front erosion `Disintegrate`/`DisintegrateCenter`/`DisintegrateAxis`);
  - `AzureDragonClawFlameV10.hlsl` → `M_AzureDragonClawFlameV10` (owned Realistic Starter VFX Pack Vol2 `T_Fire_F` /
    `T_Fire_D`, referenced read-only, recoloured cyan);
  - `AzureDragonClawRiftV10.hlsl` → `M_AzureDragonClawRiftV10` (talon rift scars after Rift Slash V4);
  - `AzureDragonClawDustV10.hlsl` → `M_AzureDragonClawDustV10` (expiry motes on C++ camera-facing quads);
  - `M_AzureDragonClawDepthV10` (two-sided opaque, custom depth follower only), the skeletal mesh, skeleton and gesture.
  - Overlays are alpha-blended (`build_overlay`, HLSL returns float4 emissive + opacity).
- `run_install.ps1` — bridge when an editor is open, background commandlet otherwise; preserves dirty/unowned
  assets and a running PIE. `-Script install_textures_ue.py` for the textures.
- `run_build.ps1` — background native builds (Game / Editor) with DLL-in-use protection.
- `ExportFab/rig.json` — bone/triangle/key manifest read by the installer.

Retired 2026-10-07 to `trash/azure-dragon-retired-20261007` (manifest `Docs/Publication/AzureDragon20261007`):
the V10.1 original Blender claw (`author_claw_v10.py`, its installer, HLSL, Blend, FBX and saved UE assets),
the superseded talon-trail and ember materials, the one-off material-usage patch and fire-pack probe, and old run logs.
