# 杖头水晶透明度恢复

2026-09-28。用户反馈 V22 水晶过白，要求恢复上一个版本的透明度。本次沿用 V22 现有资产路径，将透明相关参数恢复到 V20：

- 不透明度：`0.84–0.96 → 0.24–0.42`。
- Thin Translucent 透光色：`(0.12, 0.17, 0.15) → (0.78, 0.84, 0.82)`。
- Blender 透射权重：`0.12 / 0.025 → 0.70 / 0.46`。

当前基色、粗糙度、切面高光、几何、握持及 V28 动作保持。保留 V23 预览材质的 Default Lit／Before DOF 覆盖率修复，不恢复曾导致 UI 水晶消失的双源透明预览方式。

已修改 `QuartzAimV22/quartz_parameters.json`，由 `restore_materials.py` 在后台 commandlet 中重建并实际保存两个现用材质：

- `/Game/Weapons/ApprenticeStaff20260927/QuartzAimV22/Materials/M_Staff_QuartzDenseV22`
- `/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23`

原包保存在本目录 `Before/`；保存回执 `install-receipt.json`。命令日志为 `Saved/staff-quartz-transparency-restore-v29.log`，命令执行成功。

`update_editable.py` 同步保存当前 `BarkRebuildV21/Staff_NaturalBark_V21.blend` 和 `PrimaryWholeArmV28/Staff_PrimarySmash_V28.blend` 的水晶材质；只修改材质节点，未重建模型或动作。原 Blend 也保存在 `Before/`。

无需 C++ 构建。本轮未打开交互编辑器、运行游戏、测试或渲染，实际透明度观感由用户确认。

后续修正（V30，同日）：上述 NullRHI commandlet 完成了包保存，但未证明实际 GPU 材质编译成功。用户随后反馈游戏内棋盘格；编辑器日志定位为重建时旧薄透明输出节点残留造成的编译失败。已在 `QuartzGraphRepairV30` 修复节点删除方式，并通过正在运行的编辑器重新编译、保存两个材质；透明度参数保持本次恢复值。详见 `../QuartzGraphRepairV30/DELIVERY.md`。
