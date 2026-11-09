# M249 reload receiver feedback — 2026-11-09

Saved five grip profiles for the 30/45-round side-magazine normal and empty reloads. The existing action is preserved: all non-root tracks, clip lengths, magazine/charging travel, arm corrections, sound/contact timing and RC1 camera feedback remain unchanged. Only a `root` pose track was added to each side-reload profile row. No C++ change or build was required.

## Diagnosis and reference

Fresh compressed asset samples and the runtime graph confirmed that the receiver stays still throughout source 1.05–2.40 s, despite hand movement. The small prior contact impulses did not provide continuous load transfer. The full-clip 5.49° range mostly describes entering/leaving the prepared pose, not motion during handling.

Read the current M4/PKM receiver tracks and their production sources. M4's slap reaction applies a rigid transform to the whole assembly; PKM Charge34 separates work/box/cover/charging load and short settling reactions. The skill's RC1 rule retains one camera impulse owner. Super90 R13 was explicitly rejected historically and was not used as a production template.

M249 box reloads already retain PKM-style assembly motion (approximately 16.2° over the clip); those rows are unchanged. This revision addresses the static side-magazine branch.

## Implementation

- `author.py`: smooth receiver-space load and settle curves for release, extraction, retrieval, docking/seating, recovery and empty-only pull/forward stop. Maximum added angular magnitude about 2.14°, translation at the rear-grip pivot about 0.73 cm.
- The shared visual `root` is an ancestor of both arms and `WPN_root`. Bake its local delta through the actual parent matrix, including this imported rig's 100x scale. Thus the gun, both arms, magazine and mechanical children receive the same rigid motion without solving or moving a hand independently.
- Added feedback is zero through source 0.18 s and from 3.50 s (normal) / 4.70 s (empty), before the existing idle handoff. No random shake, extra camera track, Tick or replicated state was added.
- `install.py` preserves every other local track and action row, including Insert30, verifies the input hashes and dirty package state, and stores originals in `Before.zip`.

## Saved evidence

- `install_receipt.json`: five saved asset hashes. `saved_verification.json`: serialized root data matches the generated data; all prior joint tracks, base clips and other actions are unchanged.
- `saved/receipt.json`: 12 native offline animation-graph cases. `runtime_verification.json`: identical playback clocks; hands, elbows, magazine and charging-handle transforms relative to the gun remain equal within floating-point precision (maximum sampled position difference below 0.000007 cm).
- Previously static handling interval now moves about 0.44–0.46 cm and 1.94–2.04° in the receiver track. These are interval measurements, separate from the maximum added pivot curve.
- `saved/` contains actual engine frames/poses. `native_preview/` and `views/` are the earlier rigid-layer previews using the matching Insert30 evaluated mesh, not a separate animation baseline.

The existing editor closed before saving, so the assets were saved and checked through background commandlets. No editor GUI or gameplay session was started. In-game feel remains for user review.

For subsequent edits, collect fresh snapshots; `current.pkl` here intentionally holds the pre-Feedback31 baseline. Do not replay an older full-profile importer over these saved profiles.

## Archive update — 2026-11-10

Superseded trial captures/previews were moved to `trash/M24920261109/SourceAssets/M249Orpind20261107/Feedback31/`. See `Docs/Publication/M24920261109/archive-summary.json` and the local trash manifest for exact paths and verified hashes. Active authoring dependencies and saved evidence remain in this directory; historical preview scripts are not a current installation route.
