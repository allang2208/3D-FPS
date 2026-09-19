# 改造面板稳定性表述统一

后续：用户已授权实际稳定性优化，生产配件百分比现统一指评分变化，详见 [实施记录](../gunplay-stability-implementation-20260913.md)。下文保留初次仅改文案时的范围说明。

用户要求统一稳定性相关表述，并只读对照 Godot 与 UE 的 gunplay 机制。此次制作仅改文案，机制差异和改善建议另见 `../gunplay-stability-review-20260913.md`。

- UI 为现有 UMG 宿主与 Slate 内容；保留左侧分类、中央模型、右侧选中配件效果和详细属性汇总，以及原背景、主题和响应布局。
- 主属性统一为“枪械稳定性”。详细分项使用“枪械稳定性·抖动指数”“枪械稳定性·回稳90%”，分别保留指数和毫秒，不能把负向幅度指数直接改名为正向评分。
- 配件卡片、说明、已选改造效果和装备详情使用同一术语。旧 `shake_mult` 效果表述为“枪械稳定性提高/降低（抖动幅度降低/增加 X%）”；`stability_mult` 保留评分提高百分比。此次不改变任一倍率或存档。
- 数据仍来自 `UGunsmithSystem::Calculate` 和原有 JSON 配件目录；主评分为 0–100 分，回稳值是开镜反馈弹簧的理论震荡包络时间，不等于瞄准点自动回正。
- `RefreshPresentation`、`BuildOption` 和装备详情的既有刷新入口继续使用；无需新的事件绑定、输入模式、焦点切换或生命周期清理。
- 保留 AutoWrapText、滚动和现有空态/未选/选中/应用/撤销/关闭行为，不改变显示区域或交互。
- 修改范围：`M4GunsmithOverview.cpp`、`ColdSteelItemTooltipData.cpp`、`Content/ColdSteelData/gunsmith.json`；构建为必要交付步骤。按用户要求进行源码对照检查，不启动游戏或进行运行测试。
