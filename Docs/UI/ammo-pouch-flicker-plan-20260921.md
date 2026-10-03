# 弹药袋面板无操作闪动：原因与修复（2026-09-21）

入口：装备与背包抽屉的「弹药袋」页（`SetInventoryPage(3)` → `UColdSteelAmmoPouchWidget`）。面板合同见 [动态弹种轮盘与弹药袋](../../skills/ue5-ui-umg-slate/references/ammo-radial-and-pouch.md)，主题见 [冷钢 UI 正式规则](ui-cold-steel-design-system.md)。

## 目标与交付阶段

- 用户反馈：弹药袋界面里面板会莫名其妙闪动（没有操作也会闪）。
- 目标：找出周期性闪动的触发链并消除，不改变面板的信息结构、主题与交互。
- 阶段：游戏接入中的缺陷修复。预览与测试未要求，由用户实测。

## 原因分析（代码证据链）

| 步骤 | 位置 | 事实 |
| --- | --- | --- |
| 1 | `ColdSteelAmmoPouchWidget.cpp:23` | `Refresh()` 绑定在 `Model->OnChanged` 上 |
| 2 | `ColdSteelAmmoPouchWidget.cpp:40` | `Refresh()` 先 `Surface->ClearChildren()`，再整页重建，包括 `SAssignNew(List,SScrollBox)`、全部 `SButton`、图标 `SImage` 与样式 |
| 3 | `ColdSteelProfileRuntime.cpp:157` | 每次成功存档的 `PersistState` 末尾 `OnChanged.Broadcast()` |
| 4 | `ColdSteelProfileRuntime.cpp:412`（旧） | `TickRuntime` 每帧累计：`SaveAccumulator>=5 → SaveNow()`，**无条件每 5 秒**。2026-09-21 起改为 `fps.Save.AutosaveSeconds`（默认 300 秒）且只在有待写盘增量时写，见 [自动存档周期与写盘开销](autosave-policy-20260921.md) |
| 5 | `ColdSteelProfileRuntime.cpp:411`（旧） | 训练经验待写盘时 `TrainingFlushAccumulator>=1 → SaveNow()`，战斗中最快每 1 秒。该分支已随同一次改动删除 |
| 6 | `ColdSteelProfileRuntime.cpp:243-248` | `SaveNow()` 走完整带校验事务：`SyncRuntime` → 写盘 → 回读校验，并广播 `OnChanged` |

结论：**面板打开时每约 5 秒（训练中约 1 秒）被无内容变化地整树重建一次**。旧控件全部销毁重建，于是

- 行的悬停／按下态随旧 `SButton` 一起丢失（要等下一次鼠标移动才恢复），
- `SScrollBox`、图标与样式全部重建，同帧还叠着一次同步存盘卡顿，
- 观感就是面板在无操作时“闪一下”。

进一步证据：抽屉打开时 `SetInventoryOpen(true)` 会 `PC->SetIgnoreMoveInput(true)`、`SetIgnoreLookInput(true)` 并显示鼠标（`ColdSteelHUDWidget.cpp:1101-1118`），玩家无法移动、射击或拾取，所以**面板打开期间弹药数量等显示内容根本不会变**——这些重建全部是多余的。项目内已有同类教训：[状态效果 HUD](../../skills/ue5-ui-umg-slate/references/fpsgame-status-effects.md)「Effect Type 不变时复用卡片，避免重建造成悬停闪烁」。

## 修复合同

| 项 | 修正后行为 |
| --- | --- |
| 触发 | `Refresh()` 先采集“视图模型”（标题行、分组、每行文本／颜色／可用性、图标、占位与底部按钮状态），由同一份数据生成**内容键** |
| 重建条件 | 内容键或 DPI 比例变化，或控件树为空时才重建；否则直接返回 |
| 内容不变 | 不触碰任何控件：悬停／按下态、滚动位置、图标与样式保持 |
| 内容变化 | 仍走原来的整页重建（并把滚动位置还原），显示值不会滞后 |
| 结构 | 页面层级、间距、字号、颜色、按钮与文案全部保持原样 |
| 状态成员 | 只新增一个 `uint32` 内容键成员（POD，热补丁复用旧实例时最多多重建一次，不会读到野指针） |

内容键覆盖所有会改变画面的输入：DPI 比例、当前武器实例与名称、已装填数与弹种标签、展开分组集合、分组顺序与总数、每个可见弹种的 id／名称／等级名／等级色／可用标记／数量／当前装填／待切换／兼容性／效果摘要／描述／图标是否存在、以及底部按钮的可用状态。

## 数据与动作

不涉及存档结构、数量扣除与保存时机；`OnChanged`、`SaveNow`、`RequestAmmoChange`、`StartAmmoSwitch` 全部保持原样。本次只改绘制层是否重建。

## 状态与输入

| 状态 | 行为 |
| --- | --- |
| 无弹药 | 仍显示「尚未获得弹药，获得后会自动收纳」占位 |
| 展开／收起分组 | 结构变化 → 重建（用户操作引发，属预期） |
| 选择弹种（待切换） | 内容键变化 → 重建，底部按钮随 `Selected` 可用 |
| 未装备兼容枪械／已用尽／暂不可用 | 文案与禁用状态不变 |
| 打开／关闭抽屉 | 仍由 `SetInventoryPage` 控制可见性，未改 |
| 窗口缩放改变 DPI | `NativeTick` 检测到比例变化 → 重建一次 |

## 文件范围与交付

- 本文件与 [长按 R 弹种轮盘灵敏度修正](ammo-wheel-sensitivity-plan-20260921.md)、[弹药袋卡片格式：右侧数量不换行](ammo-pouch-row-layout-20260921.md)。
- 源码：`Source/FPSGAME/UI/ColdSteelAmmoPouchWidget.cpp`（视图采集＋内容键＋重建拆分）、`ColdSteelAmmoPouchWidget.h`（一个 `uint32` 成员）。
- 复用资源：无新增资源。
- 必要构建：`FPSGAMEEditor Win64 Development`。
- 用户明确要求的预览／检查／测试：未要求，由用户测试。
- 完成后记录实际完成项与未测试项。

## 实施记录（2026-09-21）

- `ColdSteelAmmoPouchWidget.cpp`：拆成三段——`CollectPouchView()`（按模型采集视图模型并同时生成内容键）、`BuildPage()`（原重建主体，改从视图模型取值，行为、文案、间距、字号、颜色全部保持）、`Refresh()`（状态迁移 → 采集 → 键比较 → 需要时才重建）。
- `ColdSteelAmmoPouchWidget.h`：新增视图模型的前置声明、两个私有方法声明，以及一个 `uint32 ContentKey`（POD，热补丁复用旧实例时最多多重建一次，不会读到野指针）。
- 内容键包含：DPI 比例、当前武器名称与已装填读数、展开分组集合（排序后写入，避免 `TSet` 顺序影响键）、分组顺序／名称／总数、每行的 id／数量／当前装填／待切换／可用／状态文案／标题／效果摘要／等级色／图标有无／描述、以及底部按钮可用状态。
- 结果：自动存档与训练写盘引起的 `OnChanged` 只要显示内容没变就**不再重建**；抽屉打开期间玩家移动／视角被屏蔽，弹药数量等显示内容本就不可能变化，因此面板打开时不会再出现无操作闪动。展开／收起、选择弹种、换枪、DPI 变化仍会重建一次。
- 同日后续：写盘频率本身也降下来了（`fps.Save.AutosaveSeconds` 默认 300 秒，且只在有待写盘增量时写），广播次数随之从"每 5 秒"变为"每 5 分钟一次增量写盘"。两条修复互相独立，面板侧的键守卫在旧频率下也已生效。见 [自动存档周期与写盘开销](autosave-policy-20260921.md)。
- 编译：单文件编译 `ColdSteelAmmoPouchWidget.cpp` 通过（UHT 同步重生成 4 个生成文件，无警告转错误）；随后常规构建 `Tools/Build/Build-Editor.ps1`（`FPSGAMEEditor Win64 Development`）`Result: Succeeded`，已重新链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（23:45:28），日志 `Saved/BuildEditor/build-20260921-234512.log`。
- 未测试：打开弹药袋静置观察是否仍有闪动、悬停／按下态是否稳定、展开与选择后的数值是否即时更新，均由用户实测。