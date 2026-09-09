# Imported scenes: migration and spawn validation

## Source and package boundaries

- Work on a test map copy. A copied persistent map can still share original sublevels and LevelInstance assemblies; copy them separately before changing their layout. Use new material instances for edits.
- Before relocating maps, back up maps, matching external actor/object packages and affected editor settings. Use Unreal asset rename APIs, not filesystem moves. Update default maps, travel paths and saved editor viewport/map references; stale editor references can trigger modal dialogs in unattended renames.
- Save/reload destinations and check actor counts, PlayerStart, GameMode and dependencies. Redirectors are not abandoned duplicate maps.
- When internalizing a non-World-Partition test map, account for private generated objects such as Landscape Nanite meshes in external actor packages. Verify ownership and reload, not just successful actor conversion. Do not indiscriminately convert World Partition or source maps.

## Diagnose the supporting object

- Capture possessed pawn class, movement mode, gravity, capsule dimensions, support actor/component/mesh/material, simple collision hit, and complex surface height relative to capsule feet.
- `IsMovingOnGround()` can pass on an invisible fog cube or oversized simplified collision. Zero vertical speed while grounded does not prove gravity is disabled.
- `NO PLAYERSTART with positive rating` does not prove missing starts. Enumerate them and check obstruction and streaming state.
- Repair only the confirmed offending collision component. Preserve geometry, visuals and unrelated channel responses. Mark actor/component modified, use Custom profile for channel overrides, then verify after saving and reloading.
- Do not mask missing collision with an extra giant floor. Repair the intended surface while preserving its top elevation, extent and material.

## Spawn and evidence

- Test the actual pawn collision channel and capsule clearance, slope and penetration. Missing safe ground should not silently fall back to world origin.
- Recheck after required streamed assemblies load. A fixed delay is only a test-specific workaround, not general readiness; verify slower loads and avoid blocking streaming flushes in production. Keep starts loaded where needed and helpers scoped to test maps.
- Compile and syntax checks establish code validity, not world behavior. Save/reload reports establish persistence, not playability.
- Editor Python physics queries need an initialized world. Prefer a full editor session with `-ExecutePythonScript=...`; `-run=pythonscript` commandlets may lack physics initialization. An empty trace there is not proof of absent collision.
- Runtime acceptance must check jump rise, fall, landing, horizontal movement, negative gravity and support identity. Check explicit PASS/FAIL markers as well as exit status. Preserve first-failure and final evidence separately.
- NullRHI tests do not verify rendered appearance, input usability, all routes or portal round trips. State those remaining checks explicitly.
- Coordinate shared editor/build processes; do not terminate another task's editor to release a DLL lock.

## Cleanup and publication

- Archive only task-owned abandoned outputs/scripts under trash, with original paths, reasons, byte sizes and SHA256. Retain source assets, rollback backups, reproducible repair tools, final evidence and licenses. Do not leave an unsafe provisional builder as the active entry point.
- Verify target repository and its integration-snapshot layout when UE lives outside Git. Isolate publication from unrelated dirty changes; stage exact paths, review full staged diff and outgoing commits, push without force and read back remote SHA.
- Publish authored source, instructions and compact evidence. Keep third-party binaries and maps embedding them local unless redistribution is explicitly cleared. A source snapshot without assets is not a standalone playable project.
