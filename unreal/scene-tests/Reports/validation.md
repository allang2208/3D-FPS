# Validation boundary — 2026-09-09

Existing runtime evidence was reread during publication; it is not a new playthrough.

| Evidence | Result |
|---|---|
| landing-daynight-final.log:1627 | `SCENE_LANDING_PASS grounded=10/10` |
| landing-normandy-final.log:1724 | `SCENE_LANDING_PASS grounded=10/10` |
| trench-movement-final.log:1841 | `SCENE_MOVEMENT_PASS rise=1 fall=1 ground=1 moved=102.7 bad_support=0` |
| trench-movement-final.log:1821 | gravity `-1999.20`; support is not the fog cube |
| map-organization.json | Actor counts preserved across each map rename/reload |
| spawn-fix.json | Three starts persisted as always loaded |
| trench-blocker-fix.json | Exact fog actor repair saved and Pawn-ignore checked after reload |

The old landing-trench-final.log only checked standing, which also passed while
the fog cube supported the player. It is archived and is not current acceptance.
The first-failure trench-movement-blocker.log is retained locally for diagnosis.

Publication checks: Python syntax, PowerShell syntax, JSON parsing, installed and
published skill validation, source-copy SHA256 equivalence, archive SHA256 readback,
full staged diff and whitespace checks. No gameplay source was changed by cleanup.
No fresh native compilation, GPU playthrough, full route sweep, portal roundtrip,
packaging, or audio/visual acceptance is claimed by this publication. A shared
editor was open; publication did not stop it. Prior local native builds and the
runtime results above are separate from this turn's static publication checks.

Only an ignored-by-Godot UE integration snapshot and documentation skill are added.
WORKFLOW.md's Godot gameplay tests target the existing Godot runtime, not these
Unreal source files; they are not evidence of Unreal acceptance. That runtime and
the dirty main checkout were left untouched for this scoped publication.
