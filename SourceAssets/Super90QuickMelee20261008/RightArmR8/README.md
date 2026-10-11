# Super90 quick melee: R8 right wrist and arm

Scope: the reported right-wrist compression, right-arm silhouette and buttstock overlap in R7 quick melee. Preserve the R7 gun path and left vertical tuck, 0.9 s source duration, hit time, runtime ownership curve, R24 reload assets and all other profile entries.

The old fixed palm frame forces the arm into the buttstock. R8 turns the right hand around the pistol grip in three dimensions, fits finger joints along the grip surface while retaining their natural curl, and solves the upper arm / forearm with their original segment lengths. The distal helper carries the wrist frame and the middle helper blends that change over the forearm. The shoulder stays on the body side; the windup adds a bounded downward/backward adjustment where the stock crosses the upper arm. Actual V7 skin points and sections of the stock mesh guide the local clearance fit; this is not a runtime collision system.

- `installed_source.json`: current installed native animation and four melee profile deltas read through the existing editor bridge.
- `support_geometry.py`: actual V7 skin, native bind transforms and stock surface sections.
- `author_motion.py`: right-hand regrip, contact fitting, arm support and smoothed source keys.
- `refine_support.py`: final windup shoulder / elbow clearance, following the authored regrip. Its immutable input is `BeforeSupportRefinement/`. Run this after `author_motion.py` and before either save script.
- `finish_elbow_path.py`: continuous anatomical elbow-plane and shoulder curves after support fitting. Final controls are in `elbow_path_controls.json`; the delivered patch and editable file are authoritative.
- `check_reported_wrist.py`: requested source comparison of wrist deformation, right segment lengths, finger contacts and preserved gun/left transforms.
- `inspect_pose_frames.py`: source-only comparison of the reported strike phases; not gameplay acceptance.
- `save_editable.py`: five editable actions in `Super90_QuickMelee_Editable.blend`.
- `save_assets.py`: 22 right-arm / finger tracks in the native melee and the melee-only deltas in four current profiles. Preserve every other row and retained reference.
- `save_background.ps1`: existing editor bridge when available; otherwise a background commandlet under the shared asset mutex.

`Iteration1` through `Iteration5` are rejected source candidates, never production assets: fixed-palm constraints and a single-axis regrip did not resolve both wrist deformation and stock overlap. The fifth candidate selected the wrong clearance route and forced fingers toward unreachable old contact points. The final fit starts at the strike pose and continues in both time directions. The installed status is recorded only by `save_receipt.json`. No game or PIE run is part of this delivery.

Delivery is saved: native melee plus four current profiles, five changed package hashes in the receipt. Existing PIE was stopped for asset writing with the user's confirmation; the editor remains open. The source checks and Blender poses are not runtime acceptance.
