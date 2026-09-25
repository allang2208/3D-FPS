# 弓资源栏与物品参数（2026-09-25）

目标：让独立弓类显示自身资源和动作参数，复用现有 `ColdSteelAmmoReadout`、物品 Tooltip、强化比较栏；阶段为游戏源码接入，未要求预览／测试。

## 布局和主题

沿用现有武器资源栏的位置、宽窄屏约束、字体与玻璃主题；不新增窗口、焦点或 Tick。行序为武器名、箭种／搭箭状态、拉距／箭袋。双持副栏隐藏。数字复用原弹药主副数字控件；沿用 `ColdSteelUI` 的 TextPrimary、TextSecondary、Accent、Warning。

物品 Tooltip 沿用正文卡片与摘要／比较容器，加入“弓箭参数”；弓为竖长形状，保持原非宽图标布局。强化栏仍使用现有前后数值表；弓按武器上限强化，枪械卷轴兼容规则不扩展。

## 数据和状态

| 内容 | 事实源和公式 | 更新／写入 |
| --- | --- | --- |
| 武器名、当前箭种 | 当前库存实例；`AmmoDefinitionFor` 读取 `arrow_ammo` | 现有 Refresh，只读 |
| 已搭箭／未搭箭 | `UBowWeaponComponent::HasArrowNocked()` | 现有 Refresh，只读 |
| 拉距 | 同一组件的 `DrawFraction()*100` | 已有 HUD 调度，拉弓时 Accent |
| 箭袋 | Profile `PouchCount(ArrowDefinition)`，开启该箭种无限备弹时 ∞ | 空箭袋 Warning；成功发射才扣除 |
| 满拉武器伤害 | `ColdSteelWeaponStats::DamageParts`；强化、角色与弓术同发射快照 | Tooltip／强化比较沿用原刷新；明示不计箭种、暴击和目标防御 |
| 拉满耗时 | `max(0.3, Interval(Item, Model, draw_seconds))` | 与开始拉弓的计算一致 |
| 搭箭、箭速、飞行距离 | `nock_seconds`、`full_speed_cm/100`、`range_cm/100` | 单位 s、m/s、m |

菜单开启沿用资源栏 Collapsed；非菜单为 HitTestInvisible；切换枪械／近战／工具走原分支。没有独立输入绑定或拖放事件；缺箭／体力不足仍用短时 PickupPrompt 提示。旧弓的弹匣／备弹归零是库存迁移，不由 HUD 修改。

涉及源码：`UI/ColdSteelAmmoReadout.cpp`、`ColdSteelItemTooltipSummary.cpp`、`ColdSteelItemTooltipData.cpp`、`ColdSteelEnhancementWidget.cpp`。必要常规 Editor 模块构建已完成；未运行 UI／游戏测试，由用户测试。
