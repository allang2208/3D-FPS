# M16A2 gameplay authoring

UE5 M16A2 的 Manny 手臂、机械分件和 12 个动作源文件。玩法物品为 `ue_m16a2`，入口为 F6 基本调参中的原生成物品卡片。

完整参数、公式对照、操作及交付边界见 [M16A2 三连发接入](../../Docs/Weapons/m16a2-gameplay-20260919.md)。枪械原模型和材质来源见 [署名记录](../M16A2Migration20260919/ATTRIBUTION.md)。本次沿用当前项目的 Manny 手臂、M4 动作和音频。

`build.py` 以既有 M4 源动作为参考，适配 M16 实际机械位置，保存 `M16_Manny_Editable.blend` 并导出 `Export`。`import_assets.py` 在运行中的 UE 编辑器内导入 `/Game/Weapons/M16A2/Gameplay20260919`，复用迁移材质和现有手臂材质。`build.json` 与 `import_result.json` 是制作/导入记录，不是测试报告。

静态目录图标已在 2026-09-20 改为使用共享 UE 武器图标制作入口生成，写入 `Content/ColdSteelData/Icons/ue_m16a2.png`。此前 Godot PNG 已归档到本机 `trash/m16-retired-20260920/SourceAssets/M16Presentation20260920/before`。动态图标恢复及枪口安装修正见[制作记录](../../Docs/Weapons/m16a2-icons-muzzle-20260920.md)。

2026-09-20 按用户截图排查并修正新增机械骨骼的绑定方向：Blender EditBone 必须先设置非零长度，再赋予绑定矩阵。已重新导出并导入网格、专用骨架及 12 个动作。针对本次错位的源几何比较及 UE 骨骼姿态读取记录位于 `Diagnostics/`；未启动游戏或进行视觉验收，游戏内外观由用户确认。

随后按用户“直接参考 M4 换弹，不重新设计”的要求，普通与空仓换弹完整保留 M4 源动作的手臂、手指及 twist 骨姿态，取消这两个动作上的 M16 左臂 IK 和接触位移修正。`import_reload.py` 只更新这两条动作；源文件由 `build.py` 生成。此次换弹修改未测试，旧 `Diagnostics/` 不作为本次换弹的验收记录。

此前短按方案及其导入入口已归档到本机 `trash/m16-retired-20260920/`。当前按用户要求采用拉机柄复进：左手回到护木后，右手复用 M4 WrapGrip 拉栓动作并对准 M16 横柄实际几何，锁扣、拉柄、枪机和后拉/松手声音同钟。[拉柄制作记录](../../Docs/Weapons/m16a2-empty-reload-charge-20260920.md)。最终换弹由 `M16RemovalMelee20260920` 覆盖，完整恢复顺序见[发布与恢复](../../Docs/Weapons/m16-publication-20260920.md)，不要单独重跑基础导入覆盖已认可的最终动作。
