# Super90 R19

Continue from restored R17. Refill the available magazine deficit atomically at
the existing end-of-push contact. Keep reserve accounting, empty bolt closure,
the current reload speed and Super90's 60 ms fire interval.

`author_r19.py` preserves the wrist/finger/gun/prop paths and original sample
times. It fits a small, smoothly weighted left-arm bend-plane rotation using the
actual V7 open boundary in the existing author camera, then rebuilds the affected
grip deltas. Normal and empty use 4 degrees; cycle-only needs no authored change.

`run_r19.ps1` saves 14 animations and four grip profiles through the existing
editor bridge, or a background commandlet when no editor is running. It refuses
overlapping unsaved target packages and preserves other clips. `build_r19.ps1`
performs ordinary builds only when editor/game/compiler binaries are not in use.
Do not stop another task's editor or bypass the shared batch gate.

No runtime test or render was requested. Authoring output, saved assets, live
patches and ordinary base binaries must be reported separately.
