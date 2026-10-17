# M870 support-arm and ADS repair

User feedback: the left forearm/wrist is twisted, with the left hand and chainmail sleeve crossing the iron sights. The two supplied screenshots are the visual evidence for this task.

The original M870 authoring retained a Super90 hand pose above the pump. Its hand surface reached above the sight axis. The subsequent UC migration retained that grasp and carried old forearm helper rotations through the new arm solve. ADS loads the same idle pose, so the original support-hand defect persisted there.

## Production changes

- Rotate the complete grasp to the underside of the pump, retaining native hand geometry, digit shape, skeleton, skin weights and bone lengths.
- Rebuild the left clavicle, shoulder, elbow and wrist as one arm. Forearm twist helpers are siblings: each receives its own anatomical station transform and a progressive share of pronation. No donor helper rotation is carried over after the solve.
- The UC reload turns the receiver substantially. Let the cylindrical fore-end turn within the support hand, keeping the palm underneath; otherwise a fixed grip would twist the arm again during loading. Right-hand feeding, cartridges, gun motion and event times are preserved.
- Refit the arm root below the weapon and choose a continuous elbow plane. Smooth the construction angles, then solve again at exact native bone lengths; retain the same endpoint solution for state transitions.
- Refine sight-marker tracks to the actual rear aperture centre and front-post tip. ADS continues using the current shared idle/fire sequences and existing sight calibration.
- Apply to all 13 active M870 roles: idle, walk, run, equip, fire, cycle, normal/empty reload, inspect, melee, and sprint enter/loop/exit. Restore the existing melee ownership curve after reimport.

`M870_GripADS_Editable.blend` and `Exports/Animations` are produced by `author_grip.py`. Inputs are the current `M870UrbanAnimations20261015` author file plus the original `M870Tactical20261015` bind/exporter. This revision must be applied after either earlier full authoring pipeline.

`install_animations.py` replaces only those animation packages. No gun mesh, hand mesh, outfit asset, skeleton, material, C++ or gameplay clock is changed. Old animation packages are retained under `Before/Animations`.

The source attribution/reuse status remains as documented in the two earlier M870 production folders. Nothing is committed or published. Source measurements and solver parameters are production inputs, not visual acceptance. No game launch, screenshot, preview render, audio audition, regression or multiplayer test is performed; the user handles runtime acceptance.
