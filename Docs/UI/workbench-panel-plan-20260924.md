# 工作台制作面板规划（2026-09-24）

> 按 [面板与栏目工作流](../../UI-WORKFLOW.md) 与 [冷钢 UI 正式规则](ui-cold-steel-design-system.md) 编写。
> 需求原话：**参考现在冶炼系统的冶炼栏＋冶炼升级栏，给工作台交互设计一款工作台制作栏＋升级栏；
> 格式大小完全复刻，制作内容先空着后续设计。**

## 1. 目的与范围

- 为已接入的建造工作台（`DA_VoxelBuildPalette` 构件 `workbench_table`，案例
  `SourceAssets/WorkbenchBuildable20260924`）增加 E 交互：准星瞄准工作台按 **E** → 打开**背包**
  并在抽屉左侧弹出**工作台制作面板**（与高炉→冶炼面板同一开合模型）。
- 面板外壳、尺寸、贴边、滑入/骑乘动画、左缘「升级」页签与升级弹层（同尺寸、右缘钉缝横向展开）
  **全部复刻** `UColdSteelSmeltingWidget` 及其 HUD 集成（`Docs/UI/smelting-panel-plan-20260923.md` §3/§7.7/§7.11/§7.12）。
  **2026-09-24 晚间同步**：随高炉面板演进补齐 v10（弹层三页签卡＋下方详情带，代理与行缓存分家）、
  v11（页签跟缝展开：收起压缝 2px、展开随弹层左缘同曲线推到最左、文案换竖排"收回"＝点击关闭）、
  v11c（两字逐行居中）、0.1s 数据节流与每帧动画解耦；冶炼专属件（进度条/火星/批量行）不引入。
- **本次只做外壳与占位内容**：制作列表区显示空态「制作内容后续设计」，开始按钮禁用；
  升级弹层为同构占位（三占位页签可切换、详情带读数位全为「后续设计」、升级钮禁用）。
  配方、数值、升级轴、燃料类业务一概不引入。
- 与冶炼面板**共用同一贴位**（背包抽屉左缘），因此**互斥**：开一个瞬收另一个（两面板同槽重叠不可见）。

## 2. 信息结构（与冶炼面板逐层对齐）

| 层 | 冶炼面板 | 工作台制作面板（本次） |
| --- | --- | --- |
| 头部 | 「冶炼」20px Medium ＋ × | 「制作」20px Medium ＋ ×（同控件同规格） |
| 状态卡 | 炉况卡（图标+标题+明细+进度+取出） | 工作台卡（图标位预留+「工作台空闲」+「制作配方与流程后续设计」），无进度条/按钮（属内容） |
| 列表区 | 分区标题「可冶炼矿石」+ 滚动行卡 + 空态行 | 分区标题「可制作项目」+ 滚动区 + 空态行「制作内容后续设计，敬请期待」 |
| 主操作 | 整宽「开始冶炼」 | 整宽「开始制作」（禁用） |
| 状态行 | 12px 反馈行 | 同款（暂无动作，恒空） |
| 页脚 | 快捷键/语义说明 | 「Esc 或 × 关闭 · 制作配方与升级内容后续设计」 |
| 升级页签 | 左缘 36×60 竖排「升/级」居中；收起压缝 2px，展开随弹层左缘跟缝、文案换「收/回」（v11/v11c） | 同款同构建 |
| 升级弹层 | 与面板同尺寸镜像位，HeaderTint 头部＋×＋三轴页签卡（整行可点，选中 Medium＋Accent 细边）＋下方详情带（轴名 16/等级 12/细线分区/效果 16 NumberFont/材料行/升级钮）＋垫底说明 | 同结构同动画；页签为「升级轴一/二/三」占位、Lv「Lv.—」、效果「效果数值后续设计」、材料行收起、升级钮禁用——升级轴上线时只替换轴名表与 RefreshUpgrade 三处读数 |

不随复刻引入的冶炼专属件：燃料卡、火星粒子、批量步进行、炉况视觉区、进度条动效（B1–B4）——
它们是冶炼业务内容而非面板格式。

## 3. 布局与尺寸（全部沿用冶炼公式，单一来源不复制常量）

- 宽＝`InventoryWidth/2`、高＝背包一致（画布锚右缘＋上下 12px）；背包开＝贴抽屉左缘零缝
  （`Dock=Width`），背包关＝贴视口右缘 12px；<240px 整块收起。
- 槽位＝屏幕左缘→面板右缘全宽命中区（页签/弹层正坐标重排，坐标源＝主题层推送
  `SetPanelScreenX`，Slate 缓存几何不可反推——冶炼 §7.7 教训直接继承）。
- 动画：弹出＝抽屉到位后面板自抽屉左缘滑出（`WorkbenchMotion` 4.0/s＋`EaseSmooth`，Z 序 40→42）；
  关闭＝与背包刚体骑乘同曲线向右缩回（`bWorkbenchRiding`，抽屉行程加长 `WorkbenchSlidePx`）；
  升级弹层＝右缘钉缝横向缩放 0→1 展开/收回（枢轴右中，同款 4.0/s）。
- 本体/根画布 `SelfHitTestInvisible`（`HitTestInvisible` 连子树屏蔽命中——冶炼 §7.8 教训）。

## 4. 视觉（冷钢正式规则，全部取自 `ColdSteelUIStyle` 单一来源）

玻璃底 `GlassTint`/回退 `GlassFallback`、模糊 9/21、头部 `HeaderTint`、卡片 `StatusCard` 8px、
轨道 `Content`、描边 `Border`、按钮四态 `ButtonStyle(Scale)`、字体 Noto Sans SC／JetBrains Mono、
档位 20/16/14/12、正文一律 `SetAutoWrapText(true)`、滚动条 6px、留白 16px 归属 `UpdateScale` 统一重算。

## 5. 数据合同（本次＝零业务）

- 上下文：`SetWorkbench(AVoxelBuildWorld*, FIntVector Cell)`（E 交互写入，同 `SetFurnace`）；
  面板开着期间构件被拆/脱落 → HUD Tick 有效性校验瞬关（同冶炼）。
- 不新增存档字段、不新增 JSON、不接 `StatusModel`/子系统；「开始制作」`SetIsEnabled(false)`。
- 后续设计配方时：列表行卡结构、代理点击（工程先例 `UColdSteelSmeltingRowProxy`）、
  报价/扣除/结算走业务系统，面板只做展示与转发（UI-WORKFLOW §5）。

## 6. 状态与输入

- 打开：E（准星命中 `workbench_table` 且非落体件）→ 背包＋面板同开；开面板瞬收冶炼面板。
- 关闭：Esc／顶栏 ×（只收面板保留背包）；关背包连带瞬收面板（骑乘动画）；换工作台＝重设上下文。
- 升级页签：点击左向展开弹层，再点/× 收回；无工作台上下文时页签隐藏。
- 空态：列表区恒显示空态行（后续配方上线时按冶炼口径替换）。

## 7. 文件与资源范围

- 新增：`Source/FPSGAME/UI/ColdSteelWorkbenchWidget.h/.cpp`、`ColdSteelWorkbenchHUD.cpp`。
- 修改：`ColdSteelHUDWidget.h/.cpp`（成员/Tick/Esc/连带/构建调用）、`ColdSteelInventoryTheme.cpp`
  （布局推送）、`ColdSteelWorldInteraction.h/.cpp`（`IsWorkbench`/`WorkbenchPrompt`）、
  `ColdSteelCrosshair.cpp`（准星小卡）、`FPSGAMEPlayerController.cpp`（E 分派，高炉判定之后）、
  `Building/VoxelBuildTypes.h`（`VoxelWorkbenchId`）、`ColdSteelSmeltingHUD.cpp`（互斥瞬收）。
- 无 Content 资产改动；无退役文件。

## 8. 交付

- 构建：`Build.bat FPSGAMEEditor Win64 Development`（含新 UCLASS，需全量编译；编辑器未运行时后台构建）。
- 不运行 PIE、不截图（用户规则）；实机放置 `工作台` 构件按 E 验证交由用户。
