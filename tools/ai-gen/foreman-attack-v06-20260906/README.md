# Foreman V06: attack and grip

Input: V05 editable source with its shoulder/elbow weight correction. Build:
`blender -b --python build_motion.py`. Helpers prepare_grip.py and
finish_howl.py are executed by this builder; no external generation service.

Reference: the existing original attack contact sheet, 39 variable source
frames / 1.5 seconds, right-handed overhead windup, left arm balances then
withdraws, left forward step, chest-driven downward snap and low contact.
Zero-based source frame 21 starts at 0.59625 s; the business clock and sound
event at 0.45 s are preserved. The depth and obscured hand posture are manual
3D reconstruction, not motion capture. V05's complete 36-frame GIF was
reviewed before this iteration: insufficient windup, open grip, stiff left
wrist, and a mechanical uniformly closing rope were the actionable findings.

The original palm lies around (-.805,-.13,1.18) in Blender coordinates;
the previous wrist-line anchor missed it in depth. The handle and rope now
share a palm-local anchor transformed by the actual hand bone. A rigid leather
grip adds a visible hold surface. Finger root pivots are aligned to the mesh,
with a second collective finger segment and an independently weighted thumb
on each hand. Four fingers still share their bend controls; this is not a
complete individual-finger skeleton. Local weight relaxation is constrained
to mesh neighbours and pruned to four influences.

Attack increases overhead reach, torso counter-rotation, forward loading and
left support step. The left wrist follows the forearm and withdraws during
the snap. Recovery propagates from grip toward tip with a damped wave; a cubic
transition smooths the first six whip sections. This is authored secondary
motion, not a physically simulated rope. Its 33 unit-scale sibling section
bones are retained. Idle/Walk/Death body motion uses the previous builder;
their grip/accessory poses are updated for consistency. Howl body keys are
preserved while its grip is retargeted.

Review tooling: render_keys.py gives bright Blender key poses and hand
closeups. render_motion.gd uses the project default renderer; --review-light
adds inspection lights in the preview only, writing runtime-lit separately
from the default scene lighting in runtime. Neither changes game lighting.

Validation on the final candidate:
- Export/reimport samples: all five durations retained; 1349 whip skin samples,
  maximum distance from right hand 2.962 m; no non-unit whip scale.
- Imported Idle and Walk loop-pose errors are zero. Walk stance speed error
  is 0.000484 m/s in offline reimport and 0.017111 m/s in the engine.
- Engine motion: 8 checks pass, max body joint step 0.39579 rad at 60 Hz;
  grounded movement 0.96417 m. Engine skin minimum Y for Idle/Attack/Death:
  0.005000 / 0.004970 / 0.005000 m.
- The 36 inspection-render attack frames were reviewed in sequence. The
  overhead grip, forward load and recovering left arm are more legible than
  V05. The close-up fingers remain angular due to the coarse source mesh;
  automatic checks are not a substitute for the user's visual acceptance.
- Formal scene now references assets/models/foreman_zombie/foreman_v06.glb.
  Attack gameplay clock, hit window and other controller code are unchanged.
- Formal model: 24 behavior and 8 motion checks passed; 180-frame main smoke
  completed without script errors. Motion-test teardown still reports two
  ObjectDB instances and one resource in use. Default-light and inspection-
  light attack renders completed; both GIFs decode to 36 frames / 1500 ms.
- Repository index.lock remains occupied. Changes are present locally but
  were not committed or pushed; no lock or unrelated edits were removed.
