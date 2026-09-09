# UE 5.8 scene-test integration snapshot — 2026-09-09

Authored source and repair tools from `D:/FPS3D/FPSGAME`, not a standalone
playable project. The local project and its three saved maps remain unchanged
by this publication. Fab content, map binaries, caches and editor settings are
not redistributed. Acquire the source packs separately under their own terms.

## Local maps and prerequisites

| Game map | Required local source |
|---|---|
| `/Game/GameMaps/DayNight_Lighting` | Existing project DayNight map; see sibling weather-migration |
| `/Game/GameMaps/L_Normandy_FPS_Test` | Normandy Village, `/Game/UnrealNormandy/Levels/ML_Demonstration` |
| `/Game/GameMaps/L_MilitaryTrench_FPS_Test` | Military Trench, `/Game/MilitaryTrench/Tutorial/Scenes/Scene_Trench_Tutorial` |

The source packs and their overview/component maps remain local. Normandy's
test copy still shares original sublevels. Duplicate sublevels/assemblies before
editing layouts, and create new material instances instead of changing originals.
Keep map redirectors and recovery backups; do not move Unreal assets in Explorer.

## Integrating the source

Copy the four `SceneTestPortal` / `SceneSpawnValidation` files into the existing
FPSGAME module. The included GameMode pair adds RestartPlayer and
SpawnAfterStreaming to the weather-migration GameMode; merge those additions
into a newer project rather than overwriting unrelated GameMode work. Existing
Character, PlayerController and WeatherManager classes are prerequisites. The
snapshot uses the existing Core, CoreUObject, Engine and InputCore dependencies;
no complete module/project configuration is published here.

Merge only these keys into `Config/DefaultEngine.ini`:

```ini
[/Script/EngineSettings.GameMapsSettings]
EditorStartupMap=/Game/GameMaps/DayNight_Lighting
GameDefaultMap=/Game/GameMaps/DayNight_Lighting
```

Use the pack-required PCG plugins for the trench content. Existing project setup
uses PCG, PCGExternalDataInterop and PCGGeometryScriptInterop. Enable Python editor
scripting before running the tools. Build FPSGAMEEditor before Python calls to
SceneSpawnValidation. Do not overwrite unrelated renderer/plugin configuration.

For a fresh local integration, duplicate the Normandy source map through Unreal
to the target path, select exactly one PlayerStart near the intended playable
area, and set FPSGAMEGameMode. The retired provisional Normandy builder is not
provided as an active tool because rerunning it created duplicate starts.
`build_trench.py` creates only a missing trench test map and refuses overwrite.
`organize_maps.py` is a one-time old-path migration, not a tool to run against
already organized maps. Its old sources must exist and new targets must not.

Before repairs, close/coordinate interactive editors, back up maps and their
external actor/object packages, and create `Saved/SceneTests`. Run
`fix_scene_spawns.py`, then `fix_trench_blocker.py`, in a full editor process with
`-ExecutePythonScript=<absolute script path> -nullrhi -unattended -nosound`.
Supply the local project path and unique `-abslog` path. The blocker script
targets an exact actor ID from this pack version and intentionally fails if it
cannot find it: inspect a changed pack, never broaden the filter automatically.
Inspect explicit completion markers and reload reports, not just exit codes.

The repairs preserve the intended DayNight floor's top/extent/material, use a
40cm solid surface, make starts always loaded, internalize the non-WP trench
test map's owned objects, and ignore Pawn collision on its fog cube. Source-pack
maps are not modified. Native spawning rechecks capsule clearance after streaming;
the trench delay and blocking flush are prototype measures, not a production
streaming architecture.

## Playing and acceptance

`Tools/Open-SceneTest.ps1` launches Normandy or MilitaryTrench in a visible game
window; adapt its local engine/project paths on another machine. The three
supported maps install two test portals near the spawned character. Approach
within 2m and press E with menus closed. Travel recreates the map and pawn; this
is single-player test travel, not cross-map save persistence or multiplayer.

Run a local standalone game with `-SceneSpawnAudit` for landing checks, or
`-SceneSpawnAudit -SceneMovementAudit` for the scripted jump/move test. Audit
mode exits the process automatically. See Reports/validation.md for measured
results and remaining manual acceptance. Packaged builds must explicitly cook
these dynamically referenced maps; packaging was not validated here.

## Cleanup and scope

92 obsolete task files (14,713,828 bytes) were moved to local
`trash/scene-tests-20260909`. Reports/cleanup-manifest.json records original and
archive paths, SHA256, size and reason. Restore only to absent original paths,
then verify hashes. No permanent deletion or third-party content cleanup occurred.
Useful repair/migration tools, source assets, final/first-failure evidence and
three recovery backups remain local. Raw historical logs and retired scripts
are not published. Other dirty Godot, UI, weapon and weather work is not included.

The updated ue5-debug-validation skill and its focused scene reference live
under repository `skills/ue5-debug-validation`, matching the installed local skill.
