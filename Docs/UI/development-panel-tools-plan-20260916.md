# F6 开发面板 · 抽屉规格与开发功能（2026-09-16）

交付范围：F6「交互开发面板」改为与背包装备相同的右侧抽屉规格（同样的尺寸、弹出／收回动画、打开时的 HUD 让位规则），并在「基本调参」页加入建造不消耗资源、生成物品、提升等级、提升技能等级（含直接满级）四项开发功能。用户已授权实现；按 2026-09-12 全局规则不追加检查、测试或验收，由用户自行测试。

## 1. 目的与入口

- 入口不变：非 Shipping 构建中 F6 打开／关闭，左下角 `F6 开发面板` 按钮，Esc 与「返回游戏」按钮关闭。
- 面板仍是「天气环境 / 怪物生成 / 基本调参」三页，本次只改外壳规格与「基本调参」页内容。
- 保留天气页与怪物页的既有业务入口、参数与结果文案，不新增天气或怪物模拟。

## 2. 结构与信息层级

| 区域 | 内容 | 布局与滚动 |
| --- | --- | --- |
| 全屏压暗底 | 黑色 40% 遮罩，随抽屉进度淡入淡出，同时挡住世界点击 | 固定，位于面板之下 |
| 固定标题 | 交互开发面板、返回游戏 · F6 / Esc | 右侧抽屉顶部固定，内容独立滚动 |
| 固定页签 | 天气环境 / 怪物生成 / 基本调参 | 三等宽按钮，选中态用银白描边 |
| 天气环境 | 现有场景、时钟、雨量、预设、自动天气 | 正文滚动 |
| 怪物生成 | 现有类型、数量、距离、生成／清除 | 正文滚动，固定底部生成／清除 |
| 基本调参 · 会话开关 | 开关状态行 + 六项开关卡片 | 正文滚动 |
| 基本调参 · 开发功能 | 结果行 + 生成物品／提升等级／提升技能等级三张卡片 | 正文滚动 |
| 固定操作 | 全部关闭、返回游戏 | 始终可达，不被内容挤出窗口 |

开关卡片沿用现有「标题 + 说明 + 右侧开关」结构；开发功能卡片为「标题 + 说明（含实时状态） + 右侧控件区」。窄内容宽度时控件区整行下移，与现有开关卡片的一致处理相同。

## 3. 布局（与背包同一抽屉规格）

- 抽屉贴右边缘：`Anchors(1,0,1,1)`、`Alignment(1,0)`、`Offsets(-NavigationDrawerInset, 12, Width, 12)`，与 `UColdSteelHUDWidget::UpdateInventoryLayout` 完全同源；宽度 = `min(视口宽 − RightInset − 12, clamp(视口宽 × 0.48, 720, 1040))`，高度 = 视口高 − 24。
- 内容宽度不足时仍服从实际视口（`视口宽 − 12`），不整体缩放固定画布。
- 主体滚动、固定标题与固定底部操作；字号沿用 Noto Sans SC／JetBrains Mono 与 20／16／14／12px 档位，DPI 变化重算。
- 开发功能卡片的控件区在宽布局右对齐（物品下拉 320px、技能下拉 240px、按钮与数值框固定像素），窄布局下移并让下拉占满剩余宽度。

## 4. 动画（与背包同一规则）

- 进度 `DrawerProgress` 用 `FInterpConstantTo(..., 4.0/s)` 匀速逼近 0／1，与抽屉相同。
- 面板 `RenderTranslation.X = (1 − Progress) × 抽屉宽度`；全屏遮罩与玻璃模糊 `RenderOpacity = Progress`。
- 打开时立即显示面板与遮罩；关闭时保持可见直到进度归零再 `Collapsed`，因此收回过程与外框都不消失。
- 左下角 `F6 开发面板` 入口在抽屉出现期间（含收回动画）`Collapsed`。

## 5. 打开时的隐藏界面规则（与背包同一条件）

`UColdSteelHUDWidget::SetExternalDrawerOpen(true)` 打开外部抽屉标记，HUD 的三个让位条件统一为 `bInventoryOpen || DrawerProgress > KINDA_SMALL_NUMBER || bExternalDrawerOpen`：

| 让位对象 | 现状（背包） | 本次（开发面板） |
| --- | --- | --- |
| 右侧入口列（人物状态／背包／技能） | `Collapsed` | 同一标志，同样 `Collapsed` |
| 世界时钟 | `Collapsed` | 同一标志，同样 `Collapsed` |
| 右下角武器详情（弹药栏） | `Collapsed` | 同一标志，同样 `Collapsed` |

开发面板关闭、收回动画播完后标记复位，三个对象按各自原有规则恢复。输入模式同样使用 UIOnly + 鼠标光标 + 移动／视角锁定 + `SuspendWeaponForMenu`，关闭恢复 GameOnly；关闭不放行世界攻击。

面板在视口 `ZOrder 30`（HUD 20 之上），使遮罩与玻璃覆盖 HUD 常规元素，与背包打开时的观感一致；枪械改造／强化面板（60）与拖影浮层（1000）仍在其上，打开 F6 前控制器已关闭这些面板。

## 6. 数据合同与业务入口

| 功能 | 数据来源 | 业务入口 | 语义 |
| --- | --- | --- | --- |
| 建造不消耗资源 | `UDevelopmentTuningSubsystem` 新开关 `FreeBuilding` | `UVoxelBuildComponent::ConsumePlacementBlocks`／`RefundPlacementBlocks` 读取开关 | 放置体素块时不扣背包／仓库体块；失败也不退回；拆除回收按原规则发放 |
| 生成物品 | `UColdSteelStatusModel::ItemCatalog()`（`Content/ColdSteelData/items.json` 实际加载内容） | `AddItem(Definition, Count)` | 按类别归纳的下拉：武器／弹药／消耗品／材料／建材／强化材料／祭品／货币；同类别连续排列，条目文案为「类别 · 名称」；数量 1–9999 默认 1；放不下时显示模型原因 |
| 提升等级 | `Level`／`Points`／经验门槛公式（与 `GainExperience`、`AwardKill` 同式） | `GrantLevel(1)` | 等级 +1，按正常升级发放 3 点属性点，经验夹到当前等级门槛以下以满足存档校验；升级提示由既有 `QueueProgressNotices` 发布 |
| 提升技能等级 | `SkillCatalog()` 的 12 项存档技能（名称与满级取 `DevelopmentSkillDefinition`，等级取 `MasteryProgress`） | `RaiseSkillLevel(Id, 1)` | 提升 1 级，不超过 20 级；满级清零修炼值 |
| 提升至满级 | 同上 | `MaxSkillLevel(Id)` | 直接置为 `MaxLevel` 并把修炼值清零；已满级时不重复提交 |

全部动作走 `SyncRuntime → Snapshot → CommitState` 的原有事务（校验、双槽写入、校验和、发布），控件不自行改写存档；不可写入（非单机、无角色）时按钮禁用并显示原因。

## 7. 状态与输入

- 空目录（物品目录未加载）时下拉禁用并显示「物品目录未加载」；无技能或已满级时按钮禁用并显示原因。
- 动作结果统一显示在开发功能区的结果行：成功用 `Success`，失败与不可用状态用 `Warning`。
- 技能行的实时说明显示「当前：名称 Lv.N / 20 · 修炼值 M」，等级行显示「当前等级 Lv.N · 属性点 P · 经验 E / 门槛」。
- 开关、按钮、下拉与数值框沿用共享按钮样式与焦点；打开 F6 后焦点落在「返回游戏」，Tab／Caps／P 的抽屉互斥顺序不变。

## 8. 文件与资源范围

- 修改：`DevelopmentPanelWidget.h/.cpp`（抽屉结构、尺寸、动画）、`DevelopmentTuningPanel.cpp`（开关行与页面结构）、`WeatherControlWidget.cpp`（打开时的输入模式与背包一致）、`FPSGAMEPlayerController.cpp`（面板 ZOrder、HUD 访问入口）、`ColdSteelHUDWidget.h/.cpp`（外部抽屉让位标志）、`ColdSteelPanelNavigation.cpp`（让位条件合并）、`DevelopmentTuningSubsystem.h/.cpp`（`FreeBuilding`）、`VoxelBuildComponent.cpp`（建造扣料闸门）、`ColdSteelInventoryTypes.h`（目录条目结构）、`ColdSteelStatusModel.h`。
- 新增：`Source/FPSGAME/UI/DevelopmentPanelTools.cpp`（开发功能卡片、目录、动效与让位）、`Source/FPSGAME/Development/ColdSteelDevelopmentTools.cpp`（等级／技能／目录模型入口）、本文。
- 不使用新图片、字体或付费资源；不改变物品占格、存档结构、技能成长配置与战斗公式。

## 9. 交付状态

按用户规则执行开发、接入与必要构建，不运行游戏、不截图、不做视觉或回归验收；面板实际外观、动画节奏、下拉可用性与四项功能效果由用户测试。

## 10. 构建记录

- `FPSGAMEEditor Win64 Development`（带 `-ModuleWithSuffix=FPSGAME,9162259`，用户编辑器当时正在运行）→ `Result: Succeeded`，日志 `Saved/BuildEditor/devpanel-build-3.log`；期间修正两处自身编译问题：`DevelopmentPanelTools.cpp` 局部变量遮挡 `UWidget::Slot`（C4458）、`NativeDestruct` 在 `DevelopmentPanelWidget.cpp` 与 `DevelopmentTuningPanel.cpp` 重复定义（LNK2005）。
- 用户关闭编辑器后按流程重跑 `Tools/Build/Build-Editor.ps1` → `Result: Succeeded`，产物 `Binaries/Win64/UnrealEditor-FPSGAME.dll`，日志 `Saved/BuildEditor/build-20260916-230814.log`。中间一次失败来自并行会话正在编辑的 `RuneSwordComponent.cpp`（`BeginOverhead` 尚未定义），不属于本次改动，随后自动恢复。
- 自查中发现并修正一处会直接显示错误的问题：`MasteryDefinition` 只覆盖武器精通，火球／冰锥／暴击／闪避／巧手会回退成步枪定义；新增 `DevelopmentSkillDefinition` 按技能自身返回名称与满级后重跑构建 → `Result: Succeeded`，日志 `Saved/BuildEditor/build-20260916-230858.log`。
- 构建成功只代表编译链接结果；本轮未启动游戏、未截图、未执行 UI 或功能测试。
