---
name: ue5-weather-workflow
description: Build or migrate UE5.6-UE5.8 day-night and weather systems using frame-rate-independent time, Niagara rain, wetness parameters, shelter attenuation, puddles, lightning, thunder, and evidence-based validation.
---

# UE5 weather workflow

Use this skill for the current Unreal migration when work touches the game clock,
sky/light transitions, rain, wetness, puddles, lightning, thunder, or weather
asset integration. Use the legacy Godot weather skill only when maintaining the
old Godot implementation.

## Project contract

- Advance world time with engine elapsed time (`DeltaSeconds`), never frame
  counts. For this project, one game day is `2160.0` real seconds (36 minutes).
- Keep one authoritative runtime weather manager. Spawn it from the active game
  mode only when no manager already exists, so authored map overrides remain
  possible and map travel does not create duplicates.
- Keep tuning Blueprint-visible, but retain runtime ownership and state changes
  in the manager. Treat multiplayer replication as a separate requirement; the
  current implementation is single-player.

## Effects integration

For cloud/solar conflicts, coarse rain particles, pooled wet surfaces or transition
acceptance, read [storm and rain integration](references/storm-rain-integration.md).

- Attach camera-local rain to the player view instead of filling the world with
  emitters. Ground-trace splash placement and cap spawn rates for scalability.
- Detect shelter with a periodic upward visibility trace. Smooth attenuation
  using `DeltaSeconds`; apply it consistently to rain particles and layered rain
  audio.
- Publish wetness, cloudiness, and lightning through one material parameter
  collection. Materials must consume those parameters before claiming a wetness
  system is visually integrated.
- Use deferred decals for puddles only on validated outdoor surfaces. Refresh
  them at a coarse interval and reuse existing decals instead of spawning every
  tick.
- Separate lightning flash timing from thunder playback delay. Randomize among
  licensed no-background thunder cues so rain ambience is not doubled.

## Asset and licensing boundary

- Prefer MCP asset queries for class, parameter, dependency, and save checks.
  Do not require foreground editor clicks for checks that MCP can perform.
- Before running an MCP script whose save fallback writes every dirty package,
  ensure unrelated packages are already saved or use an isolated editor session.
- Keep import/configuration scripts, source audio provenance, license notices,
  and asset paths. Do not publish Fab binary assets unless redistribution rights
  are explicitly established.
- The reference snapshot and exact asset paths are in
  `../../unreal/weather-migration/README.md`.

## Validation gate

1. Compile both the editor module and the game target after the final source
   change. A stale DLL or a successful single-file compile is insufficient.
2. Query Niagara systems, the weather MPC, rain sounds, puddle material domain,
   and thunder cues through MCP; confirm assets save and reload.
3. Run a normal-duration standalone check for the `2160s` contract and an
   accelerated schedule check that reaches rain and storm.
4. Search logs for the manager-ready asset counts, state transitions, fatal
   errors, ensures, Niagara errors, and linker errors.
5. Report visual PIE review, audible mix review, and packaged cook separately;
   headless or `-nullrhi -nosound` runs do not prove those outcomes.

## Repository publication

Archive only confirmed superseded files to `trash` with original path, size, and
SHA-256. Preserve final previews, reproducible scripts, source assets, and
licenses. Publish a source/evidence snapshot from an isolated worktree and use
an ordinary non-force push after staged diff and remote ancestry checks.
