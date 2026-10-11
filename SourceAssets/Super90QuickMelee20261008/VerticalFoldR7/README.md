# Super90 quick melee R7 — vertical left tuck / forward stock strike

The user rejected R6's motion interpretation. R7 is a new coordinated gun and
bilateral arm path, not another elbow offset on the old horizontal sweep.

## Motion contract

- Withdraw the left support hand towards the left side of the body. Its elbow
  folds down in the vertical plane through the shoulder and wrist; palm roll
  does not steer the left elbow sideways.
- Turn the held assembly during this tuck, then extend the right arm to drive
  the buttplate forward. The complete gun path is rebuilt from editable stages.
- Recover by unfolding and returning the gun to the current grip's idle pose.
- Keep gun-relative palm transforms and local finger shapes. Both palm world
  paths and both support chains change with the new gun path.
- Preserve the 0.9 s source duration, 240 Hz samples and 1/6 s contact clock.
  Stage slopes distinguish the withdrawal, fast drive, follow-through and return.
  No global playback-rate change, hit/cooldown/damage or camera change.

`motion_controls.json` holds the editable camera-space stages and torso anchors.
`author_motion.py` writes 15 tracks: gun root and seven support tracks per arm.
Five grip variants are authored independently. The ownership curve introduced
by R6 is retained, with entry/return matched to the new motion. The existing
`Super90SupportArmNode` consumes it without another C++ change.

## Inputs and delivery

`installed_source.json` is the preceding turn's R6 payload that was actually
saved to the canonical packages; provenance is in `source_provenance.json`.
The initial attempt to reread through a commandlet failed before reading or
writing an asset. That failed log is not evidence of a source export or save.
`read_source.py` remains available for future fresh input captures.

Calibration remains in sibling `LeftArmR5` and the V7 editable parent is
`SourceAssets/BenelliM4Super9020261006/Super90_Gameplay_Editable.blend`.
Neither dependency is retired by this revision.

Run authoring, save the editable Blend, then use `save_background.ps1` to write
the canonical melee sequence and merge only this action's tracks into the four
current profiles. Other actions and retained overrides are read from the live
profiles. Active PIE/dirty target assets stop replacement. `Before` preserves
the five previous packages. `save_receipt.json` records actual saved assets.

No editor launch, gameplay test, screenshot, render or visual acceptance is
part of this delivery. This asset-only revision needs no new native build.
