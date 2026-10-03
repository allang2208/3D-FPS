# F6 开发面板 · 怪物生成页选项条字号统一（2026-09-21）

2026-09-21 用户反馈：F6「交互开发面板 → 怪物生成」页的选项条字体太小，要求按冷钢 UI 规则统一放大。按全局规则只做必要开发与构建，不运行游戏、不截图、不做视觉验收，由用户自行测试。

## 1. 目标与范围

- 入口不变：F6 → 页签「怪物生成」；怪物类型下拉、生成数量、前方距离、生成／清除按钮的数据与业务入口全部不变。
- 本次只改该页选项条与数值框的字体档位和控件规格，使其与本面板「基本调参」页的下拉、数值框、按钮同源；不改页面顺序、说明文案、怪物目录与生成算法。
- 对照依据：冷钢 UI 正式规则 §4 字号六档与 §5 标准操作高度、`Source/FPSGAME/UI/ColdSteelUIStyle.h`、同面板 `DevelopmentPanelTools.cpp` 的既有卡片控件规格。

## 2. 问题与现状

| 位置 | 原实现 | 问题 |
| --- | --- | --- |
| 怪物类型下拉条目（收起态与展开列表共用） | `GenerateMonsterOption` 10.5px | 低于六档最小 11px，是表外字号，明显小于同页 16px 标签 |
| 物品／技能下拉条目 | `GenerateListOption` 12px | 同类选项条用不同档位，页面之间不统一 |
| 生成数量／前方距离／生成物品数量数值框 | `StyleCount` `NumberFont(10.5)` | 同样是表外字号，且矮于同面板 36px 操作高度 |
| 怪物页三组控件 | 直接加入滚动区，自然高度 | 与「基本调参」页 36px 下拉／数值框不同高 |

## 3. 信息结构与布局

| 栏目 | 内容 | 宽屏／窄窗 | 固定或滚动 | 显示条件 |
| --- | --- | --- | --- | --- |
| 怪物类型 | 16px 标签 + 14px 下拉（全内容宽、36px 高） | 同一竖排；宽度随抽屉与滚动区变化 | 正文滚动 | 页签选中 |
| 生成数量 | 16px 标签 + 14px 数值框（同上规格） | 同上 | 正文滚动 | 页签选中 |
| 前方距离 · 米 | 16px 标签 + 14px 数值框（同上规格） | 同上 | 正文滚动 | 页签选中 |
| 结果说明／帮助 | 14px / 12px 文本（未改） | 同上 | 正文滚动 | 页签选中 |

- 控件宽度取同页满宽说明行的**实测内容宽度**，滚动条显隐、抽屉宽度变化和视口变化都不会挤压或裁切右端箭头。
- 高度取共享 `ColdSteelUI::ActionHeight`（36px），随 DPI 反算；页签、底部生成／清除与「返回游戏」仍固定在滚动区之外。

## 4. 主题与资源

| 元素 | 复用主题／组件 | 字体角色与字号档 | 资源来源 |
| --- | --- | --- | --- |
| 页签、生成／清除按钮 | `CreatePanelButton` + `ColdSteelUI::ButtonStyle` | Noto Sans SC 14px | 工程字体 |
| 怪物类型下拉 | `UComboBoxString` + `SizeBox(36px)` | Noto Sans SC 14px（条目与收起态同一控件） | 工程字体 |
| 数量／距离 | `USpinBox` + `SizeBox(36px)` | JetBrains Mono 14px，中文回退 Noto Sans SC | 工程字体 |
| 分区标签／正文／帮助 | `CreatePanelText` | 16 / 14 / 12px | 工程字体 |

不新增图片、字体或主题色；下拉的底色、描边、悬停态继续走 `ColdSteelUI::ButtonStyle`，数值框继续用 `Content` / `ButtonHover` / `Accent`。

## 5. 数据与动作（无变化）

| 操作 | 业务入口 | 范围与单位 | 保存 |
| --- | --- | --- | --- |
| 选择怪物 | `UDevelopmentSpawnComponent::GetMonsters()` 的 Id／显示名 | 目录顺序即下拉顺序 | 无写入 |
| 生成 | `SpawnInFront(Id, Count, DistanceMeters, Result)` | 1–10 只、前方 3–15 米 | 沿用原生成逻辑 |
| 清除 | `ClearSpawned()` | 只影响本面板生成的怪物 | 同上 |
| 生成物品数量框（同面板） | `AddItem(Definition, Count)` | 1–9999 | 原存档事务 |

## 6. 状态与输入（无变化）

- 目录为空时下拉禁用；无权限或无角色时生成按钮禁用；清除按钮仅在已生成怪物时可用 —— 判定入口未改动。
- 下拉展开／收起、数值框拖动与键盘输入、Tab／Caps／P 抽屉互斥与 F6 / Esc 关闭顺序保持原样；点击与焦点归属不变。
- 控件只在“实测尺寸与目标不一致”时写入宽高，避免每帧让布局失效；页面未显示（实测宽度为 0）时跳过，切到该页后下一帧自动对齐。

## 7. 文件范围与交付

- 修改：`Source/FPSGAME/UI/DevelopmentPanelWidget.cpp`（选项条与数值框字号、36px 规格、实测宽度对齐）、`Docs/UI/ui-cold-steel-design-system.md`（§4 补充选项条与数值框档位条款，版本 2.19）、`skills/ue5-ui-umg-slate/references/fpsgame-panels.md`（可复用经验）。
- 新增：本文。
- 不改：`DevelopmentPanelWidget.h`（不新增成员、不改反射数据）、物品／技能目录入口、怪物生成组件与存档结构；不使用新图片或字体。
- 必要构建：`FPSGAMEEditor Win64 Development`（`Tools/Build/Build-Editor.ps1`，该脚本要求先关闭 FPSGAME 编辑器）。
- 用户明确要求的预览／检查／测试：未要求，由用户测试；本轮未启动游戏、PIE、截图或验收渲染。

## 8. 构建与验证状态（2026-09-21）

- 单文件编译验证：`Build.bat FPSGAMEEditor Win64 Development -SingleFile=Source/FPSGAME/UI/DevelopmentPanelWidget.cpp -NoHotReload -WaitMutex`，结果 `Result: Succeeded`（`[1/1] Compile [x64] DevelopmentPanelWidget.cpp`，19.35 秒），日志 `Saved/Logs/DevPanelSpawnTypeCheck-20260921.log`。该模式只编译该翻译单元，不写 `UnrealEditor-FPSGAME.dll`，因此不影响正在运行的编辑器。
- 常规构建／链接尚未完成：本机现有两个 FPSGAME 编辑器进程（用户编辑器 PID 11592、另一会话的 `-game` 性能采样 PID 12676）占用模块 DLL，`Build-Editor.ps1` 的守卫要求先关闭 FPSGAME 编辑器再构建；本轮未停止任何进程，保留现场，由用户在关闭编辑器后构建或原地 Live Coding 热更。
- 本次改动不新增 `UPROPERTY`／成员变量、不增删 `UFUNCTION`，反射数据与类布局不变，属于 Live Coding 支持的函数体改动；若在编辑器内热更，需重新编译同一翻译单元后由 `NativeTick` 在切到「怪物生成」页的下一帧对齐选项条尺寸。
- 未测试项：面板实际外观、字号观感、下拉展开行高、36px 控件与窄视口下的表现、数值框拖动与生成／清除功能，均由用户实测确认。