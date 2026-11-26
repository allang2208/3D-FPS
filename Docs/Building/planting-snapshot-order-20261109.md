# Planting snapshot ordering repair (2026-11-09)

## Failure and contract

World-stream chunks and owner inventory replies both carry `FColdSteelPlantingNetState`. They can complete in a different order from capture. A failed shared inventory save sets `bSaveBlocked` without committing crops, so `PlantingRevision` alone cannot order these snapshots. The former consumer accepted every equal-revision payload and could reopen the planting preview after receiving an older unlocked view.

The public runtime snapshot now includes `SnapshotSequence`. `UColdSteelPlantingSystem::NetworkState` increments one authority publication counter for the current UWorld. The consumer first rejects lower crop revisions, then rejects older or duplicate sequences at an equal revision. A newer same-revision snapshot can therefore both lock on failure and unlock on recovery; the flag is not permanently latched.

The counter is runtime-only and is not added to the world/profile save schema. A different world resets the publisher counter. Disconnect/context reset clears the client mirror, allowing a restarted authority's sequence. Existing crop records, inventory receipts, and save-journal recovery remain authoritative and unchanged.

## Isolated regression

After the final Editor build, run:

`Tools/Crops/run_planting_network_audit.ps1 -RunAuthorizedRegression`

The launcher uses a unique directory under `SourceAssets/PlantingMultiplayer20261022/TestRuns/`, a dedicated UserDir, and a unique audit profile. The commandlet refuses any root outside that subtree or a Saved directory outside the requested run. The launcher compares production `Saved/SaveGames` file lists, sizes, and SHA-256 before and after.

Cases exercise production snapshot serialization/consumption, planting request preparation, shared inventory commit, and journal reload:

- Save failure at unchanged crop revision, with unchanged inventory and crop state.
- Two independent client mirrors receive lock, delayed old unlocked state, recovery, and delayed failure state.
- Duplicate snapshots do not dirty client UI state.
- Correct preparation and commit charge one input and create one crop.
- Competing empty-slot/harvest intents are serialized against current authority state and cannot duplicate the result.
- Stale bed and plant identities fail validation.
- Mature harvest gives the configured yield once, and disk reload does not resurrect the crop.
- Older crop revision is rejected even if its sequence is larger.
- Fresh/reconnected mirror accepts current state and a reset authority sequence.
- Invalid world and authority-side mirror adoption are rejected.

This commandlet intentionally exercises network branches without sockets. It is not evidence of UDP transport, multiple authenticated accounts, complete PlayerState RPC upload/acknowledgement, rendered UI, actual keyboard/mouse interaction, dedicated-server play, cross-machine behavior, or a packaged build. The separately coordinated UDP fixture must be reported on its own evidence.

## Verification status

- PowerShell helper: parsed without errors.
- Source whitespace check: passed for tracked touched files.
- First coordinated Editor build: planting sources compiled successfully; full link blocked by compilation errors in the separately added enhancement UDP fixture. Isolated runtime regression awaits a successful final build.
- No commit or push was requested or performed.