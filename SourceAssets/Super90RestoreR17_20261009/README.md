# Restore Super90 reload R17

The user rejected R18's interpretation: reload speed must stay unchanged. They
want the loader drawn earlier and stages connected without idle gaps, rather
than skipping draw/dock and accelerating the return. This operation restores
the previous R17 reload baseline; it does not author another timing variant.

Restore 14 normal/empty animations: normal from R16, empty from R17. Cycle-only
was never changed by R18. Merge only these 14 entries into the four current grip
profiles, preserving other entries and retained overrides. Restore the original
R16 contact, audio and camera clocks and undo R18-specific entry/end blending.

Keep the separately requested 60 ms Super90 base shooting interval, 60 ms floor
and matching firing-animation cadence. Do not restore whole shared C++ files or
the gunsmith catalog from R18 backups.

`build_restore.ps1` builds the ordinary Editor/Game targets; `run_restore.ps1`
imports through the existing editor or background commandlet. Completion is in
`build_receipt.json` and `import_receipt.json`. No game, preview or test.

Follow-up: the first restore preserved old header mtimes with copy2, so UBT
skipped GunsmithSystem.cpp and kept R18 catalog durations alongside restored
R17 clips. TimingCacheFix records the 18 matching saved packages. The optional
saved-timing reader was blocked by an active native build before commandlet
startup; no saved_timing.json was produced. The final repair Editor/Game builds
both succeeded in batch 20261009-232957 (see build_receipt.json).
Rewrite restored headers with the current mtime before rebuilding dependencies;
do not preserve historical source timestamps during rollback. No animation or
gameplay-speed parameter was changed to compensate for the stale binary.
