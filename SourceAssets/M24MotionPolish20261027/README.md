# M24 motion and sight correction — 2026-10-27

This revision addresses the reported tactical-sprint left-arm twist and camera intrusion, bolt-hand contact, and rough mechanical-sight finish.

- `author_motion.py` uses the V9 rest hinge to solve the released left arm and its twist helpers. It transports the shoulder skin down by 4 cm as the hand withdraws, with a continuous transition back to the accepted hold. The right arm and rifle sprint motion retain their source tracks.
- `fit_bolt_grip.py` fits native finger flexion and the palm to the existing bolt knob. The contact is expressed relative to `WPN_BoltHandle`, then reused for fire, cycle and empty reload. The hand approaches, stays attached during manipulation and releases. Finger translations, bone lengths, mechanical tracks and event clocks are retained.
- `author_sights.py` retains the sight interfaces and aim sockets, increases ring resolution to 96 segments and bevels to four segments, and replaces separate flute boxes with continuous milled drums.
- `install.py` bakes six corrected roles into sparse native grip profiles. Other roles retain the prior support profile; the 10-round variant also retains its five magazine-reach arm tracks. Full runtime animation copies are not saved.
- `install_sights.py` saves private WS1 material instances with satin roughness 0.28, grain amplitude 0.006, mottle 0.003, no scratch/stipple/wear, and a flat surface-normal input. The black sight interior remains matte.

Runtime references are in `Source/FPSGAME/Weapons/M24WeaponAssets.h` and `M24Attachments.h`, under `/Game/Weapons/M24/MotionPolish20261027`.

## Bounded diagnosis requested by the user

`before.json` and `after.json` measure the authored V9 skin against the calibrated hip camera. At the sampled sprint-loop frames, visible left-arm vertices fell from 5,658 at the reported middle pose to zero, and the native elbow-plane mismatch changed from about 152 degrees to zero. These are source-space diagnostics, not gameplay acceptance.

`bolt_grip_fit.json` records the fitted knob contact: nearest pad samples average approximately 1.18 mm (thumb), 0.81 mm (index), and 0.79 mm (middle), with no penetration beyond the 0.15 mm fitting tolerance into the knob convex shell at the reference pose. This checks the knob fit, not every weapon surface or every interpolated runtime pose.

`after_sprint.png`, `after_bolt.png`, and `sight_rear.png` / `sight_front.png` are Blender source renders. They do not depict a running UE game or its final lighting. `install_receipt.json` records the saved UE assets, and `build_receipt.json` records the native build when complete. No PIE, gameplay or multiplayer tests were run.
