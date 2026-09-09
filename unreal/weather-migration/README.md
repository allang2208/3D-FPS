# UE5 day/night and weather migration snapshot — 2026-09-09

This directory preserves the reproducible source, MCP configuration, validation
evidence, previews, and licensing notes from `D:/FPS3D/FPSGAME`. It is an
integration snapshot for the existing UE 5.8 `FPSGAME` module, not a standalone
Unreal project.

## Implemented contract

- Game time advances from Unreal's `DeltaSeconds`, so elapsed game time is
  independent of frame count. One complete game day is `2160` real seconds
  (36 minutes).
- `AFPSGAMEGameMode::BeginPlay` creates one `AFPSWeatherManager` when a map using
  that game mode has no existing manager. Scripted audit worlds can opt out.
- Deterministic schedule states are Clear, Cloudy, Light Rain, Rain, and Storm.
- Rain follows the local camera; splash emitters are ground-traced; an upward
  shelter trace reduces rain visuals and the three rain audio layers indoors.
- `MPC_FPS_Weather` receives wetness, cloudiness, and lightning values. Runtime
  puddle decals use traced outdoor surfaces.
- Storm lightning drives a flash value and delayed randomized thunder playback.

## Snapshot contents

- `Source/`: manager implementation, game-mode integration, and the module
  dependency snapshot used for the successful build.
- `Tools/ConfigureWeatherMcp.ps1`: reproducible Niagara and material-parameter
  configuration through the connected Unreal MCP server. It targets
  `127.0.0.1:8000` and uses the UE 5.8 fallback that saves all dirty content
  packages; run it only with unrelated editor packages already saved or in an
  isolated editor session.
- `Tools/ImportWeatherAudio.py`: imports the three existing Godot rain loops as
  looping Unreal sound waves. Its local source paths must be adapted on another
  machine.
- `ThirdPartyNotices/WEATHER_ASSETS.md`: provenance, license, and use notes.
- `Preview/`: morning and night/rain captures from the generated lighting map.
- `Reports/`: runtime/build evidence and the recoverable local cleanup manifest.

## Required local content

The source expects these project assets:

- `/Game/Weather/VFX/NS_FPS_Rain`
- `/Game/Weather/VFX/NS_FPS_RainSplashes`
- `/Game/Weather/Materials/MPC_FPS_Weather`
- `/Game/Weather/Audio/S_Rain_Light_Loop`
- `/Game/Weather/Audio/S_Rain_Soft_Loop`
- `/Game/Weather/Audio/S_Rain_Patter_Loop`
- `/Game/JVAD3D_SimpleWaterPuddles/.../MI_JVAD3D_SimpleWaterPuddles_A`
- three no-background thunder cues under `/Game/Thunder_Sounds/CUE`

The local project also contains the Fab Niagara Examples Pack, Free Thunder
Sounds, and Simple Water Puddles. Their binary assets are deliberately not
republished here; acquire them from Fab under their own terms. Generated Unreal
assets, maps, caches, build products, and editor settings are also excluded.

## Validation boundary

The native `FPSGAMEEditor Win64 Development` and `FPSGAME Win64 Development`
targets compiled successfully. MCP inspection confirmed Niagara, material,
puddle-decal, and thunder-cue types. Standalone runtime logs confirmed all
required weather assets loaded and the automatic schedule transitioned through
rain and storm. See `Reports/weather-validation.md`.

The automated runs do not replace a normal GPU PIE review of precipitation,
puddle placement, shelter transitions, or an audible mix review. A packaged
cook was not part of this checkpoint.

## Cleanup

Two superseded logs were moved locally to
`D:/FPS3D/FPSGAME/trash/weather-migration-20260909`. The manifest records their
original paths, sizes, and SHA-256 hashes. Final evidence, previews, editable
source, import tooling, licensing, and the map-organization recovery backup were
retained.
