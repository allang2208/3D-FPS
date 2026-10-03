# Can grasp revision — 2026-10-03

`author_grip.py` authors only the soda-can grasp from the accepted V7 native
hand skin and the actual saved 12.2 cm × 6.1 cm can. Palm contact, the four
finger-pad wraps, and the opposing thumb are authored together. The runtime
uses the existing semantic-palm solver and cumulative phalanx flex angles;
bone lengths, rest transforms, weights, and shared hand assets are retained.

The resulting `grip_profile.json` moves the palm relation from the former
potion-derived anchor to the can body's own contact. It increases finger
closure and gives the thumb its own opposition direction. Publication updates
only `soda_can` in `Content/ColdSteelData/potion_use_motion.json`.

The pose layer now recovers at the can's existing release time, 1.94 seconds,
so the hand keeps its authored grasp during the visible lowering movement.
The action still lasts 2 seconds and settles hydration/SAN at 1.58 seconds.
The can trajectory, effects, audio, other consumables, and item art are retained.
`SourceAssets/SodaCan20261003/configure_soda.py` reads this same profile to
keep future item publication from restoring the old loose grasp.

Only JSON and authoring sources changed; no new native binary or asset import
is needed. The existing motion loader reads the file at pawn BeginPlay, so
restart the current play session to load the new grip.

No editor UI, gameplay test, QA render, or screenshot was started. Final hand
contact and appearance are left for the user's game test.
