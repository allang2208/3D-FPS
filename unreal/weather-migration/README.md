# UE5 weather integration snapshot — 2026-09-10

Subsequent development targets UE5. The active local project is
`D:/FPS3D/FPSGAME/FPSGAME.uproject` (UE 5.8.2).
This directory updates the weather source/evidence snapshot. It is **not a
standalone Unreal project**, and does not include the complete host game or
licensed binary assets.

## Current behavior

- The existing sky Blueprint owns the main map clock; native scene lighting
  handles Normandy and MilitaryTrench. The normal day remains 2160 seconds.
- Fine camera-local rain, mist, world-fixed wet surfaces, surface splashes,
  eaves drips and step ripples use fixed pools and quality caps.
- Storm clouds smoothly cover/darken the sky and suppress the sun disk. The
  main map's baked sunny sky fades out. Existing cloud layers are reused;
  Normandy creates one reusable fallback. Clear weather restores original
  materials, visibility, layer properties and clock-derived light values.
- Only the three supported gameplay maps use cloud overrides. No new
  directional light is created, and weapon-preview maps are excluded.
- Layered rain audio, shelter attenuation, lightning and delayed thunder remain.

See [rain implementation](Reports/RAIN_UPGRADE_20260910.md),
[storm implementation](Reports/STORM_CLOUDS_20260910.md) and
[lighting audit](Reports/LIGHTING_CONFLICT_AUDIT_20260910.md).

## Integration and prerequisites

Copy current weather files from `Source/` into the host `Source/FPSGAME/`,
and the weather UI files into its `UI/` directory. Merge module dependencies
instead of replacing the host Build.cs. The unchanged GameMode files here are
the **2026-09-09 historical spawn integration**, not the latest game mode;
preserve current portals, UI, weapons and other host changes.

Runtime dependencies include Engine, Niagara, UMG/Slate and the existing host
game classes/UI style. The diagnostic harness also uses RenderCore/RHI.
The editor-only rain authoring bridge requires NiagaraEditor; the Python
authoring tools use the UE 5.8 NiagaraToolset_System / NiagaraExt APIs and
therefore need those editor capabilities enabled.

The local project must already contain these Niagara graphs and user bindings:

- `/Game/Weather/VFX/NS_FPS_RainFine`
- `/Game/Weather/VFX/NS_FPS_SurfaceSplashes`
- `/Game/Weather/VFX/NS_FPS_RainMist`
- `/Game/Weather/VFX/NS_FPS_RoofDrips`

`Tools/Weather/build_rain_assets.py` **reconfigures these existing graphs** and
creates the procedural rain/wet-surface materials. It does not reconstruct all
Niagara emitter graphs from an empty project. Binary graphs are retained in the
local project and are not included in this public source snapshot.

Other prerequisites are `MPC_FPS_Weather`, the three `/Game/Weather/Audio`
rain loops, the no-background thunder cues under `/Game/Thunder_Sounds/CUE`,
the main day/night Blueprint, the three gameplay maps and their licensed
content. Storm clouds reuse the engine SimpleVolumetricCloud material or the
map's existing compatible instance. No new cloud textures are downloaded.
See [asset notices](ThirdPartyNotices/WEATHER_ASSETS.md).

Install `Tools/` under the host project root. `ConfigureWeatherMcp.ps1` now
launches the isolated rain authoring commandlet; it no longer rebuilds the old
blue-card/Fountain rain. Adapt engine paths on another machine.

## Verified outcomes and limits

- Local FPSGAMEEditor and FPSGAME Development builds passed.
- Rain upgrade: 7/7 runs passed (three renders, three weather-panel checks and
  the surface/roof/quality contract run).
- Storm clouds: 10 checks on each of three maps, 30/30 passed. Two storm/clear
  cycles verify recovery and unique cloud/light ownership. Actual rendered
  images are in `Preview/`; concise checks are in `Reports/`.
- GPU samples were contaminated by concurrent workloads and startup stalls.
  They do not establish net cloud cost or an FPS guarantee. Packaged cook,
  multiplayer and audible mix acceptance are not claimed.
- These results were obtained in the complete local host project, not by
  launching this incomplete source snapshot alone.

`Tools/Weather/run_storm_validation.ps1` reproduces the storm checks in the
host. `run_rain_validation.ps1` also requires the host weather-panel/UI wiring.

## Recoverable retirement

The old two rain Niagara packages, pre-upgrade backups, the retired inspection
script and superseded debug outputs were moved locally into
`trash/weather-upgrade-20260910` (76 files, original paths and SHA-256 recorded).
Trash, caches, build products and licensed binary content are not published.
The current retirement script moves exact legacy packages to trash, checks
their archived backup hashes and leaves locked editors alone.

Earlier 2026-09-09 reports/previews remain historical evidence; current status
is this README and the 2026-09-10 reports.
