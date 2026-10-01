# SVD Refine04 — fine surface finish

2026-10-01: imported and saved 59 existing material instances, one 1024² RGBA
linear BC7 grain texture and one private material graph. The material graph is
used only by the original mixed handguard/body and factory-stock instances.
No mesh, animation, collision, material slot binding or weather table changed.

Production entry points:

1. `capture_inputs.py`: read current source bindings/graphs/parameters.
2. `produce.py`: author the periodic technical PBR texture and `recipe.json`.
3. `apply_finish.py`: import, compile and save through the project batch gate.

The source baseline is `Input/current.json`; per-instance backups are `Before/`;
the save receipt is `apply_receipt.json` (`complete=true`, `tested=false`).
The application used the already-running editor bridge, not a newly launched
editor or a concurrent commandlet. The bridge log is
`D:/FPS3D/FPSGAME/SourceAssets/WeaponSurface20260930/logs/apply_finish.20261001-152049-962.bridge.txt`.
It reports `success=True` and `WEAPON_SURFACE_SVD_R04_SAVED 59 instances 1 texture
1 private master; tested=False`.

No game run, screenshot, beauty render, visual acceptance or extra test was run.
See `Docs/Weapons/svd-finish-refine04-20261001.md` for scope and retained details.
