> 2026-09-27 整理：此版被 V7 替代。旧 `Export/` 已移到 `trash/melee-bow-iterations-20260927/SourceAssets/BowQuickCombatContact20260927/Export/`；作者脚本、Blend、接触拟合及回退备份仍保留。历史导入脚本的旧导出路径不再是当前重导入口。当前版本与恢复边界见 [发布记录](../../Docs/Weapons/melee-bow-publication-20260927.md)。

# Bow quick melee: upper grasp and camera tuning

2026-09-27. Requested scope: compare quick-melee shake, reduce excessive bow
shake, and remove right-hand clipping on the upper bow.

## Delivered

- Right grip still uses the anchor 30 cm above the left grip. The bow turns
  horizontal and pushes forwards; duration 0.90 s, contact 0.32 s unchanged.
- Whole-hand correction relative to V3: -1.24 cm local X, +3.10 cm local Y,
  -23 degrees around local Y at the upper grip anchor. Individual fingers
  open around the wider wood/binding. Skin, rest pose and bone lengths stay
  unchanged. Exact local transforms are in `contact-fit.json`.
- Reach and release now open the fitted grasp and travel from/to the outside
  of the bow. They no longer blend the string-pulling finger pose through
  the wood. Contact remains locked from 0.14 to 0.62 s.
- Only the bow's shared impact impulse is attenuated. Axial movement and
  pitch use 0.40 gain; lateral movement, yaw and roll use 0.16; vertical
  translation uses 0.25. The same gains apply to the residual tail.

## Shake comparison

The pistol, rifle and sword paths use `QuickCombatImpactShake::Add`. The bow
previously used exactly that same impulse, not a larger numerical gain.
Their individual action-camera curves differ.

| Impact component | Other quick melee / old bow | New bow |
|---|---:|---:|
| Backwards translation before character scale | 20 cm | 8 cm |
| Pitch before character scale | 26 deg | 10.4 deg |
| Yaw before character scale | 9 deg | 1.44 deg |
| Roll before character scale | 8 deg | 1.28 deg |
| Pitch at default CameraMotionScale 0.45 | 11.7 deg | 4.68 deg |

These are the shared impact component at age zero; the bow's small forward
action curve is added separately. Duration and contact frame are unchanged.

## Requested contact inspection

`fit_contact.py` uses the real modular bow body, including upper wrapping.
The source has nested shells with mixed normals; an outer radial envelope
is used for contact clearance, rather than interpreting raw normal signs
as solid containment. The complete weighted hand surface is evaluated.

- V3 closed-grip penetration into that envelope reached approximately 3 cm.
- V4 sampled reach / grip / push / release poses have positive clearance
  (minimum approximately 0.047 cm); see `motion-clearance.json`.
- Offline close-ups and player-camera views are in `Review`. These inspect
  the authored animation and current catalog hip offset, not a game capture.
- No gameplay session, broad regression or acceptance test was started.

## Saved integration

`import-receipt.json` records the saved asset at
`/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat`.
The V3 binary is retained in `Before/A_Bow_QuickCombat.uasset`.

`build-editor.log`: normal FPSGAMEEditor build succeeded, including
`FPSQuickCombatComponent.cpp` and the linked `UnrealEditor-FPSGAME.dll`.
Two earlier bridge attempts found no running MCP endpoint and made no
changes. Integration subsequently used the background commandlet.

Run `author_contact.py` in Blender to reproduce the FBX and .blend from the
saved fit. `fit_contact.py -- --refine` is optional authoring, not a runtime
dependency. `prepare_delivery.py` creates the scoped import and render
scripts; `import_contact.py` imports and saves the canonical animation.

Final in-game shake comfort and grip appearance remain for the user to test.
