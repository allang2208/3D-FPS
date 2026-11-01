# M24 reload flow — 2026-10-28

User-requested revision: remove the stiff pause after extraction and make discarding the old magazine readable. Applies to normal and empty reloads with both the 5-round and 10-round magazine.

## Cause and revision

The previous release pass froze the complete left arm at source frame 23 through the 24–27.5 interval. Its magazine drop began at frame 26.25 with translation only, close to the lower edge of the view. The paced runtime clock made the hold particularly visible.

This pass retains the initial extraction corridor until frame 22, then follows a continuous wrist arc to the left. Staggered thumb/finger opening accompanies release at frame 25.25 (1.58258 seconds at the unmodified reload clock). The magazine carries lateral velocity and angular motion into its ballistic fall. The empty hand continues to the retrieval point; it does not follow the falling magazine. The prop is reused for the new magazine only below the frustum during frames 29–30. The replacement grip closes before the magazine returns into view. After seating, the opening hand retreats along the outside of the magazine.

The native arm solver keeps the saved shoulder anchor, bone lengths, elbow plane and V9 forearm twist convention. The previous source shoulder retraction was too early for a visible toss, so its global shoulder displacement was not reused. Current gun/right-arm trajectories, scope work, quick melee and equip-only bolt motion remain intact.

## Delivery

- `M24_ReloadFlow_Editable.blend`: editable actions, quarter-frame keys at the original 30 Hz source clock, based on the latest stock-bash source scene.
- `flow_patch.json`: additive local tracks for source frames 20–50, merged into the two existing runtime profiles. The existing base animation sequences remain their shared inputs.
- `author_flow.py`, `library.py`: reproducible authoring from the fresh saved-asset snapshot in `ue_before.json`.
- `install.py`: merges only the four reload entries and owned left-arm/magazine tracks; checks concurrent changes before editing; saves the actual profile assets. Backups are kept in `Backups/`.
- `M24_ReloadFlow_preview.gif`: offline authoring preview of normal reloads, using the existing runtime time map. Gray materials are for pose review.

Runtime profiles:

- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip`
- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_Mag10`

The reload duration, ammo timing, insert/seat sounds, empty-reload bolt tail, viewmodel anchors and mesh are unchanged. No C++ change or DLL rebuild is required. A successful `install_receipt.json` plus `readback_receipt.json` records publication, independently of this source document.

## Scoped review

The user explicitly requested inspection. `review_flow.py` and `motion_review.py` therefore inspect the affected hand/magazine sequence and produce offline images; no game/PIE test is started. All four variants retain the unrelated component transforms. The grip remains registered while the magazine is held; the original zero-speed interval is absent in the reviewed extraction/release range. Prop switching is below the frustum for both magazine sizes. The bone translation residual is below 0.02 mm and is numerical decomposition precision, not a bone-length edit.

Runtime appearance, audio and gameplay acceptance remain for the user to test.
