# Super90 Loader R12

Rework of user-rejected R11. The user selected a shouldered stock with the reference video's gun pose and framing; the downward muzzle constraint is retired.

`author_r12.py` builds the guide/props, 15 animation FBXs, four grip-profile delta files, `authoring.json`, and `Super90_Speedloader_R12.blend`. `skin_arm.py` rebuilds the native arm deformation from the converted V7 skin hinge and a wrist-first solve. It does not export idle.

Run `run_r12.ps1` to save through the existing editor bridge or background commandlet, using the shared asset batch gate. It preserves non-loader profile entries and retained references. `Before/Content` holds the replaced packages; `import_receipt.json` is the actual save receipt with before/after hashes.

Reference, failure analysis, decisions, timing and acceptance boundary: `../../Docs/Weapons/super90-speedloader-r12-plan-20261009.md`.

Saved: `import_receipt.json` has `completed=true`, 24 saved packages with changed before/after SHA256 hashes. Each profile retains 15 unrelated entries plus 15 R12 loader entries. Background commandlet log: `import-commandlet-20261009-201004.log` (exit 0; 0 errors, 6 warnings).

Author preview: `D:/FPS3D/test/super90_r12_diag/final_empty/R12_empty7.gif`. Reconstructed hip camera with workbench materials; not a runtime capture. No game or PIE test performed.
