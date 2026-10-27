# Magic Arrow Rain visibility V4 — 2026-10-27

Requested: thicker green falling-arrow light and a more readable, explosive airburst. Author for the existing 10–40 m combat view, with short local effects at the burst and no screen-space flash.

## Runtime presentation

- Falling trail radius: 2.6–3.2 cm, previously 0.95–1.30 cm. Maximum length remains 300 cm. The arrowhead stays emissive during the whole 0.125 s fall, then fades over 0.07 s after contact.
- `M_ArrowRainTrailV4` is a dedicated additive cylinder material: soft silhouette, bright emerald core, pale inner highlight, axial fade and flowing modulation. It requires no texture or extra mesh/component. The held-arrow `M_ArrowRainFlow` is preserved.
- Airburst: one 0.24 s ragged core, two pressure fronts offset by 0.035 s, 18 rolling smoke sprites and 14 radial streaks. The main front reaches approximately 7.8 m visible width at the default radius. The core expands rapidly and holds its strong phase for 0.065 s; inner smoke clears by 0.27 s, while outer smoke expands and fades by 0.90 s.
- 35 airburst particles, up from 28; no new runtime component, light, sound layer or texture. Each smoke sprite retains the existing two atlas-frame samples. The wider pressure fronts increase brief transparent coverage; no performance measurement is claimed.
- Cone V3 launch, doubled speed, contact effects and damage timing are unchanged. Existing costs, aiming, cooldown, area damage, audio and replication stay on their current paths. The asset list includes the new trail for the existing asynchronous preparation path.

## Sources and recovery

- `CoreMask.hlsl`, `WaveMask.hlsl`, `TrailOpacity.hlsl`, `TrailColor.hlsl` are original procedural material sources.
- Incremental author: `Tools/Skills/build_magic_arrow_rain_visibility_v4.py`.
- Background build/save entry: `Tools/Skills/import_magic_arrow_rain_visibility_v4.ps1`. Uses the shared UE authoring mutex, waits for existing builds, and refuses to overwrite loaded FPSGAME binaries/packages. Does not start the GUI or game.
- Full restore: `Tools/Skills/build_magic_arrow_rain_assets.py` applies base assets, V2, Cone V3 and then Visibility V4.
- Exactly five owned saved assets: `M_ArrowRainBlastCoreV4`, `M_ArrowRainBlastWaveV4`, `M_ArrowRainTrailV4`, `M_ArrowRainMetal`, `NS_ArrowRainBurst`, all under `/Game/Skills/MagicArrowRain20261026`.
- Read-only dependencies: V2 burst smoke, base glow and the existing approved Mantaflow atlas. The V2 pressure-front material remains unchanged because Cone V3 surface rings use it.
- `Before/` preserves any previously existing owned packages once. These are scoped recovery inputs, not a whole-project restore.
- Production logs and save receipt: `Saved/MagicArrowRain20261026/VisibilityV4/`.

Production completed 2026-10-27 13:02 (Asia/Shanghai): regular Editor and Game Development builds succeeded; the asset commandlet exited 0 and saved all five owned packages. See `Saved/MagicArrowRain20261026/VisibilityV4/asset-receipt.json` and the build/author logs beside it. No GUI/game was launched, and no game, render, audio, network or performance test was run. Existing packaged builds were not repackaged.

2026-10-27 repository cleanup: pre-edit package backups moved to `trash/bow-skills-retired-20261027/SourceAssets/MagicArrowRain20261026/VisibilityV4/Before/`. Current assets and this upgrade recipe remain active.
