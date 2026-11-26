# Village planting and segmented defenses — 2026-11-17

Requested scope: compare the previous southwest overview camera; naturalize the marked village planting, remove the duplicate chapel-side wall, add chapel garden planting, raise repaired perimeter masonry by 25%, install wooden gates at both exits, and support monster damage, collapse and temporary physical fragments.

Delivered 2026-11-18: saved models/level, Editor and Game builds, 17 passing standalone gameplay checks, and four passing final gate follow-up checks. Final gate-open and gate-closed frames were visually inspected for both exits after the mirror-geometry repair; the long spike faces are gone. Separate-peer multiplayer and a full autonomous night wave were not run.

## Scene and assets

- The camera is the existing construction review's southwest camera: village local eye `(-PadHalfX-1500,-PadHalfY-1400,terrain+2100)`, target `(-PadHalfX+2500,-PadHalfY+2500,terrain+100)`, FOV 60.
- `TemperateVillagePlanting.cpp` owns seed-local planting patches and exclusion masks. Real mesh bounds, roads, building/service footprints, chapel masonry, grave paths, headstones, wall corridors and inward gate swing areas are reserved.
- The accepted hazel palette is `UTemperateHillsAssets::Shrubs` (static meshes), not the optional skeletal `ForestShrubs` array. The dedicated village display emits only its `0x6...` candidate IDs, using the common terrain-support/neighbor filters. Native PCG omits those IDs so nothing is rendered twice. Farther culling is limited to this small village palette.
- The source layout and saved village level remove exactly 20 captured street-wall instances parallel to the chapel north courtyard wall. The chapel's own courtyard wall and outer perimeter remain.
- Repaired masonry and piers use Z scale 1.25. The west/east openings retain their original widths, 1000/800 cm.
- Gates have 428/328 cm leaves, 215 cm height, a 6 cm center gap, inset hinges, bevelled planks, timber bracing, iron straps, fasteners and handles. Independent mirrored right leaves keep both exterior faces consistent. Fixed iron hinge mounts attach the leaves to the stone piers. Gates swing inward through 88 degrees and stop at blocking geometry or pawns.
- Assets: `/Game/WorldGeneration/TemperateHills/VillageDefenses`. Source geometry, saved-asset receipts and the original removal list: `SourceAssets/VillageDefenses20261117`. The directory is explicitly included in cooking.

## Gameplay

| Part | Health |
| --- | ---: |
| Repaired masonry bay | 1200 |
| Repaired pier | 1600 |
| Double wooden gate | 900 |
| Ruined masonry bay | 350 |
| Ruined pier | 500 |

`AVillageDefenseSection` owns authoritative damage and replicated health. Station identities are deterministic within a world; ruined and repaired states use different ID ranges. Per-world `VillageDefenses_<WorldId>` saves preserve partial damage and destroyed bays. Repair unlocks replace the initial ruined perimeter with fresh repaired defenses, while subsequent world reconstruction restores saved damage.

The native E-key interaction uses the existing player-owned `FPSDoorPushComponent` server validation, including reach and visibility. Gate repair checks occupancy before spawning closed leaves. Monster contact uses the near collision surface; blocked night-raid routing can select reachable wall/gate approach points instead of refusing all spawns when the village is closed. Defense pawns are excluded from ordinary monster perception targets; explicit breach targeting still handles them.

Destroyed bays immediately lose gameplay collision and navigation obstruction. A reliable server event starts a seeded, top-down fragment release. Local fragments collide with world geometry, ignore pawns, shrink during seconds 10–12 and expire at 12 seconds. At most eight fragment groups / 128 bodies remain active. Physical fragments are cosmetic; health and the resulting breach are authoritative.

## Evidence and iteration

- `Saved/VillageConstructionReview20261117/planting_baseline`: actual initial comparison frame; the pre-change construction/UI review passed 22 checks. This receipt is not a validation of the new defense code.
- `Saved/VillageDefenses20261117/Build01`: Editor and Game builds succeeded.
- `Saved/VillageDefenseReview20261117/first`: real rendered first iteration. Repair, segment count, 25% height and both gate swings passed. Actual contact-damage checks failed; later destruction checks therefore failed too. This run must not be described as a pass.
- Follow-up source fixes correct contact-time obstacle targeting, isolate the animation fixture from its autonomous AI, use the actual hazel palette, reshape the planted patches, mirror right gate leaves, and add fixed hinge mounts.
- `Saved/VillageDefenses20261117/Build02`: Editor and Game builds succeeded; all nine defense mesh assets are saved, including the mirrored leaves and fixed hinge mounts.
- `Saved/VillageDefenseReview20261117/second`: 15 of 17 checks passed. Real NurseZombie animation contact dealt 22 damage (1200 to 1178), then destroyed a weakened bay; partial and destroyed health were read back from disk, and physical bodies were present. Both ground samples measured 12 cm clearance. East-gate completion and fragment expiry were inspected too early by wall-clock waits during severe loading stalls. This receipt remains failed.
- The rendered planting display completed with 5596 instances across 32 mesh groups. The first overview in this run preceded its completion; it is not the final visual comparison.
- Follow-up review timing now uses game time for moving gates/physics, waits for the planting actor and at least 300 overview frames, and keeps state changes out of the frame requested for screenshots. The final breach screenshot is captured before level teardown. The next run also requires moving physical fragments, not just physics-enabled components.
- `Saved/VillageDefenseReview20261117/third`: all 17 functional checks passed. Both gates reached 88 degrees. At the collapse sample, all 16 stone bodies simulated physics and 15 were moving; the later sample contained no debris actors and showed a clear breach. Partial and destroyed health were saved. Final same-camera overview, chapel-side and yard images are in its `Evidence` folder.
- The gate-open frames showed thin spike faces. `gate_shadow` ruled out shadow-cache invalidation as the fix. Inspection of the actual source geometry found the cause: `Mesh.solid` shares point lists across triangle corners, and `deepcopy` retains this aliasing. In-place X reflection therefore flipped shared ring and cap points repeatedly, leaving some corners on the original side. The wide right leaf incorrectly spanned X=-427.675 to +421 cm in the timber group.
- Mirroring now creates an independent reflected value for each corner, normal and triangle. The corrected wide right timber spans -427.675 to -0.325 cm; the iron group spans -423 to +1 cm, matching its hinge barrel. Bounds symmetry and nonzero triangle area passed for both leaf sizes and the hinge mount (`mirror-geometry-check.json`). Normal Nanite rendering and automatic shadow invalidation are retained.
- The shortened `gate_shadow` fixture did not reproduce the full review's E-key action (west angle stayed at zero); it is a failed receipt. The final gate-only visual follow-up uses direct gate toggles; the full native-E result is recorded in `third`.
- `Saved/VillageDefenses20261117/Build07`: final Editor and Game builds succeeded. The corrected nine mesh assets were saved at 2026-11-18 00:00 (see `import-process.json` and `asset-production.json`). The local vegetation actor now destroys itself if its source hills actor is destroyed, so an in-level world replacement cannot leave a second vegetation set behind.
- `Saved/VillageDefenseReview20261117/gate_final`: four checks passed; west opened to 88 degrees and closed, east opened to 88 degrees. Both closed/open frames were inspected and show complete rigid timber/iron geometry without the earlier spike fans. This run uses the normal Nanite and shadow settings.
- Multiplayer behavior is implemented but has not been exercised with separate peers by this review.

Review entry: `fps.Test.VillageDefenseReview` with `-VillageDefenseReview -VillageDefenseOut=<isolated directory>`. The launcher `Tools/WorldGeneration/run_village_defense_review.ps1` uses an isolated host, player profile and save directory and never overwrites the player's active world save.
