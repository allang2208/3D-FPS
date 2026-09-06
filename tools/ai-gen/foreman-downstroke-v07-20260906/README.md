# Foreman V07: downward lash and doubled whip

User accepted the V06 overall direction, requested a downward lash instead
of a forward thrust, doubled whip length, and a larger attack range.

Reference: V06 full attack sequence and existing source action contract;
39 variable source frames, 1.5 seconds, zero-based frame 21 / 0.59625 s
contact and 0.45 s sound remain. User-requested downward motion overrides
the original source config's historical `thrust` label. Source-config.json
remains an unchanged provenance snapshot.

Right wrist rises over the head, follows an outward elbow arc and descends
to the right hip. The whip first forms an elevated crest, then lashes down
at the contact time. Torso/left arm retain the accepted V06 direction.

Whip bind centreline doubles from 3.2 m to 6.4 m, with ring spacing 0.1 ->
0.2 m. Grip dimensions and rope radius are unchanged. Curves are fitted to
a 6.4 m length and resampled by arc length onto the existing 33 ring bones.
Finite straight chords make tightly coiled evaluated lengths slightly
shorter than the fitted curve; the bind geometry is exactly doubled.
Ground constraints account for the body's final root grounding correction.
Idle/Howl store the extra length in loose loops; death lays it on the floor.

Controller: WHIP_REACH_MULTIPLIER=2.0 changes both attack_start_range and
impact_range from 3.2 m to 6.4 m. Width, damage, bleed, cooldown, locked lane,
wall blocking, interruption and hit timing are preserved. Expanded behavior
tests cover far windup, a hit at 6.3 m, a miss at 6.5 m, lateral dodge, a
wall at 4 m, and automatic attack initiation in the new range.

Rebuild with Blender 5.1: `blender -b --python build_motion.py`.
The builder starts with the existing V05 smoothed mesh and the V06 grip
preparation; local helper copies keep this iteration reproducible.
render_motion.gd --review-light adds preview-only inspection lighting;
project/game lighting is not changed.

Final checks: formal model 31 behavior assertions and 8 motion assertions
passed; main 180-frame headless smoke completed. Motion-test teardown still
reports existing resource-in-use warnings. Imported wrist descends 1.392 m
between 0.42 and 0.59625 s; forward-axis travel is 0.804 m, so downward motion
dominates. The earlier tight shoulder arc exceeded the 0.5 rad/frame limit;
the final outward arc peaks at 0.4337 rad/frame at 60 Hz. Exported bind length
is 6.399997 m. 1349 whip skin samples pass, max hand-to-whip distance 6.625 m.

Previews: Attack-detail.gif shows the body/hand and deliberately crops the
long distal whip; Attack-review.gif shows the complete extended trajectory.
Both are actual default-backend Godot renders with preview-only fill lights.
Use --detail to regenerate runtime-detail, and --review-light without
--detail for the full trajectory. Formal scene references foreman_v07.glb.
