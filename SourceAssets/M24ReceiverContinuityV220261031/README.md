# M24 advanced chassis / skeleton stock continuity correction

This revision fixes the rejected trigger-guard assembly and the stepped receiver-to-stock transition. It applies when the advanced chassis and skeleton sniper stock are equipped together.

- The previous preview omitted the native animated trigger. The new previews include that actual trigger, the native magazine, bolt, barrel and scope at their original source coordinates.
- The old lower housing islands, two transition pieces and leftover guard strut were removed. One continuous lower receiver now runs from the measured Meshy hinge interface to the forend.
- The side recess crosses both former join positions as one continuous feature. Its floor has longitudinal topology instead of a warped n-gon.
- The trigger housing and closed guard are fitted around the native trigger. The animated trigger and its bone/path are not relocated.
- Stock and receiver are welded at the real interface; the internal mating caps are removed. The new geometry uses the already-saved M24 private finish materials, with a valid shared UV0 channel at export.

Published asset paths:

- `/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_ReceiverStock_Advanced`: stock, continuous lower receiver, guard and fasteners.
- `/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_AdvancedFront_ForIndependentGrip`: retained upper action and forend.

Both remain in the established weapon-root coordinate system. Grip meshes, poses, native-stock variant, weapon data, C++ and shared SVD/SVCH assets are unchanged. Exact pre-import backups are under `Before/`.

`M24_ReceiverContinuityV2_Editable.blend` is the editable source. `geometry_contract.json` describes exports and the welded interface; `geometry_review.json` records the scoped geometry inspection. `install_receipt.json` records the saved assets and material bindings.

`assembly_side.png`, `receiver_close.png` and `receiver_oblique.png` are Blender source-assembly previews with approximate neutral lighting and saved finish targets. They are not UE screenshots. No editor GUI, PIE or gameplay acceptance was run for this correction.
