# AKM authored finish R01 — saved 2026-10-01

User-authorized AKM metal response alignment with WS1.1, preserving the original authored finish. This is an explicit AKM pilot; M4 and HK416 are outside this change.

Saved through the already running project editor after the user stopped PIE:

- 38 material instances, 36 private source-graph adapters, one 1024² linear BC7 roughness detail texture.
- Material slot deltas on 30 current meshes, including the main skeletal mesh, magazines, mounts, optics shells and attachments.
- Two AKM-only device body materials updated at their existing paths because TacticalDeviceComponent loads them directly.
- 40 self mappings merged into the existing weather presentation library.
- `apply_receipt.json`: `complete=true`, `geometry_changed=false`, `tested=false`.

Production log: `../../logs/apply_finish.20261001-164157-707.bridge.txt`.
Full production note: [AKM surface R01](../../../../Docs/Weapons/akm-surface-standard-20261001.md).

## Source and controls

`Input/current.json` captures source graph wiring, material slots, original effective parameters and weather sources. `produce.py` writes the recipe, HLSL and technical detail texture. `apply_finish.py` creates the saved materials and writes only scoped bindings. `finalize_records.py` publishes `bindings.json` after the production save completes.

Original BaseColor, Metallic, Roughness, AO and normal textures are not rewritten. Color keeps the authored RGB and applies a continuous tone scale to neutral, medium-value metal; saturated decoration, bright exposed wear, dark recesses and nonmetal areas reduce or suppress that adjustment. This is a conservative numeric mask, not a semantic paint/marking segmentation map. Source roughness deviations are retained at .75 weight. Metal identity and structural normal chains remain authored.

The new detail texture affects roughness only. No new procedural scratches or grain normal layer. Original wood/bakelite, grip polymer, glass, reticles, rubber, special trim, inner regions and hands retain their individual paths. Existing extended-magazine UV2–6 seam normal reconstruction remains in the duplicated source graph.

## Later explicitly requested reimports

Do not rerun source capture against already upgraded assets as a new baseline. `bindings.json` is the current material-slot record. The common `WeaponAttachmentFinish20260913/import_finish.py` now reuses it for exact matching AKM meshes; other source importers can be followed by `rebind_current.py` through the existing runner:

```powershell
& 'D:\FPS3D\FPSGAME\SourceAssets\WeaponSurface20260930\run_ue.ps1' -Script 'D:\FPS3D\FPSGAME\SourceAssets\WeaponSurface20260930\AKM\Refine01\rebind_current.py' -FileCache -GateSeconds 300
```

That is a future production entry, not a test, and was not run after this save. It restores only the recorded old/current bindings and merges the self-wet mappings. If another task has changed a slot identity/material, it stops rather than replacing that work. Asset construction uses `apply_finish.py`; rerunning rebind does not recreate deleted materials.

Pre-change packages are under `Before/`. Do not restore the whole weather library over later parallel changes; revert only this revision's entries when an actual rollback is requested.

No game, PIE, render, screenshot or additional test was run for this revision. Saved assets and necessary material compilation are production completion, not visual acceptance.
