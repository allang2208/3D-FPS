# 图鉴栏系统规划（武器 · 怪物）

依据 [面板与栏目工作流](../../UI-WORKFLOW.md) 与 [冷钢 UI 正式规则](ui-cold-steel-design-system.md) v2.19 编写。
参考原项目 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev` 的 `src/ui/codex-manager.js` 与 `src/ui/codex-formula-helper.js`
（原图鉴为「装备 / 怪物 / 友军」三分区 + 卡片网格 + 详情面板）。

## 目标与交付阶段

- 名称、入口、解决的操作需求：**图鉴**。入口为右侧持久栏目「图鉴」（快捷键 `K`），复用背包装备同一右侧抽屉；
  满足玩家查阅已实装武器与怪物的完整档案（数值口径、机制说明、来源）的需求。
- 范围与用户已确定的内容：本轮为**游戏接入**。分区为「武器」「怪物」两类；武器数据来自现有物品目录
  （`UColdSteelStatusModel::ItemCatalog()` 与物品 `Data` JSON），怪物数据来自
  `UDevelopmentSpawnComponent::GetMonsters()` 与 `MonsterCoreStats`（原 `enemy-config.json` 口径）。
  不做原项目的「友军」分区（UE 无仓鼠部队系统）。
- 阶段：游戏接入（源码 + 必要编译）。
- 对照的现有面板、实际源码与规范版本：
  - 右侧栏目入口：`Source/FPSGAME/UI/ColdSteelPanelNavigation.cpp`
  - 抽屉宿主与页面切换：`Source/FPSGAME/UI/ColdSteelHUDWidget.cpp`（`SetInventoryPage`）
  - 最接近的自包含抽屉页：`Source/FPSGAME/UI/ColdSteelSkillPage.h/.cpp`
  - 数据：`ColdSteelStatusModel.h`（`ItemCatalog`/`Items`/`CreateItem`）、`MonsterCoreStats.h`、
    `DevelopmentSpawnComponent.h`
  - 规范：冷钢 UI 正式规则 v2.19、`Source/FPSGAME/UI/ColdSteelUIStyle.h`

## 信息结构与布局

面板 → 页签 → 栏目 → 卡片／数据行。

| 栏目 | 内容与优先级 | 宽屏位置 | 窄窗／矮窗位置 | 固定或滚动 | 显示条件 |
| --- | --- | --- | --- | --- | --- |
| 标题栏 | 「图鉴」 | 抽屉内顶部 | 同宽屏 | 固定 | 常显 |
| 主分区页签 | 武器／怪物 | 标题下方整行均分 | 同宽屏 | 固定 | 常显 |
| 分类页签 | 武器：全部／枪械／近战／生产工具；怪物：全部／品阶 | 分区页签下方 | 横向滚动 | 固定 | 常显 |
| 卡片网格 | 图标、名称、类别／品阶、战力等级 | 详情左侧，≥ 720px 时两列 | < 720px 时详情改为上下重排（网格在上） | 网格独立滚动 | 常显 |
| 详情栏 | 名称、来源、数值分组、机制说明 | 详情右侧 42% | 窄窗在网格下方，最小 420px 高 | 详情独立滚动 | 已选择条目 |
| 页脚 | 快捷键与操作提示 | 抽屉底部 | 同宽屏 | 固定 | 常显 |
| 空态 | 「此分类暂无档案」 | 网格区 | 同宽屏 | — | 列表为空 |

- 实际内容区断点、左右边界与中缝：抽屉沿用既有规格（视口 48%、720–1040px、不超过视口宽 − 12px，贴右缘、外沿 12px）。
  网格与详情中缝 12px；内容宽 < 720px 时纵排，详情最小 420px 高，外层整体滚动。
- 标题／页签／确认／页脚的固定方式：标题栏、两组页签、页脚固定；网格与详情各自滚动。
- 长名称、多项目、空列表和溢出内容的处理：名称允许换行，不缩小字号；空列表显示明确的空态文案。

## 主题与资源

| 元素 | 复用主题／组件 | 字体角色与字号档 | 资源来源及加载位置 |
| --- | --- | --- | --- |
| 外壳／分区卡片 | `GlassTint`；分区卡 `StatusCard`，圆角 `CardRadius` 8px | — | 抽屉沿用宿主的 `UBackgroundBlur`（强度 9、半径 21）；卡片不再叠加模糊 |
| 标题／正文／数值 | `TextPrimary`/`TextSecondary`/`TextTertiary` | 标题 20、分区标题 16、正文与数值 14、辅助 12 | 工程字体 `Content/UI/GunsmithWorkbench/Fonts/` |
| 同级按钮／主要操作 | 共享 `ColdSteelUI::ButtonStyle`；页签等宽等高，高 `ActionHeight` 36px、间距 `ActionGap` 4px | 14px | 共享主题 |
| 图标 | 武器沿用 `UColdSteelWeaponIcons` 目录图与动态图标；怪物暂用中性占位 | — | 缺失／等待显示中性占位，不伪造图标 |
| 稀有度／语义色 | `ColdSteelUI::RarityColor`；收益 `Success`、代价 `Danger`、中性 `TextTertiary` | 14px | 共享主题 |

## 数据与动作

| 字段或操作 | 模型／业务入口 | 来源范围与过滤 | 单位／排序／公式 | 更新触发 | 确认、扣除与保存 |
| --- | --- | --- | --- | --- | --- |
| 武器目录 | `UColdSteelStatusModel::ItemCatalog()` | `Definitions` 中非弹药条目 | 按 `GroupOrder` 再按名称；类别索引复用 `Group` | 目录构建一次并缓存（`bItemCatalogBuilt`） | 只读，无写入 |
| 武器数值 | 物品 `Data` JSON（`ColdSteelInventory::Text/Number/Flag`） | 同目录条目 | 伤害、射速、弹匣、射程、换弹等沿用展示口径 | 选择条目时读取 | 只读 |
| 武器来源 | `UColdSteelStatusModel::Items()` | 全部持有实例（背包／装备／仓库） | 计数与已装备位置 | 打开面板时统计 | 只读 |
| 怪物目录 | `UDevelopmentSpawnComponent::GetMonsters()` | 已注册的 9 个身份 | 按品阶再按名称 | 打开面板时读取 | 只读 |
| 怪物六维与战力 | `MonsterCoreStats::Get` / `CombatLevel` | 与运行时同一入口 | 力量/敏捷/智力/体质/精神/幸运；战力由 `CombatLevel(S,MaxHp,Speed)` 派生 | 选择条目时求值 | 只读 |
| 怪物品阶与奖励倍率 | `MonsterCoreStats::RankExperienceMultiplier/GoldMultiplier/RankCombatBonus` | 同入口 | 经验 ×、金币 ×、战力加值 | 同上 | 只读 |

列表、默认选择、显示数量与实际内容使用同一范围。本面板为**只读档案**，不改变任何存档字段、容量或战斗公式。

## 状态与输入

| 状态／触发 | 显示、隐藏或禁用 | 原因文案／反馈 | 选择、焦点、滚动与确认行为 |
| --- | --- | --- | --- |
| 无数据／未选择 | 网格显示空态；详情显示「从左侧选择条目查看档案」 | 空态文案 | 详情区不可点击 |
| 已选择 | 卡片显示银白选中边；详情填充 | — | 点击卡片切换选择，详情滚动位置复位 |
| 分类切换 | 网格按新分类重建 | — | 无效分类回退「全部」；保持当前分区 |
| 图标等待／失败 | 中性占位 | — | 就绪只刷新图片，不重建卡片 |
| 打开／关闭 | 抽屉滑出收起；K 或点击当前入口收起 | — | 关闭归还焦点，不穿透世界攻击 |

- 键鼠入口、快捷键、Tooltip 限位、返回游戏与阻止关闭穿透：`N` 打开／收起图鉴；`Tab` 关闭任意已打开抽屉；
  复用宿主现有输入与 `CloseButton` 焦点归还路径，不新增输入模式。
- Construct／Destruct 绑定与释放、数据刷新和布局更新责任：宿主 `SetInventoryPage` 管理可见性；
  页面在 `RebuildWidget` 构建，`NativeTick` 只做必要的几何档位判断，`ReleaseSlateResources` 释放 Slate 引用与贴图。

## 文件范围与交付

- 本次修改文件、复用资源、新增资源及来源／许可：
  - 新增 `Source/FPSGAME/UI/ColdSteelCodexPage.h/.cpp`（图鉴页）
  - 修改 `Source/FPSGAME/UI/ColdSteelHUDWidget.h/.cpp`（宿主接入第 4 页、`bCodexTabActive`、快捷键 `N`）
  - 修改 `Source/FPSGAME/UI/ColdSteelPanelNavigation.cpp`（右侧新增第 4 个入口，布局按 4 项重算）
  - 修改 `Source/FPSGAME/UI/ColdSteelInventoryTheme.cpp`（把抽屉宽度同步给图鉴页）
  - 修改 `Docs/UI/ui-cold-steel-design-system.md`（新增第 17 节，版本 2.20）
  - 新增本规划文档
  - 无新增美术资源；武器图标位置暂以文字名呈现，怪物使用文字名与品阶，均不使用占位图。
- 确认退役的文件、保留替代物、trash 目录及归档清单：无退役文件。
- 需要的必要构建：`FPSGAMEEditor Win64 Development`。
- 用户明确要求的预览／检查／测试及交付文件：**未要求，由用户测试**。

## 实施记录（2026-09-24）

- 快捷键由 `K` 改为 **`N`**：`K`／`J` 已分别由 `FPSGAMEPlayerController` 绑定给强化台与改造台并在 `HandlePanelShortcut` 之前消费，`C` 是滑铲（`DefaultInput.ini` 的 `Slide`）；`N` 在输入映射与源码中均未被占用。
- 怪物分类由原项目的「家族（family）」改为**品阶**：本工程怪物身份未登记家族信息，品阶（`EMonsterRank`）是唯一已存的可靠维度。
- 未做原项目的「友军」分区：UE 无仓鼠部队系统。
- 武器图标：本次以名称与类别文字呈现（原项目的贴图/spritesheet 管线在 UE 侧对应 `UColdSteelWeaponIcons`，接入需单独一轮图标任务）；不使用占位图。
- **编译与链接验证**：`FPSGAMEEditor Win64 Development` **整体构建成功（Result: Succeeded）**，含 `Link [x64] UnrealEditor-FPSGAME.dll`，零错误（`Saved/BuildEditor/build-codex-cache.log`）。图鉴四个改动文件均参与编译。
- **自查修正（同轮）**：初版读物品 `Data` 的 `damage／attackInterval／range／magazine／reload／weight` 六个字段——经比对 `items.json` 实际 schema，这六个字段并不存在，数值会全部显示「—」。已改为与物品浮窗、运行时同一口径：`UGunsmithSystem::Calculate` 的 `FGunsmithStats` 为基础，再由 `ColdSteelWeaponStats::Damage/DamageParts/Interval/Reload` 施加敏捷／附魔后处理；未登记改造目录的物品如实显示「无枪械／近战参数」。`description` 亦更正为实际的 `desc`。
- **分类修正（同轮）**：原用 `Entry.Group == "生产工具"` 判断工具，但 `ClassifyItem` 从不下发该分组（工具落入「其他」），该分支是死代码。已改为只按物品自身 `category`（`tool`／`weapon_melee`／`weapon`／`weapon_ranged`／`weapon_magic`）归类，缺失时以 `weaponType` 兜底。实测收录：枪械 10 + 近战 3 + 生产工具 3 = **16 条武器**，怪物 **9 条**。
- **性能**：怪物六维与品阶按身份 Id 缓存（`MonsterStatsCache`），避免每次重建都重复 `LoadSynchronous` 与求值。
- **未测试**：未运行游戏、未做 UI 与交互测试，由用户测试。编辑器内需重新编译／热重载后才能看到图鉴入口。

## 页签与文字排列修订（2026-09-24 第二轮）

用户反馈选项卡文字呈竖直排列。定位为排版缺陷，非数据问题：

- **根因**：分类页签原用 `FillWidth(1.f)` 等分抽屉宽度，4 个分类各占约 1/4；而标签走 `Label()` 的 `AutoWrapText(true)`，窄列下中文被逐字换行，视觉上成为竖排单字。
- **主分区页签**：保持等分（`FillWidth(1)`）——仅两个字，等分正确；行内 `HAlign_Center`，行高 `ActionHeight`。
- **分类页签**：改为 `AutoWidth` + `ContentPadding`（左右各 14px），按钮宽度贴合文字；整行 `HAlign(HAlign_Center)` 居中，不再靠等分硬撑。
- **标签文本**：新增 `TabLabel()`，`AutoWrapText(false)` + `WrapTextAt(0)`，从机制上杜绝竖排；选中态由 `bActive` 决定字重与颜色。
- **列表卡片**：新增 `LeftLabel()`（左对齐单行不换行）。卡片改为首行横向「名称 …… 战力」（`FillWidth(1)` + `AutoWidth` 两端对齐，战力仅怪物栏显示）、次行类别；名称不再换行导致卡片高低不齐。
- **详情明细行**：由「说明 `FillWidth(1)` 换行 + 数值 `AutoWidth`」改为「说明 `AutoWidth` 且最小宽 84px 不换行 + 数值 `FillWidth(1)` 右对齐」，形成稳定的左右两列。
- **页脚**：快捷键提示改为单行居中。
- **验证**：`ColdSteelCodexPage.cpp` 编译零错误（`Saved/BuildEditor/build-codex-tabs.log`）。整目标链接仍因**用户正在使用的 UnrealEditor**（PID 95472）持有 `UnrealEditor-FPSGAME.dll` 而报 `LNK1104`；按 AGENTS.md 不强制结束该编辑器。
- **未测试**：本轮同样未运行游戏、未做 UI 测试，页签实际观感由用户确认。

## 冷钢 UI 合规复核（2026-09-24 第三轮）

按 `ui-cold-steel-design-system.md` 逐条比对排版布局与整体规划：**主题合规**（零违规 token），**发现并修正两处版式缺陷**。

**合规项（已核对）**
- **第 2 节配色**：未新增任何私有色值，全部来自共享 `ColdSteelUI`（`StatusCard`／`AttributeRow`／`Border`／`Accent`／`TextPrimary/Secondary/Tertiary`／`Success`／`ButtonNormal/Hover/Pressed`／`RarityColor`）；无蓝色染底、无彩色装饰边框。
- **第 3 节玻璃与圆角**：`SBackgroundBlur` 计数为 **0**，符合「次级卡片共享主面板模糊、不逐卡叠加」；卡片 `CardRadius` 8px、按钮 `ButtonRadius` 6px、轮廓 1px、滚动条 6px，均按 DPI 除以 `Scale`。
- **第 4 节字体**：字号仅用 **20／16／14／12** 四档，无表外字号；点数换算统一 `Pixels × 0.75 / PixelScale`；标题与分区标题 Medium 500、正文 Regular，数值走 `NumberFont`。
- **第 5 节按钮**：主分区页签等宽同高等距（`FillWidth(1)` + `ActionHeight`）；分类页签按 §17 采用文字自适应，与参考的 `codex-cat-tab` 一致。
- **第 6／13 节**：短标签横排不换行、长说明按段落宽度换行（§6 第 118 行既有条款）；复用宿主抽屉的标题、动画、让位与 `Tab` 关闭合同，不另建窗口。
- **第 17 节**：第 4 个入口、键位 `N`、只读档案、缺失显示「—」，与本节其他条款一致。

**修正 1（真实缺陷）· 响应式阈值失效**
原用 `< 720px` 作为纵排阈值。但抽屉宽度下限即 720px、`SetLayoutWidth` 收到 `Width−2`，正常显示器实际为 718–1038px —— 阈值取 720 意味着 **1080p／1440p 上永远走纵排，左右并排版式几乎从不出现**。已改为常量 `StackedBelowWidth = 560`（经用户确认），`BuildPage` 与 `BuildDetail` 共用，消除「并排排版却要求 420px 最小高」的矛盾约束。静态推算各宽度下详情列内宽 196–369px，均容得下 84px 说明列 + 数值。

**修正 2 · 两列滚动条行为不一致**
档案列表原 `SetScrollBarAlwaysVisible(true)`，右侧详情列为按需出现；一常驻一按需会让中缝宽度随滚动跳动。已统一为按需，与抽屉内其他面板惯例一致。

**验证**：`ColdSteelCodexPage.cpp` 编译零错误，整体构建 `Result: Succeeded`（`Saved/BuildEditor/build-codex-audit.log`）。
**未测试**：未运行游戏、未做 UI 测试；阈值与列宽为静态推算，实际观感由用户确认。

## 用户截图反馈修正（2026-09-24 第四轮）

用户截图指出两处：「卡片还是圆边角处理」「右下角的返回也是横向排列」。

**修正 1 · 圆角与描边未按 DPI 缩放（真实缺陷）**
调用 `ColdSteelUI::RoundedBrush` 覆盖按钮样式时，我传的是原始像素 `CardRadius`(8) 与 `1.f`，**没有除以 `PixelScale`**。而 `ColdSteelUI::ButtonStyle(Scale)` 内部的写法是 `ButtonRadius/Scale, ..., 1/Scale`。两者混用导致高 DPI 下圆角偏小、描边偏粗，卡片呈现「方角加粗边」——即用户看到的圆角不生效。项目内正确写法见 `DevelopmentPanelWidget.cpp:290`、`WeatherControlWidget.cpp:191`、`ColdSteelSmeltingWidget.cpp:424`。已修正全部 4 处覆盖点（分区卡画刷、选中页签、卡片 4 态）；选中边宽度由 `1.f` 改为 `Hairline * 2.f` 以保持 2px 语义。

**修正 2 · 按钮标签逐字竖排（同「页签竖排」一类缺陷）**
「返回列表」用的是 `Label()`（`AutoWrapText(true)`），在窄详情列里被逐字换行成「返／回」两行。已改用 `LeftLabel()`（单行）。同时排查了**全部 14 处文字调用点**，按用途分为三类：
- **必须单行**（已改）：按钮标签、页签、卡片名称与类别、明细行说明与数值、卡片战力 → `TabLabel`／`LeftLabel`／新增 `ValueLabel`。
- **保留换行**（正确）：物品说明、空态提示、口径说明等成段正文——符合 §6「长说明按明确的可用段落宽度换行」。
新增 `ValueLabel()`：JetBrains Mono 单行数值，用于明细行数值与卡片战力，避免数字在窄列被拆散。

**验证**：`ColdSteelCodexPage.cpp` 编译零错误（`Saved/BuildEditor/build-codex-corners.log`）。链接因用户编辑器的 DLL 占用报 `LNK1104`，按 AGENTS.md 不结束该编辑器。
**未测试**：未运行游戏、未做 UI 测试；圆角与换行的实际观感由用户确认。

## 详情立绘接入（2026-09-24 第五轮）

用户要求：给图鉴详情加图片，「武器装备统一朝向、怪物也是统一视角、统一朝向」，并设置好接入。

**先查现状（决定了工作量分配）**：武器侧**已有**截图管线 `UColdSteelWeaponIcons`——共用的 `FPreviewScene` 工作室、固定正交相机、`Capture->SetWorldRotation(FRotator::ZeroRotator)`，朝向本就统一，所以武器直接复用，不另拍一套。怪物侧**什么都没有**：无任何 `MonsterIcon`／`MonsterPreview` 类，磁盘上也没有怪物图（仅 `craft_wolf_banner.png` 一张无关横幅）。故怪物需要新建工作室。

**统一口径（两类共用的三条硬约束）**
1. **相机**：正交投影，`SetWorldRotation(FRotator::ZeroRotator)`，不随被摄体尺寸摆动；`bUseCustomProjectionMatrix` + `FReversedZOrthoMatrix`，与武器图标/近战图标逐字一致。
2. **被摄体朝向**：恒为 `FRotator(0,0,0)`。武器按 +X 前向、怪物按 `ACharacter` 前向取正面。体型差异只改取景半高（`FMath::Max(240cm, 盒高×1.15)`），不改朝向。
3. **画幅**：立绘 132×198px（2:3）统一外框；渲染缓冲 512×768（怪物）与武器图标各自原生尺寸，显示时等比填充。

**新增 `UColdSteelMonsterPortraits`**（`Source/FPSGAME/UI/`）：与 `UColdSteelWeaponIcons` 同机制——`GameInstanceSubsystem` + `FTickableGameObject`，同样的阶段机（建工作室→生成→摆姿取景→`CaptureScene`→GPU 回读）、`FRHIGPUTextureReadback` + 线程池转 `FColor`、按 Key 缓存 + `OnReady` 广播、LRU 淘汰、透明底 alpha 取反约定。

**写代码时发现并修掉的三个真问题**
1. **自动附身（会污染预览）**：怪物类构造里设了 `AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned`（`WolfMonster.cpp:58`），直接 `SpawnActor` 会在预览场景里生成 AI 控制器并跑行为树，浪费性能且可能让预览体自行移动导致取景漂移。第一版我改的是 CDO——**这是错的**，`GetDefaultObject()` 返回共享 CDO，改写会污染真正的游戏怪物。改为 `FActorSpawnParameters::Template` 传临时模板：生成体复制模板属性而非 CDO 属性，只影响这一具预览体。
2. **回读包误用文件级静态**：第一版把 `PendingReadback` 放在匿名命名空间，多 `GameInstance` 会互相覆盖；已改为成员，并把结构体移出匿名命名空间（否则与头文件前置声明不是同一类型，`error C2027/C2039`）。
3. **缺失包含**：`Components/DirectionalLightComponent.h`、`Engine/TextureCube.h`、`Materials/MaterialRenderProxy.h`。
4. **漏了就绪门（会拍到灰模／糊图）**：武器图标路径会先轮询「材质着色器编译完成 + 贴图像素流送到位」再捕获，我第一版直接 `CaptureScene()`。怪物贴图通常比武器更大，未流送完就拍会得到灰模或糊图。已补 `SubmitReadiness()`：渲染线程查 `IsRenderingThreadShaderMapComplete`，游戏线程按立绘分辨率 `StreamIn` 相应 mip，全部就绪才拍；总超时 10s，超时记失败留占位。

**接入点**：`ColdSteelCodexPage` 新增 `PortraitBrush`／`PortraitFrame`／`RequestPortrait`／`HandlePortraitReady`；详情头部改为「左图右文」横向结构；选中即请求，`OnReady` 命中当前选中项时重建详情；`RebuildWidget` 绑回调、`ReleaseSlateResources` 解绑（`RemoveAll(this)`，避免页面销毁后被回调引用）。未出图时显示同尺寸「生成中」占位框，不画假图。

**验证**：`ColdSteelCodexPage.cpp` 与 `ColdSteelMonsterPortraits.cpp` 编译零错误，整体构建 `Result: Succeeded`（`Saved/BuildEditor/build-codex-portrait6.log`）。
**未测试**：未运行游戏、未做 UI 测试。**立绘的实际取景、朝向一致性与怪物静态姿势均未在引擎内目视确认**——取景半高、正面朝向、静息姿态这三项是按代码推算的，尤其怪物是否停在第 0 帧静息姿势、以及是否有怪物网格自带偏转（如 `AWolfMonster` 构造函数里 `GetMesh()->SetRelativeRotation(FRotator(0,-90,0))`，四足兽因此面向世界 +X 时视觉正面可能与两足怪不同）需要用户实机确认后再微调。

## 用户反馈修正（2026-09-24 第六轮）

用户反馈两件事：① 怪物都没进图鉴，「因为没有分配等级」；② 武器贴图被错误压缩，「可以直接调用背包里的图片给其预留整个横栏不要拉伸」。

### 修正 1 · 怪物没进图鉴：真因是登记表取错组件（不是等级未分配）

**真因**：`UDevelopmentSpawnComponent` 挂在 **PlayerController** 上（`FPSGAMEPlayerController.cpp:55` 构造里 `CreateDefaultSubobject(TEXT("DevelopmentSpawner"))`），而我的 `ResolveSpawner()` 是 `PC->GetPawn()->FindComponentByClass<...>()` —— **从 Pawn 找，恒为 nullptr**，于是怪物分区永远为空。已改为 `GetOwningPlayer<AFPSGAMEPlayerController>()->GetDevelopmentSpawner()`，与 `DevelopmentPanelWidget::ResolveSpawner` 同一入口。

**关于「等级未分配」的核查结论**：九只怪物**全部都已能解析出品阶**，没有一只是未分配的。依据：
- `MonsterCoreStats::Get` 对九只登记身份都有对应 `Cast` 分支；`BP_ZombieDog`（读 uasset 确认父类 `WolfMonster`）与 `BP_NurseZombie`（父类 `NurseZombie`）都走继承分支。
- 没有 `Rank` 成员的五个类（`FatZombie`／`Mutant3`／`WitchMonster`／`InfectedDogMonster`／`WitchRebuiltMonster`）分别继承 `ANurseZombie`／`AWolfMonster`，而两者都声明了 `Rank`（默认 `Normal`），因此子类同样有 `Rank`。
- 现行品阶：手脑 `Lord`、毒蛆 `Elite`、其余（胖子僵尸／突变体-3／护士僵尸／巫婆·重建候选／野狼／僵尸犬／感染犬）均 `Normal`。
- 按用户指示**保留现有品阶不变**（改默认值会连带改奖励倍率与战力加成）。
- 顺带核查：CDO 查询路径安全——`MonsterCoreStats::Get` 内的 `UProgressiveInfectionComponent::AttributeMultiplier(Target)` 在无组件时返回 `1.f`（`ProgressiveInfectionComponent.cpp:62`），不会因传 CDO 出错。

### 修正 2 · 武器贴图被压缩：固定竖框 + SImage 拉伸

**真因**：武器图标**不是 2:3**。枪械画布宽按「320px/格行」推出（`IconCanvasWidth`，如 768×320 → 12:5 **横幅**），近战是 384×768 **竖幅**。我先前用固定 132×198 的 `SBox` 包 `SImage`，而 `SImage` 会把画刷拉满整框 → 横幅枪械被硬压进竖框，即用户看到的「错误压缩」。

**改法**（按用户要求：预留整个横栏、不拉伸）：改为**整条横栏**布局——高度固定 132px，武器可用宽 300px、怪物 220px；按笔刷真实 `ImageSize` 求等比 `Fit = min(可用宽/图宽, 可用高/图高)`，再用 `SImage::DesiredSizeOverride` 给出等比目标尺寸并居中。算法与背包 `ColdSteelInventoryPresentation.cpp:127-134` 一致（同一 `ImageSize` 源、同一取景比例），因此图鉴与背包显示同一张图、同一比例。

**写这段时避开的一个坑**：`SImage` 只持有 `const FSlateBrush*`（`SImage.h:40` `SLATE_ATTRIBUTE(const FSlateBrush*, Image)`）。第一版我把缩放后的尺寸写进一个局部 `FSlateBrush` 副本再传地址，会**悬空**；已改为沿用工作室缓存里的原始笔刷 + `DesiredSizeOverride`。

**验证**：本机此刻有其它并行任务的多个文件处于半成品状态（`ColdSteelWorkbenchWidget.cpp` 常量未闭合、`ColdSteelProductionDrops.cpp`、`M4GunsmithLayout.cpp`、`ProductionToolStats.cpp`），整体构建被它们挡住，**无法给出 `Result: Succeeded`**。改以 `-DisableUnity` 单独编译验证：`build-codex-single.log` 中 `ColdSteelCodexPage.cpp` 与 `ColdSteelMonsterPortraits.cpp` **零错误**（该 log 的错误全部来自上述其它任务的文件）。按 AGENTS.md 不修改、不代管他人半成品。
**未测试**：未运行游戏、未做 UI 测试；怪物是否已出现在图鉴、武器贴图比例是否正确，均由用户实机确认。

## 用户反馈修正（2026-09-24 第七轮）：详情占 2/3 + 立绘真正铺满横栏

用户反馈：① 右详情要占面板 **2/3**、左名称列表 **1/3**；② 上一轮「贴图占一横栏」**没有成功，还是压缩在一个小范围**。

### 修正 1 · 左右比例 58/42 → 1/3 与 2/3

`BuildPage` 并排分支原为 `.58 / .42`，改为 `CodexGridShare = 1/3`、`CodexDetailShare = 2/3`（新增两个常量，与 `StackedBelowWidth` 并列，避免比例散落两处漂移）。

### 修正 2 · 上一轮为什么没生效（两层原因，第二层才是关键）

- **第一层（上一轮已改，但不彻底）**：固定 `132×198` 竖框 + `SImage` 拉满 → 横幅枪械被压扁。上一轮改成等比 Fit，但把缩放上限写死成 `MaxW = 300px`。
- **第二层（本轮的真因）**：立绘当时放在**与文字并排的 `AutoWidth` 槽**里。`AutoWidth` 槽宽 = 内容自身宽度，图片再大也只能占到自己那点宽度，永远无法横跨整列——所以「还是压缩在一个小范围」。**只改缩放算法、不改容器槽位，视觉上不会有变化。**

**本轮改法**：立绘改为**独占一整条横栏**（单独一行，整宽居中），名称／类别移到下一行；横栏宽度不再硬编码，而是由详情列实际宽度推出：`列宽 = PageWidth × 2/3`（并排）或 `PageWidth`（纵排），再减去左右 12px 内边距；高度上限武器 200px、怪物 240px（防竖幅近战把详情顶下去）。等比 Fit 与 `DesiredSizeOverride` 保留。

**效果对照（内容宽 → 图片可用宽）**：改前恒为 **300px**（就是用户看到的「小范围」），改后 1280→457px、1600→489px、1920→592px、2560→671px，约翻倍并铺满横栏。

**同时核对左列收窄到 1/3 后仍可读**：网格列 239–346px，减去内外边距后卡片文字宽 199–306px；卡片名称最长约「QBZ-191 突击步枪」9 字 ×20px ≈180px、「巫婆·重建候选」7 字 ≈140px，均单行容纳；卡片标签本就是 `LeftLabel`（不换行），不会退回竖排。

**验证**：`-DisableUnity` 构建中 `ColdSteelCodexPage.cpp` 与 `ColdSteelMonsterPortraits.cpp` **实际参与编译且零错误**（`Saved/BuildEditor/build-codex-layout.log`）。该次构建整体仍失败，唯一报错来自其它任务正在改的 `WorldGeneration/FluidPresentationSubsystem.cpp:360`（`C4458` 成员名遮蔽），与本任务无关，未触碰。
**未测试**：未运行游戏、未做 UI 测试；2/3 比例与立绘横栏的实际观感由用户实机确认。

## 系统审计（2026-09-24 第八轮）：UI 排版 + 数值引用

对 `ColdSteelCodexPage` 与 `ColdSteelMonsterPortraits` 做了一遍逐项审计，范围：字体层级、换行策略、画刷 DPI、数值字段真实性、品阶映射、热键一致性、指针生命周期、缓存与失败语义。

### 审计发现并修复的缺陷

**A1 · 品阶页签错位一格（真实缺陷，用户可见）** —— 最严重的一项。
`MonsterCategoryLabels` 刻意不列 `Minor`（九只身份没有一只用它），但过滤用的是下标算术 `Category != Row.SortKey + 1`，**等于假设「页签编号」与「EMonsterRank 枚举值」重合**。实际两套编号不同，导致每一阶都错位：**毒蛆(Elite) 显示在「领主」页签、手脑(Lord) 显示在「首领」页签**，且没有任何怪物能出现在「精英」页签下。只看「全部」页签时完全正常，所以此前未暴露。
修法：新增 `MonsterCategoryRanks[]` 映射表（页签→品阶）+ `static_assert` 保证两表同长，过滤改为按品阶比对，不再做下标算术。

**A2 · 立绘延后重试会串作业（真实缺陷，我上一轮引入）**
上一轮为「首次编译超时不该永久失败」加了延后重试，但 `DeferCurrentJob` 把作业移到**队尾**后，`Tick`／`FinishJob`／`PollReadback`／`SpawnSubject`／`BeginReadback` 仍按 `Queue[0]` 认定「当前作业」——作业身份错位，可能销毁/发布错误的作业，`Pending` 集合也会残留。
修法：新增 `ActiveIndex` 显式记录在拍作业，上述五处一律经 `ActiveIndex` 取；`DeferCurrentJob` 内先 `CancelReadback()` 再 `ResetSubject()`，避免回读包引用已释放的渲染目标。

**A3 · 单次超时即永久失败（健壮性）**
怪物首次渲染需等着色器编译 + 贴图首次流送，10s 单次超时容易误判；一旦进 `Failed` 就**再也不出图**。改为 `MaxAttempts = 3` + 1.5s 冷却的延后重试，与武器图标工作室的 `DeferCurrentJob/RetryAfterSeconds` 同策略。

### 审计通过、无需改动的项

- **字体层级**：仅用 12/14/16/20px，全部落在冷钢六档（24/20/16/14/12/11）内。
- **换行策略**：`AutoWrapText(true)` 仅剩 `Label()` 一处定义；`Label()` 调用点全部是**成段正文或标题**（分组标题、空态提示、物品说明、战力口径说明、详情标题）。卡片／页签／数值一律走 `LeftLabel`／`ValueLabel`／`TabLabel`（均单行），无竖排回归。
- **画刷 DPI**：4 处 `RoundedBrush` 覆盖（分区卡、选中页签、卡片四态）全部经 `Radius`／`Hairline` 预算并已除以 `Scale`。
- **武器数值字段真实性**：`name`／`type`／`rarity`／`isTwoHanded`／`equipSlot`／`desc` 逐个在 `items.json` 中确认存在（130/130、13/21、26 等），无伪造字段；全部 13 件武器类物品 `name` 非空。战斗数值仍走 `UGunsmithSystem::Calculate` + `ColdSteelWeaponStats`，不读物品 Data 里不存在的字段（该问题在第一轮自查时已修）。
- **怪物数值来源**：六维／等级／品阶走 `MonsterCoreStats::Get(CDO)`；CDO 路径安全——内部 `UProgressiveInfectionComponent::AttributeMultiplier` 无组件时返回 `1.f`。九只身份全部能解析品阶。
- **热键一致性**：`N` 在右侧栏目导航（`ColdSteelPanelNavigation` 入口 3）与 HUD 快捷键（`EKeys::N`）两处一致，入口→页号映射（`Entry==3 → Page 4`）正确。抽屉内那条 3 项页签循环是本来的正确行为：该页签条已被 `SetVisibility(Collapsed)` 整体隐藏，第 4 项「图鉴」是 `bInteractive=false` 的占位，绑定的是 Dummy 控件。
- **指针生命周期**：`BorderImage(&…)` 两处均取类成员（`SectionBrush`），非局部量；`SImage` 用 `DesiredSizeOverride` 表达等比尺寸，不改写画笔刷，无悬空。
- **缓存**：`MonsterStatsCache` 按身份 Id 缓存；立绘缓存 32/64 上限 + LRU；纹理随缓存条目一并移除。
- **ID 冲突**：13 个武器 Definition 与 9 个怪物 Id 无交集，`OnReady` 回调按 Id 匹配暂不会误命中（仍属脆弱点，见下）。

### 保留的已知脆弱点（未改，记为后续观察）

`HandlePortraitReady` 只按 Id 匹配、不区分「武器工作室」还是「怪物工作室」触发。当前两套 Id 无交集故无实际影响；若日后新增同名武器与怪物，会引发一次多余重建（不致命）。另「首领」页签当前无任何怪物（无 Boss 品阶身份），会走空态文案，属预期。

**验证**：`-DisableUnity` 构建中 `ColdSteelCodexPage.cpp` 与 `ColdSteelMonsterPortraits.cpp` **实际参与编译且零错误**（`Saved/BuildEditor/build-codex-audit2.log`）。该次整体构建失败，报错全部来自其它任务正在改的 `Monsters/WolfMonster.cpp`（78 行未提交改动，报 `bUsePredictiveHunting`／`BuildHuntingPounce` 未声明，与图鉴无关），未触碰。
**未测试**：未运行游戏、未做 UI 测试；品阶页签归属（毒蛆应落「精英」、手脑应落「领主」）与立绘观感由用户实机确认。

## 缺陷 3 的正确解法：改为后台异步加载（2026-09-24 第九轮）

上一轮我把「单次 10s 超时即永久失败」改成「最多 3 次、1.5s 冷却的延后重试」。用户追问**有没有兼顾性能的后台异步加载方案**——这个质疑是对的：**重试只是把超时往后挪，没有解决「为什么要等这么久」**。

### 病根：同步加载硬卡游戏线程

`SpawnSubject()` 原先用 `Queue[i].CharacterClass.LoadSynchronous()`。**`LoadSynchronous` 会在游戏线程上硬等包加载与类构造**——首次进图鉴时直接卡帧，等待时间取决于磁盘与包大小，既不可预测，也不是超时值调大调小能解决的。贴图首次流送同理。

### 采用项目内已有的成熟方案，不另造一套

武器图标工作室**早就解决过同一问题**，做法在 `ColdSteelIconResources.cpp`：
- `BeginResourceLoad()` 用 `UAssetManager::GetStreamableManager().RequestAsyncLoad(...)` 发起**异步**加载，返回 `FStreamableHandle`；
- 阶段机里 `if(ResourceLoad && !ResourceLoad->HasLoadCompleted()) return;` **每帧只查完成状态，游戏线程从不等待**；
- 句柄**保留到捕获结束**，防止 GC 在拍摄前把预载资源卸掉。

本轮把怪物立绘改为**同一策略**：
1. 新增 `BeginAsyncLoad()`：对该身份的 `TSoftClassPtr` 发 `RequestAsyncLoad`，句柄存 `ResourceLoad`；
2. 阶段机拆出「等异步加载」（Stage 1）与「等着色器/贴图就绪」（Stage 4）两个互不混淆的等待；
3. `SpawnSubject()` 的 `LoadSynchronous` 改为 `Get()`（此时异步加载已完成，取值不阻塞）；
4. **异步加载阶段不设人为超时、不消耗尝试次数**——加载由 UAssetManager 正常调度，静候其完成即可；
5. `ResetAsyncLoad()` 在 `FinishJob`／`DeferCurrentJob`／`Deinitialize` 三处 `CancelHandle()`，避免句柄泄漏；
6. 仅 Stage 4 保留 10s 上限，且仅用于防「着色器永久失败」占住队列，命中后延后重试。

### 效果

- **游戏线程不再被包加载阻塞**：首次打开图鉴某怪物时不会因加载卡帧，加载在后台推进、UI 只做状态轮询。
- **不再依赖超时兜底**：原来「等 10s 后重试」变成「加载完就继续」，超时值不再是正确性的一部分。
- 重试机制**保留**，但降级为纯粹的失败兜底（加载句柄拿不到类、或资源始终不就绪时最多 3 次），不再是主路径。

**验证**：`-DisableUnity` 构建中 `ColdSteelCodexPage.cpp` 与 `ColdSteelMonsterPortraits.cpp` **实际参与编译且零错误**（`Saved/BuildEditor/build-codex-async.log`）。该次整体构建失败，报错来自其它任务正在改的 `Production/ProductionToolComponent.cpp`（未提交改动，`fatal error C1083` 无法打开包含文件），与本任务无关，未触碰。
**未测试**：未运行游戏、未做 UI 测试；异步加载的实际卡帧改善与立绘出图由用户实机确认。

## 内存与加载时机修正（2026-09-25 第十轮）：打开才加载、逐个顺序、当前项优先

用户反馈：**加载导致内存占用而卡死游戏进程**。要求改为「只在打开图鉴栏时加载、逐步单个顺序加载、优先加载玩家正在查看的项」。

### 诊断：真正的病根不是「请求太多」

先核对了实际情况，结论与直觉相反：

- **请求本来就是懒的**：`RequestPortrait` 只在 `SelectEntry` 里调用（`ColdSteelCodexPage.cpp:726`），即玩家点选才拍，**从来没有预取整份列表**。所以「改成只在打开时加载」这条本身几乎已满足。
- **真正的常驻问题在工作室内存**：`EnsureStudio()` 创建的 `FPreviewScene` + `512×768 RTF_RGBA16f` 渲染目标（约 6MB），**只在 `Deinitialize()` 里释放**（原 `Studio.Reset()` 仅出现在析构路径）。也就是说**只要拍过一张图，预览场景和渲染目标就整个会话一直驻留**，且 `FPreviewScene` 会持续参与场景更新——这是「占内存 + 卡」的主要来源。
- 单次捕获的瞬时峰值约 10.5MB（FFloat16 数组 3MB + FColor 数组 1.5MB + GPU staging 3MB + RT 3MB），属正常单张开销，不是主因。
- 缓存上限 32 张 × 1.5MB ≈ 48MB（CPU+GPU 各一份），偏大。

### 修正

1. **关闭即释放工作室**：新增 `TeardownStudio()`，整段拆掉预览场景／捕获组件／渲染目标，并把被摄体材质引用一并放手。新增 `ReleaseIdleResources()` = 清空未拍的排队项 + 拆工作室，**但保留已完成的小图缓存**（缓存是独立的小纹理，不依赖工作室，保留可让重开面板立即命中）。
2. **打开才加载**：图鉴页新增 `bCodexVisible` 状态，在 `NativeTick` 里按可见性变化驱动——**关闭→释放，打开→只把「当前选中项」排进队列**（没有选中项就什么都不加载，等玩家点选）。
3. **严格单个顺序**：核对确认 `Tick()` 每个分支只处理一个作业且立即 return，函数体内**无 for／while 循环**，`CaptureScene` 与 `BeginReadback` 各只有一处调用——一次只有一个捕获在飞，天然逐个顺序。
4. **当前查看项优先**：新增 `RequestPriority()`。玩家点选的那张**插到队首**（排在已排队的项之前），正在拍的那项不动；若该键已在队列中则**挪到最前并保留其已消耗的尝试次数**。同时修正 `ActiveIndex`，避免挪动后被指向别的作业。
5. **缓存收紧**：32 → **12 张**（约 18MB）。图鉴一屏最多看一张详情图，12 张足够覆盖「翻回去不用重拍」。

### 顺带修好的并行冲突

`ColdSteelCodexPage.cpp` 里出现了一处**并行任务造成的半成品改名**：某并行任务为规避新增类成员 `bActive` 的遮蔽（C4458），把 `BuildPage()` 里的两个局部量 `bActive` 改名为 `bIsActive`，但**只改了一半**——局部量声明与部分引用改了，L394／L399 仍写 `bActive`，于是编译不过（`error C2065: bActive 未声明`）。

本轮把类成员改名为 `bCodexVisible`（本文件已有同名局部量，成员叫 `bActive` 本身就不合适），局部量统一回 `bActive`，两处页签渲染恢复一致。`TabLabel` 的**参数** `bIsActive` 保持不变（它是形参，与成员无关）。

**验证**：`-DisableUnity` 构建 **`Result: Succeeded`，全模块 0 错误**（`Saved/BuildEditor/build-codex-lazy3.log`）；我的两个文件零错误零警告。此前受阻的 `WolfMonster.cpp`／`ProductionToolComponent.cpp` 在本次构建中也已通过（由各自任务补齐）。
**未测试**：未运行游戏；内存占用改善、关闭后是否真的释放、以及当前项优先的实际手感由用户实机确认。

## 新增武器／怪物的接入成本（2026-09-24 核查）

回答「图鉴有无自动添加机制」：**列表与详情是全自动的，唯有立绘需要额外一步，且武器与怪物的成本不同**。

### 列表 ＋ 详情 ＋ 数值：自动

**武器**：完全数据驱动，**只改 `Content/ColdSteelData/items.json`，零代码改动**。链路三处都不含白名单：
1. `ColdSteelProfileRuntime.cpp:100-102` —— `for(const auto& Pair:Root->Values) Definitions.Add(...)`，把整个 JSON **全量**读入；
2. `ColdSteelDevelopmentTools.cpp:92 ItemCatalog()` —— `for(const auto& Pair:Definitions)`，**全量**转成目录条目；
3. 图鉴 `Entries()` 只按 `WeaponCategoryOf()` 读物品自身的 `category`／`weaponType` 归类。

所以新武器只需在 `items.json` 里加一条，把 `category` 写成 `weapon`／`weapon_ranged`／`weapon_melee`／`weapon_magic`／`tool`，图鉴立刻收录；战斗数值走 `UGunsmithSystem` + `ColdSteelWeaponStats`，也不需登记（未登记则如实显示「无枪械／近战参数」）。

**怪物**：**需要在代码里登记一条**。`UDevelopmentSpawnComponent` 构造函数内以 `Add(Id, Name, ClassPath, Radius)` 硬编码九个身份（`DevelopmentSpawnComponent.cpp:12-31`），图鉴、开发面板、刷怪共用这一张表。加新怪物 = 在该构造函数里加一行 `Add(...)`。这是**有意为之**：这张表同时是刷怪名单，不该自动收录磁盘上任何怪物资产。

### 立绘：需要额外一步

- **枪械**：`UColdSteelWeaponIcons::Supports()`（`ColdSteelWeaponIcons.cpp:39`）是**硬编码 10 个 Definition 的白名单**（ue_m4a1／ue_akm／ue_a762／ue_svd／ue_pkm_lowpoly／ue_qbz191／ue_ash12／ue_m16a2／ue_m1911／ue_dan_wesson715）。新枪不加白名单则**不出立绘**（显示「生成中」占位），不崩不报错。
- **近战**：**数据驱动**。`ColdSteelMeleePreview::Supports()` 判据是 `IsMeleeWeapon(Item) && !Text(Item,"world_mesh").IsEmpty()` —— 只要 `items.json` 里给了 `world_mesh` 路径就自动出图（现有三把近战都已声明该字段）。
- **怪物**：**自动**。立绘按登记表里那条的 `CharacterClass` 生成，登记了就能出图，无额外代码。

### 结论与建议

| 新增内容 | 列表／详情／数值 | 详情立绘 |
|---|---|---|
| 枪械 | 只改 `items.json` | 需在 `Supports()` 白名单加一行 |
| 近战武器 | 只改 `items.json` | 只改 `items.json`（补 `world_mesh`） |
| 怪物 | 需在 `DevelopmentSpawnComponent` 加一行 | 自动 |

**可改进项（未做，待用户决定）**：枪械立绘的白名单是唯一「数据已加、图不出」的坑。若希望枪械也做到纯数据驱动，可把白名单换成读物品字段（如 `ue_icon`／`icon`，现有枪械条目已带这两个字段）来判定「是否有可渲染的枪械本体」，与近战的 `world_mesh` 判据对齐。这属于行为变更，需用户确认后再动。

## 设计约束（图鉴栏，供后续沿用）

本节把图鉴栏的硬约束就地固化，便于单独查阅本页即可复现；正式条款以
[冷钢 UI 正式规则](ui-cold-steel-design-system.md) 第 17 节为准（该节由同批改动加入）。

- **入口**：右侧持久栏目「图鉴」，第 4 项，快捷键 **N**（`K`／`J` 属强化台与改造台，`C` 是滑铲，均被 `FPSGAMEPlayerController::InputKey` 先消费）。栏目入口序 0 状态／1 背包／2 技能／3 图鉴，**与抽屉页号不同：图鉴是第 4 页**，`ActivatePanelNavigation()` 里做 `Entry==3 → Page 4` 的换算。
- **左右分栏比例**：并排时左名称列表 **1/3**、右详情 **2/3**（`CodexGridShare`／`CodexDetailShare`）。详情占大头才能容下整栏立绘与「说明 + 数值」两列。
- **立绘必须独占整条横栏**：**不能与文字并排**。放进 `AutoWidth` 槽与文字并排时，槽宽只等于图片自身宽度，图片永远无法横跨整列——这正是「改了缩放仍显示在很小范围」的原因。横栏宽度由**详情列实际宽度**推出，不硬编码小上限。
- **等比不拉伸（硬约束）**：按笔刷真实 `ImageSize` 求 `Fit = min(可用宽/图宽, 可用高/图高)`，用 `SImage::DesiredSizeOverride` 给等比目标尺寸并居中。**禁止**把画刷 `ImageSize` 改写成可用宽高来硬拉——那会变形。
- **横栏高度上限**：武器 200px、怪物 240px，防止竖幅近战把详情内容顶出屏幕。
- **统一朝向与视角**：两类立绘都用**固定正交相机**拍摄，相机朝向恒为 `FRotator::ZeroRotator`、不随被摄体尺寸摆动，被摄体朝向恒为 `FRotator(0,0,0)`。
- **来源**：武器**复用背包武器图标工作室**（`UColdSteelWeaponIcons::Find/Request`），不另拍一套；怪物走图鉴专用立绘工作室 `UColdSteelMonsterPortraits`。
- **数据来源必须挂在 PlayerController**：怪物生成登记表由 `AFPSGAMEPlayerController` 持有（构造里 `CreateDefaultSubobject`），**不在 Pawn 上**；按 Pawn `FindComponentByClass` 取会永远拿到空，导致怪物分区恒为空。
- **怪物立绘为纯展示**：生成时用 `FActorSpawnParameters::Template` 传临时模板把 `AutoPossessAI` 置为 `Disabled`，**不改写共享 CDO**（怪物类构造里是 `PlacedInWorldOrSpawned`，直接 SpawnActor 会在预览场景跑 AI／行为树）。
- **运行时渲染 + 有界缓存**：首次选中时异步渲染，完成后经 `OnReady` 回填重建详情；未出图时显示同高整条横栏占位框，不画灰色假图、不留塌陷空洞。缓存上限 32（怪物）／64（武器），超出按 LRU 淘汰；不往仓库新增 PNG。
- **预览资源一律异步加载（硬约束）**：预览用类与贴图必须走 `UAssetManager::GetStreamableManager().RequestAsyncLoad(...)`，阶段机每帧只查 `HasLoadCompleted()`，**禁止在游戏线程 `LoadSynchronous`**。句柄须保留到捕获结束防 GC 卸资源，并在作业结束／延后／析构三处 `CancelHandle()`。
- **失败口径**：该类无骨骼网格、材质未编译或回读超时（10s）时记为失败，立绘位保持占位，不影响文字档案显示。加载阶段的等待不设人为超时、不消耗重试次数；重试仅作失败兜底（最多 3 次）。
- **页签与枚举的编号必须显式映射**：怪物页签刻意不列 `Minor`，**页签下标与 `EMonsterRank` 枚举值不是同一套编号**，禁止用 `SortKey+1` 之类下标算术反推，必须用映射表比对并以 `static_assert` 保证表长一致（此前用下标算术导致每一阶都错位一格）。
- **字体**：只用冷钢六档（24/20/16/14/12/11px）。页签／卡片／数值一律 `AutoWrapText(false)` 单行显示；`AutoWrapText(true)` 仅用于成段正文与可换行标题，否则窄列里中文会逐字竖排。
- **缺失口径**：任何数值缺失显示「—」，未登记六维的身份仍列出条目并标注「未登记六维」，不伪造数值。