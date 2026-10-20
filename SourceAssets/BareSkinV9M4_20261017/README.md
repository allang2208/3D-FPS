# Bare skin V9 — M4 sample (2026-10-17)

Record: `Docs/Characters/bare-skin-v9-m4-sample-20261017.md`. Target: `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416` only.

Order (system Python unless noted; UE steps run through `run_ue.ps1` with UE closed):

1. `read_m4.py` (UE, read-only) -> `Snapshot/m4_read.json`: reference pose, skin slots/material settings, sampled M4 clips.
2. `geometry.py` -> `Work/geometry.npz`: ring/elbow-join smoothing, micro-fold and sliver cleanup, forearm section and bony landmarks.
3. `normals.py` -> `Work/normals.npy`; `export_work.py` -> `Work/mesh.npz`.
4. `blender_unwrap.py` (Blender) -> `Work/uv_new.npy` (new UV0).
5. `weights.py` -> `Work/weights.json` (wrist ring + elbow join denoise only).
6. `correctives.py` -> `Work/correctives.npz/.json` (elbow 20/75/110/135, wrist; every key fold-guarded);
   `grip_correctives.py` appends the held-grip examples (`JC_Grip_*`); `validate_anim.py` checks the shipped clips
   (`hand_holes_*` = faces turned against their own vertex normals, i.e. pinholes on the single-sided skin).
   `diag_palm.py` is the R2 pinhole diagnosis.
7. `fields.py` -> height/colour/masks; `blender_bake.py` (Blender) -> tangent normal; `finish_textures.py` -> `Textures/`.
8. `payload.py` -> `Work/install_payload.json`; `install_m4.py` (UE) installs; `read_saved.py` (UE) reads back.
9. `run_all.ps1` chains Editor build -> install -> Game build without interrupting other sessions.
   `reinstall.ps1` (R2) restores `Before/` over our own first install, reinstalls, reads back and builds.

`pose_ranges.py`, `blender_probe.py`, `blender_preview.py` are author-side checks (Blender renders are not UE renders).
`m4data.py` always reads the V8 snapshot (`M4(check_asset=True)` to insist the live asset is still V8). The live
viewmodel is now V9 R2, so `install_m4.py` only writes onto the V8 package: rerun through `reinstall.ps1`, which
restores `Before/` first and refuses if the live asset is not this task's last install (`install_receipt.json`).
