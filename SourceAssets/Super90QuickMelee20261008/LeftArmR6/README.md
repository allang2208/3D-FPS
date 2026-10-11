# Super90 quick-melee left arm R6 — 2026-10-10

User reported a foreground elbow/upper-arm hump and twisted left wrist during
the horizontal gun swing. This revision changes the support chain only.

- Fresh installed source keys are in `installed_source.json`, read through the
  existing editor bridge. Calibration and skeleton conversion remain in the
  retained sibling `LeftArmR5` directory.
- `author_motion.py` lowers the shoulder support and keeps the elbow below the
  held wrist. The upper-arm frame follows the skin hinge; the forearm helpers
  converge to the palm roll at the wrist instead of leaving residual twist there.
- Both palm component transforms, fingers, gun, right arm and 0.9 s / 240 Hz /
  1/6 s contact clock remain from the installed source. Seven left-chain tracks
  are reauthored for base, vertical, canted, prism and angled grips.
- `Super90MeleeArmAuthored` is the ownership weight for the final support node.
  The current animation graph blends the curve with action weight, so idle,
  interruption and recovery retain the ordinary Super90 support correction.
  Full melee weight uses the authored elbow instead of solving it again with
  the loader palm-width rule. Other clips have no such curve.
- `save_assets.py` saves the canonical melee sequence and merges only its seven
  left-chain tracks into the four current grip profiles. Loader entries and
  retained animations are copied from the current loaded profiles, not an old
  profile dump. Target dirty packages and active PIE stop the write.
- `save_editable.py` saves five matching Blender actions and the ownership curve
  as a keyed custom property in `Super90_QuickMelee_Editable.blend`. No render.

Production order: read source, run authoring, save editable source, build native
targets, save assets. `build_r6.ps1` and `save_background.ps1` use the existing UE
batch mutex. `compile_existing_editor.py` is an alternative for this function-body
change when an editor is already open; it was not used for this delivery.

Before-state assets and the original native function are retained under `Before`.
Build and asset-save receipts distinguish actual delivery from source generation.
This revision has no gameplay test, screenshot, render or visual acceptance.
