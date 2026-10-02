# M16 common M4 V7 wrist bind

This extends the saved `M16Repair20261002/NeutralBind` production. Its nineteen
neutral left digit references remain the hand baseline. M16's `hand_l` mesh
reference rotation now comes from the existing natural M4 V7 wrist. This changes
the mesh inverse binding, rather than introducing another runtime twist angle.

The eight existing neutral-hand mesh packages retain their native M16 local
translations, scales, hierarchy, weights, shared animation skeleton, materials,
UVs, mechanical geometry and animation keys. Naked-arm positions are rebuilt
directly from the accepted common V7 canonical surface, including the wrist
vertices weighted to `hand_l`. Glove positions are recovered from the retained
first shell source and bound once to the new wrist references. The previous
compressed NeutralBind surface is used only as the installer precondition.

Two additional existing M16 cuffs need the same binding: the field sweater has
839 hand-weighted source vertices and chainmail has 6,577 hand/digit-weighted
source vertices. Their old source snapshots supply only the necessary cuff
geometry. Forearm-only vertices, cuff detail, lining, weight data and LOD policy
are retained. Their digit mesh references also become the current nineteen
neutral references so the follower meshes use the same wrist and hand frame.
The charcoal short sleeve has no wrist/hand/digit weights and remains unchanged.

Entry points:

- `author_common_wrist_bind.py` creates ten exact position patches, the common
  wrist reference, author manifest and editable JSON. It does not import assets.
- `save_editable.py` was executed in background Blender and actually saved
  `Editable/M16_BareArmsV7CommonM4Wrist20261002.blend`.
- `install_common_wrist_bind.py` can run through the existing serialized UE
  Python bridge or an unattended Python commandlet. It refuses PIE, dirty target
  packages, changed package hashes, changed active cuff paths and mismatched
  source geometry before its first mutation. It backs up each package and writes
  `installed.json` after each actual package save. It does not start UE itself.
- `Before/Reference` retains the superseded native wrist reference and neutral
  digit production receipts. Package backups are written under `Before/Packages`
  when the installer actually runs.

Runtime integration must remove the rejected M16 partial forearm-helper twist
block in `DoorPushPoseLayer.cpp`. The ordinary complete authored local arm chain
is appropriate once M16 and M4 share the wrist mesh-local reference. Sprint
production is owned by the separate Sprint subdirectory; these sources do not
modify its animation keys.

Authoring and the editable Blender file are complete. UE package saving is
pending; this worker has not invoked the bridge, commandlet, editor or build.
No game, render, animation preview, runtime test or acceptance was performed.
