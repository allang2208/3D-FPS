> 2026-09-27 整理：此版被 V7 替代。旧 `Export/` 已移到 `trash/melee-bow-iterations-20260927/SourceAssets/BowQuickCombatPalm20260927/Export/`；作者脚本、Blend、接触拟合及回退备份仍保留。历史导入脚本的旧导出路径不再是当前重导入口。当前版本与恢复边界见 [发布记录](../../Docs/Weapons/melee-bow-publication-20260927.md)。

# Bow quick combat V5: open right palm

2026-09-27. User requested inspection of the awkward right hand and a five-finger-open push based on the hand-animation skill / casting palm reference.

## Change

- Replace V4's lower wrap grip with an open right palm on the rear of the upper bow, about 30 cm above the left support hand. Palm forward; fingers point upward once the bow turns horizontal; thumb opens from its base.
- Use the V7 native hand's anatomical axes and preserved joint translations. Four fingers have mild individual flex and splay. No Manny transform copying, skin edits, bone scaling or fitted fist.
- Raise/open before contact; shoulder and elbow support the palm; detach toward the camera before relaxing and lowering the hand.
- Retain the exact previous bow path, left grasp, source timing, gameplay contact and speed/impact settings. The 0.90 s source clip is still retimed at runtime to about 0.571 s (miss) / 0.606 s (confirmed hit, including 35 ms stop).

## Source and delivery

- `author_palm.py`: native rig authoring and 240 Hz baking; depends on the retained V4/V11 author sources.
- `fit_palm.py` / `palm-fit.json`: translation-only heel placement against the upper bow's real exterior envelope.
- `Bow_QuickCombat.blend`: editable V7 skeleton and animation.
- `Export/A_Bow_QuickCombat.fbx`: baked animation.
- `import_palm.py`: canonical asset import/save; backs up V4 into `Before/` before replacement. Successful execution writes `import-receipt.json`.
- Canonical runtime asset: `/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat`.

Imported, compressed and saved through the background UE commandlet on 2026-09-27 at 13:35 local time; exit code 0. The previous V4 binary is retained in `Before/`. No interactive editor was opened.

## Requested inspection scope

Compared V4 with actual skinned V5 frames from the player's camera and close palm/side/back views. The fingers are visible above the horizontal bow, with the hand back toward the player. Reviewed entry, contact and release against the upper-riser exterior: the sampled phases have no penetration greater than 0.05 cm; the held palm's minimum separation is approximately 0.075 cm. This numerical result covers the source skin and upper-riser envelope only.

`Review/palm-review.jpg` and `Review/palm-closeup.jpg` are offline Blender inspections, using the current catalog's hip offset. They are not UE gameplay captures. No PIE, gameplay acceptance or broad regression was run; the user judges the final in-game feel.
