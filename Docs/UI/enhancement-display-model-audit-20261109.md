# Enhancement workbench display audit, 2026-11-09

## Result

The final `FPSGAMEEditor` build succeeded. The isolated `EnhancementDisplayAudit` commandlet completed with **69 equipment definitions, 25 additional Viper single-slot option cases, one Viper factory-reset case, 95 cases total, and 0 failures**.

This is structural engine validation with real loaded assets under NullRHI. It is not rendered visual acceptance, a mouse-input test, or an exhaustive test of every cross-slot modification combination. No normal player save was used; each run initialized a unique `DisplayAudit_<GUID>` profile.

## Defects and changes

- The old gun display copied local animation bones but never refreshed the poseable component before disabling its tick. Its visible gun could remain in the reference pose while static attachments used the sampled idle pose.
- The display now snapshots the source's **final component-space bones**, converts that snapshot into parent-local transforms, and refreshes immediately. This also retains procedural belt/carry-handle corrections which plain `CopyPoseFromSkeletalComponent` misses. The first audit identified a 12.55 cm maximum bone discrepancy on PKM and 0.011 cm on LMG201; both passed after final-pose copying. Final maximum discrepancy across all cases was approximately 2.73e-13 cm.
- Preserve source culling bounds scaling, including Pit Viper's established expanded envelope.
- Match the icon recipe for installed tube-shotgun loader guides and M24 bolt appearance.
- Route all three production tools through the tool builder rather than attempting an absent melee `world_mesh`.
- Recognize actual rendered children of the skeletal bow assembly's intentionally empty static root, and wait for the relevant tool-loading handle.

The existing shared workbench placement, arm-material filtering, inventory ownership, source asset identities, and other sessions' changes were preserved.

## Coverage

The merged catalog contained 288 definitions. The enhancement eligibility predicate selected:

- 21 firearms.
- 11 modular melee weapons.
- 3 production tools.
- 2 bows.
- 1 staff.
- 31 equipment / magic-book items.

Checks cover display creation, asset-load readiness, nonphysical cosmetic ownership, finite positive bounds, visible geometry inside the centered envelope, exact frozen firearm pose relative to its source, retained culling envelope, and coherent component transforms after table-style rotation and scaling. Viper additionally covers all 25 catalog single-slot choices and return to its factory recipe.

## Evidence

- Final build: `Saved/BuildEditor/build-20261109-100849.log`.
- Final engine audit: `Saved/EnhancementDisplayAudit20261109/run-20261109-1009.log`.
- Machine-readable final report: `Saved/EnhancementDisplayAudit20261109/report.json`.
- Initial 2-failure report retained: `Saved/EnhancementDisplayAudit20261109/report-first-run.json`.
- Static merged catalog and direct asset existence inventory: `Saved/EnhancementDisplayAudit20261109/catalog_inventory.json`.
- Pre-edit source copies: `Saved/EnhancementDisplayAudit20261109/Before/`.

Run from the project directory after a successful ordinary build:

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
  'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=EnhancementDisplayAudit `
  -unattended -nop4 -nosplash -nosound -nullrhi
```

The commandlet performs synchronous waits only in its isolated offline audit path. Normal workbench loading remains asynchronous. Runtime visual behavior and drag interaction should be reported separately from these structural results.
