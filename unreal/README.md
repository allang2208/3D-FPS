# UE5 development

As of 2026-09-10, subsequent 3D FPS development targets **Unreal Engine 5**.
The current local project is `D:/FPS3D/FPSGAME/FPSGAME.uproject` (UE 5.8.2).
The repository root retains the Godot prototype and its history as a migration
reference; it is not the current UE project root.

This directory publishes selected source/evidence integration snapshots:

- [Weather, rain and storm clouds](weather-migration/README.md)
- [Imported scene and spawn integration](scene-tests/README.md)
- [Historical AKM migration](akm-migration/README.md)
- [M4 arms, reload and MAT workflow](m4-arms/README.md)

These snapshots do not contain a complete, independently runnable UE project.
They require the local FPSGAME host module and documented licensed assets.
Acquire engine/Fab content under its own terms; do not reconstruct the current
game by overwriting it with historical GameMode or weapon snapshots.

Use the relevant UE5 skill for new work. Preserve Godot timing, animation,
inventory and gameplay contracts when migrating them, and validate the actual
UE runtime. Repository publication continues to follow WORKFLOW section 8:
scoped files, recoverable trash, isolated publication when histories are mixed,
ordinary pushes and remote SHA verification.
