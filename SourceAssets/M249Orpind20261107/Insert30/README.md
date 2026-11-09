# M249 side-magazine insertion arm correction — 2026-11-09

Delivered: five saved grip profiles, covering the shared 30/45-round normal and empty reload clips. Only the left upper arm, elbow/forearm helper chain and the compensating wrist-local transforms changed. No C++ build was needed.

The inserted-magazine pose placed the elbow high and behind the camera. This enlarged the near forearm at the bottom of the view. The early recovery also blended the main upper-arm roll against a different helper-bone solve. The correction lowers the elbow on its existing shoulder-to-wrist IK circle, preserves bone lengths, and transports the seated/recovered arm frames through the existing recovery interval. Upper-arm rotation and V9 forearm half/full twist stations are solved together.

Hand/finger component poses, right arm, weapon, magazine path, camera effects, ADS/idle, and source/gameplay clocks remain preserved. The correction begins smoothly at source 1.80 s, reaches the insertion posture at 2.35 s, releases after 2.76 s and rejoins the existing recovered pose at 3.14 s (empty) or 3.50 s (normal). The elbow return follows the existing playback clock; reload duration is unchanged.

## Saved result and evidence

- `install_receipt.json`: hashes for the five saved assets; `Before.zip` is their original backup.
- `saved/receipt.json`: 12 offline engine cases, 30-round factory and 45-round factory/vertical/canted/prism/angled, normal and empty.
- `saved_comparison.json`: identical playback clocks; wrist position difference at most 0.00855 cm (0.0855 mm). All protected component positions differ by at most 0.01105 cm, chiefly between the two magazine playback clocks.
- At insertion, the nearest visible left-arm surface is approximately 13.2 cm from the camera's forward plane, previously 9.6 cm. No sampled insertion arm vertices remain in the first 10 cm of the visible frustum.
- The original factory normal reload's upper-arm peak rotation around insertion/release decreases from 10.68 to 5.99 degrees per 60 Hz frame; factory empty decreases from 10.54 to 9.69. These are scoped measurements, not a claim that every bone's peak decreases in every grip variant.
- Actual evaluated, morphed UE surfaces were inspected in `native_views/*_saved_*.png`; first-person engine frames and pose streams are in `saved/`.

The editor GUI and gameplay were not started. This is a saved asset correction with offline animation-graph and geometry review; in-game feel remains for user review.

## Reproduction

Current shipped authoring: `candidate.py` defines the arm solve; `publish_native.py` converts actual **before** engine poses into local profile corrections; `install.py` publishes them with original-input/hash protection. The native pose stream omits component scale: this skeleton uses a 100x import scale, recovered from the reference binding before deriving local translations. Retain that conversion.

`publish.py` and `candidate_views/` are intermediate compressed-grid diagnostics. `after/` and `final/` are superseded trial captures, not the delivered result. The delivered capture is **`saved/`**. Do not use historical installation scripts or these trial captures as a fresh production baseline.

For a future change, collect fresh assets and hashes into a new revision folder. `current.pkl` and `inputs.json` here intentionally retain this correction's pre-edit baseline. Preserve other actions and retained clips when replacing the two side-reload rows in each profile.

## Archive update — 2026-11-10

Superseded trial captures/previews were moved to `trash/M24920261109/SourceAssets/M249Orpind20261107/Insert30/`. See `Docs/Publication/M24920261109/archive-summary.json` and the local trash manifest for exact paths and verified hashes. Active authoring dependencies and saved evidence remain in this directory; historical preview scripts are not a current installation route.
