# Bare skin V9 rollout (2026-10-17)

Record: `Docs/Characters/bare-skin-v9-rollout-20261017.md`. Source of truth for the surface: `SourceAssets/BareSkinV9M4_20261017/`.
The rollout is complete and user-approved; the approved baseline is snapshotted outside the repo at
`D:/FPS3D/FPSGAME_Backups/BareSkinV9Baseline20261019/` (sha256 manifest). Surviving per-write backups sit
under `Before/Content/`; earlier `Before/` files were removed by an external cleanup on 10-19.

Per batch (`batchN.json` from `batchN_plan.py`):

1. `snapshot_targets.py` (UE, read-only) -> `Snapshots/` (all in-scope meshes, own reference skeleton); `scan_rest.py` audit.
2. `read_clips_true.py` (UE, read-only; uses `ue_rawpose.py`, the anim data model by time) -> `ClipsTrue/<pose source>.json`;
   `twist_audit.py <batch>` -> twist plan. Never read poses from `AnimPose` evaluation: it resamples at the wrong
   rate and returns the bind pose right after load.
3. `build_batch.py <batch>` -> mesh/corrective payloads and validation (`jc.py` driver mirrors the C++ component);
   `twist_specs.py <batch>` -> forearm twist specs (twist_01 100%, twist_02 50%).
4. `install_batch.py` (UE, `V9R_BATCH`) -> meshes, `MI_BareSkinV9`, forearm twist tracks; receipts `Installed/`;
   originals in `Before/`. Memory-bounded batches resume via receipts and `.partial.json`.
5. `reread_changed.py` re-reads written animation through the data model; `verify_branch.py` checks twist branches;
   `build_retry.ps1` builds Editor + Game.

Arm animation repair: `armfix.py` / `elbow_hinge.py` / `reroute.py` plan per-frame changes (forearm bone spin removed,
elbow axial twist moved into the forearm progressively 60-120 deg, hand roll only corrected on the left hand and only
on frames that actually cross ±180 deg), `armfix_write.py` writes, receipts under `InstalledArm*/` `InstalledBranch/`.
Weapon material slot repair: `matprobe.py` / `matprobe_compare.py` compare triangle material assignments against
`Before/` backups; `matfix.py` restores them (Pit Viper grip / Super90 bolt-and-shell fix).

Transition correctives: `pose_examples.py` builds `JC_Pose_*` examples (worst-frame first, bounded neighbourhood
increase, per-side capacity 48, rejected frames retried), `make_clipssim.py` -> `ClipsSim2/` simulation data,
`install_pose_loop.ps1` installs until `Installed_pose*/` receipts cover every mesh. `patch_clipsim.py` refreshes
simulation after animation rewrites; `affected_groups.py` lists groups needing regeneration.

Archive: rolled-back approaches, one-off probes/experiments, run logs and consumed payloads were moved to
`trash/bare-skin-v9-scratch-20261020/` (per-file sha256 in `archive-manifest.json` there) by `archive_scratch.py`.
Modules: `rollout.py` (M4 V9 source + snapshots), `transfer.py` (UV-key / position correspondence, surface transfer,
target fold relaxation; uses `match.py` / `uvmatch.py`), `jc.py`, `twist_fix.py`, `unspin.py` (elbow-axial resolver
used by `audit_elbow_axial.py`).
