# M24 fire bolt-cycle motion reuse

The user's requested receiver movement is copied at its original amplitude
from the current `A_M24_fire` presentation, source frames 10–50 (30 Hz).
Frames 0–9 contain the firing kick and are excluded.

The actual saved bolt-handle transforms establish constant offsets: equip is
fire +3 frames; empty reload is fire +55 frames. Target motion windows are
therefore frames 13–53 and 65–105 respectively. No mechanical keys, clip
durations, audio cues, magazine motion or gameplay timing are changed.

The gun and complete existing arm chains receive the same rigid motion, leaving
local elbow, wrist, twist and finger channels intact. This includes the separate
skeleton-stock pistol-grip poses. Existing scales and tracks outside the two
windows are retained. Four production profiles are updated: base, mag10,
skeleton_base and skeleton_mag10.

Authoring inputs: `before.json.gz`, `motion_sources.json`.
Reproduction: `author.py`, `install.py`, `run_assets.ps1`.
Before-assets are retained under `Before`; exact saved asset paths are recorded
in `install_receipt.json`. No C++ or model changes are required.

No gameplay, rendering or acceptance tests were run; visual acceptance is left
to the user.
