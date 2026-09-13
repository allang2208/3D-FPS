# M1911 轻型快速扳机

2026-09-13：按用户要求增加仅影响数值的 M1911 扳机改造件，并制作枪匠配件图标。

- 武器：`ue_m1911`；槽位：`trigger`；选项：`m1911_lightweight_fast`。
- 唯一数值：`fire_interval_mult: 0.75`。基础射击间隔由 0.18 秒变为 0.135 秒；角色攻速与附魔倍率继续按原系统计算。半自动输入方式不变。
- 原厂选项 `false`（标准扳机）移除该倍率。使用现有枪匠草稿、应用并保存、武器实例 `gunsmith_parts` 数据流。
- 目录接入：`Content/ColdSteelData/gunsmith.json` 的 M1911 条目，不添加全枪型通用扳机。
- 图标运行路径：`Content/ColdSteelData/AttachmentIcons20260913/trigger_m1911_lightweight_fast.png`。现有 `UM4GunsmithWidget::BuildOption` 按 `槽位_选项ID.png` 加载；`FPSGAME.Build.cs` 已将整个 `Content/ColdSteelData` 作为 UFS 运行依赖纳入打包。
- `trigger_m1911_lightweight_fast.png` 为内置 imagegen 生成的二维 UI 图标，原样复制、保留生成图片的 alpha；提示词见 `prompt.txt`。不使用外部素材包，不宣称其属于公共领域。此图不是模型材质贴图或建模图纸。
- 本轮无模型、骨架、动画、枪身材质或 C++ 修改，无需原生编译。重新开始游戏会话加载目录后，在 M1911 枪匠的“扳机”中选择“轻型快速扳机”，点击“应用并保存”。

按用户规则未主动进行测试、游戏运行、截图或验收，由用户测试。
