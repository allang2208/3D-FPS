# 冶炼面板规划（2026-09-23）

> 按 [面板与栏目工作流](../../UI-WORKFLOW.md) 与 [冷钢 UI 正式规则 2.19](ui-cold-steel-design-system.md) 编写。本文只做规划，实现按授权阶段进行。

## 1. 目标与范围

为已接入的高炉（`/Game/Props/BlastFurnace20260923/SM_BlastFurnace`，建造面板「其他 → 冶炼高炉」）增加交互：

- 准星瞄准高炉按 **E** 打开**背包**，并在**背包左侧**弹出**冶炼面板**。
- 冶炼面板：**宽度 = 背包面板的一半**，**高度与背包一致**。
- 功能：放入**原矿石**，经过一定时间冶炼生成**矿锭**，带**进度条**。
- 进度条复刻原项目 `E:\无尽轮回\长期备份\2026-7-13-1\game-dev` 的实现，遵循其**按进度取色**规则。

**不在本次范围**：熔炼数值平衡、锭的后续用途、锭类物品图标绘制（沿用占位/已有图标）、背包拖拽改造。

## 2. 原项目进度条复刻依据

来源：`game-dev/src/ui/game-ui-manager.js` 与 `game-dev/game-style.css`。

### 2.1 取色函数（核心规则）

`game-ui-manager.js:51-68`：

```js
const TIMELINE_PROGRESS_COLORS = [
    { at: 0,     rgb: [61, 196, 91] },   // #3DC45B 绿
    { at: 1 / 3, rgb: [65, 139, 231] },  // #418BE7 蓝
    { at: 2 / 3, rgb: [241, 193, 63] },  // #F1C13F 黄
    { at: 1,     rgb: [229, 65, 62] },   // #E5413E 红
];

function timelineProgressColor(value) {
    // 在相邻两个色标之间线性插值，返回 rgb(...)
}
```

**规则本质**：颜色由**进度值**在四个色标之间线性插值得到，而不是整条固定颜色。

**语义**：原项目是"未来 5 日事件时间轴"（`at:0` 绿 = 时间还早/安全，`at:1` 红 = 临近/紧急），属**倒计时威胁**语义。CSS 侧（`.world-invasion-bar`，`game-style.css:1799-1812`）再以 `linear-gradient(90deg, start 0%, #f1c13f 33%, #418be7 66%, end 100%)` 画彩虹条，用 `width` 裁切；JS 设 `start=timelineProgressColor(1)`、`end=timelineProgressColor(0)`。

### 2.2 冶炼场景的方向决定

冶炼是**正向进度**（0% 未开始 → 100% 完成），直觉语义应为 **0% 红 → 100% 绿**（完成=绿、成功）。

因此：
- **复刻**其**取色机制**：4 色标 + 线性插值函数。
- **方向按冶炼语义正向化**：`at:0 = #E5413E 红`，`at:1/3 = #F1C13F 黄`，`at:2/3 = #418BE7 蓝`，`at:1 = #3DC45B 绿`。
- 原项目反向常量（时间轴用）保留在注释中说明来源，不混入冶炼取色。

> 若用户希望完全照搬反向（0 绿 1 红），只需交换常量数组顺序，函数不变。此项已于 2026-09-23
> 按推荐口径（正向）定稿，见第 7 节实现记录。

### 2.3 进度条视觉

- 轨道：深底 `Content` `#121212EB`，圆角与填充一致。
- 填充：高度 **5px**（原项目 `.world-invasion-bar` 的 `height: 5px`），圆角 `inherit`。
- 颜色：填充条整体取**当前进度对应颜色**（单色），或按原项目铺满彩虹再用 width 裁切。**冶炼采用"单色=当前进度色"**，更易读且保持"颜色随进度变化"的规则。
- 过渡：`width` 线性过渡（原项目 0.18s linear）。

## 3. 布局与尺寸

- 背包抽屉：`InventoryWidth = clamp(视口宽 × 48%, 720, 1040)`，且不超过 `视口宽 − RightInset − 12`；仓库打开时两者各取 `(视口宽 − RightInset − 24) / 2`（`ColdSteelInventoryTheme.cpp:29-31`）。
- 冶炼面板：**宽度 = 背包实际宽度的一半**（即 `InventoryWidth / 2`），**高度 = 背包一致**（画布锚定右侧 + 上下外沿 12px）。
- 位置（2026-09-23 第三轮）：面板只在背包开着时出现，**贴在背包抽屉左侧**（中缝 12px）。代码同时支持"背包关时贴视口右缘"的独立态（`SmeltDock`，当前生命周期下基本走不到，留作后备）。低于最小可用宽（240px）整块收起。
- 生命周期（2026-09-23 第三轮，按用户澄清定稿）：**高炉 E＝背包＋面板一起开；打开背包永远不带出面板**。面板有自己的关闭出口（Esc／顶栏 ×，可只收面板保留背包）；关闭背包时一并收起面板，避免下次开背包残留上次面板。

## 4. 冷钢 UI 规范（第 2/3/4 节）

| 项目 | 取值 |
| --- | --- |
| 面板玻璃底 | `GlassTint` `#1A1A1AF8` |
| 低画质回退 | `GlassFallback` `#1D1D1DFF` |
| 顶栏叠层 | `HeaderTint` `#64646416` |
| 分区卡片 | `StatusCard` `#252525E8` |
| 数值轨道／深底 | `Content` `#121212EB` |
| 主文字 | `TextPrimary` `#E8E8E8FF` |
| 次要文字 | `TextSecondary` `#B7B7B7FF` |
| 弱提示 | `TextTertiary` `#919191FF` |
| 银白强调 | `Accent` `#D6D6D6FF` |
| 细边 | `Border` `#DEDEDE2E` |
| 按钮默认／悬停／按下／禁用 | `ButtonNormal` `#2B2B2BBE` / `ButtonHover` `#414141E6` / `ButtonPressed` `#181818F0` / `ButtonDisabled` `#16161678` |
| 背景模糊 | `UBackgroundBlur` 强度 **9**、半径 **21** |
| 圆角 | 主面板 **10px**，分区卡片 **8px**，按钮 **6px**，轮廓 **1px** |

### 字体（第 4 节）

- 文字：**Noto Sans SC**（`ColdSteelUI::TextFont`），Regular 400 正文／Medium 500 标题。
- 数字、计时、数量：**JetBrains Mono**（`ColdSteelUI::NumberFont`）。
- 字号档位（本面板用四档）：**20**（面板标题）／**16**（分区标题）／**14**（正文、属性名、按钮）／**12**（辅助说明、快捷键）。
- 调用合同：`Points = Pixels × 0.75 / PixelScale`（`ColdSteelUI::TextFont` 接收 Slate 点数）。

## 5. 数据

### 5.1 已有矿石（items.json）

`ironOre` 铁矿石、`copperOre` 铜矿石、`silverOre` 银矿石、`goldOre` 金矿石（另有 `aluminumOre`、`tinOre`、`leadOre`、`titaniumOre`、`tungstenOre`、`mithrilOre`、`coalOre`、`sulfurOre`）。字段含 `id / name / ue_icon / maxStack / rarity / type`（`type` 为「祭品」，`category` 为 `tribute`）。

### 5.2 待新增

- **锭类物品**：`ironIngot` 铁锭、`copperIngot` 铜锭、`silverIngot` 银锭、`goldIngot` 金锭（路线图 O2 已指出"没有锭类物品"）。
- **冶炼配方**：新增 `smelting-recipes.json`（对齐路线图"新增 `crafting-recipes.json`"的同类做法），字段建议：
  ```json
  {
    "id": "ironIngot",
    "input": { "item": "ironOre", "count": 1 },
    "output": { "item": "ironIngot", "count": 1 },
    "seconds": 8.0
  }
  ```

### 5.3 炉内状态

- 每个高炉实例保存：配方 id、开始时间、是否完成。
- 冶炼**按真实时间推进**（存开始时间戳，读档后按时间差续算，而非存剩余秒数）。

## 6. 交互流程

1. 准星瞄准高炉 → `ColdSteelWorldInteraction::TraceTarget` 命中 → 准星提示（参照 `ColdSteelCrosshair` 现有提示绘制）。
2. 按 **E** → 背包与冶炼面板一起打开（背包已开则只补面板）。**按 I／Tab 打开背包不会带出面板。**
3. 冶炼面板：显示当前炉内状态
   - **空闲**：列出可冶炼矿石（读背包中的矿石），选择矿石 + 「开始冶炼」按钮。
   - **冶炼中**：进度条 + 剩余时间（JetBrains Mono），显示产出预览。
   - **完成**：「取出矿锭」按钮 → 产物进背包。
4. 面板打开时 Esc／顶栏 × **只收面板**（背包保留）；关闭背包则**一并收面板**（下次开背包不带面板）。冶炼**继续计时**（不因关面板中断）。

## 7. 实现记录（2026-09-23，用户授权"接着做完"后按本文推进）

两个待确认点按本文推荐口径拍板：**① 进度条取色方向用正向（0% 红 → 100% 绿）；② 锭类物品
铁/铜/银/金 4 种一次做全**。若要改成完全照搬原项目反向，只需交换 `SmeltingProgressColor`
的色标顺序。

- **冶炼输入定为材料线矿石**：`iron_ore / copper_ore / silver_ore / gold_ore`（`category=material`，
  矿镐采集线，描述本就是"可用于后续冶炼与制造"，与路线图"产出与 TemperateHillsProduction
  矿物分布配对"一致）。第 5.1 节列的 `ironOre/copperOre/…` 是祭品线（`category=tribute`），
  本次不作输入——两套 id 语义不同，调研时混写过一次，这里更正。
- **锭类物品**：`items.json` 新增 `ironIngot/copperIngot/silverIngot/goldIngot`（材料类，
  stack 999；稀有度 common/common/rare/epic）。图标为 PIL 程序化占位图（256px 透明底，
  `SourceAssets/SmeltingPanel20260923/make_ingot_icons.py`，回执 `ingot-icons.json`），
  正式渲染图后续按 `ue5-item-asset-workflow` 替换。
- **配方**：`Content/ColdSteelData/smelting-recipes.json`，1 矿 → 1 锭，
  铁 8s／铜 10s／银 14s／金 20s（默认档，数值平衡不在本次范围）。加载器
  `UColdSteelSmeltingSystem`（GameInstance 子系统，`Building/SmeltingSystem.h/.cpp`），
  与 items.json 同口径：进程启动读一次，无热重载。
- **炉内状态**：`FVoxelSmeltingJob{锚格, 配方, StartTicks}`，挂建造世界存档
  （VBX `Version 4→5` 尾块，与 Prefabs 同一"按版本门控追加"的做法；老档读入=没有在炼的炉子）。
  计时为**绝对 UTC**（`FDateTime::UtcNow().GetTicks()`）：关闭游戏也计入，读档天然按差值续算，
  结算清空与发放同事务、重复读档不双发。
- **E 交互**：`ColdSteelWorldInteraction::IsSmeltingFurnace`（占位构件 `PrefabId==blast_furnace`
  且非落体件）；准星提示复用祭坛/宝箱同一条小卡（`ColdSteelCrosshair.cpp`），文案带炉内状态
  （空闲/冶炼中/取出矿锭）；按 E 在 `FPSGAMEPlayerController::InputKey` 分派
  （放在门判定之前）→ `UColdSteelHUDWidget::OpenSmelting`：开背包＋挂左侧面板。
- **面板**：`UColdSteelSmeltingWidget`（纯代码 UMG，外壳三段式与仓库侧板同源：描边 Border →
  `UBackgroundBlur` 9/21 → `GlassTint` → 内容）；宽＝`InventoryWidth/2`、高与背包一致、
  贴背包抽屉左侧中缝 12px（`ColdSteelInventoryTheme.cpp` 布局公式扩展，仓库同开时按剩余空间
  再夹一次，不足则整块收起）；随同一条 `DrawerProgress` 滑入滑出；屏外点击判定已把面板算进
  "内部"。三态按第 6 节：空闲=矿石列表（只列持有的，未持有不生成卡片）＋开始按钮；
  冶炼中=5px 进度条（单色＝当前进度色，四色标线性插值）＋剩余时间（JetBrains Mono）；
  完成=「取出矿锭」。失败原因走面板自己的状态行，不占提示栏（技能规范 2026-09-17 条款）。
  行点击按工程先例走代理 UObject（`UButton::OnClicked` 是动态无参委托）。
- **扣料与退回**：投料 `ConsumeItem`（背包优先、仓库兜底、全有或全无，带原因文案）；
  取出 `AddItem`，背包放不下则任务保留可重试。**拆除高炉**：炉内有冶炼先退料
  （完成退产物、未完退原料），背包放不下就拒绝拆除；**失去支撑脱落**则尽力退料，
  放不下随炉清理并在提示栏点名。孤儿任务读档时丢弃并记日志。
- **字体溢出修正（2026-09-23 用户反馈"字体超出方框"）**：Slate 不裁剪，未开换行的正文在
  半宽面板里直接画出玻璃框——违反正式规则 §3"超长文本换行，不靠缩字号"。修正：
  ① 顶栏只留 20px 标题，长说明移到页脚（12px 辅助档，可换行）；② 所有正文/说明/状态行
  `SetAutoWrapText(true)`（炉况明细、配方行名称与产出注、空态行、状态行、页脚）；
  ③ 滚动条按 §3 设 6px；④ 侧板可用宽 <240px（仓库同开挤压时）整块收起，不出细条。
  字号档位复核：本面板 20/16/14/12 四档合规；字体合同复核：`GunsmithUI::TextFont(Pixels/Scale)`
  与仓库同源、无重复 ×0.75。颜色复核：弱提示 `TextTertiary`、完成 `Success`、失败 `Warning`、
  选中 `ButtonHover`＋2px `Accent`，均取自 `ColdSteelUIStyle` 单一来源。
- **构建**：`Build.bat FPSGAMEEditor Win64 Development` 成功（`Saved/SmeltingPanel20260923/build_editor.log`），
  新 DLL 已落盘；运行中的编辑器不重启，**下次启动生效**。未运行 PIE、未截图，交由用户实机测试。

### 7.1 燃料改造与进度条加粗（同日第二轮，用户追加需求）

用户要求：*"在开始冶炼上新增一个燃料以及剩余燃料的进度条，新增一个添加燃料按钮；现在的进度条
太细了，不明显，可以帮我进行优化加粗，左边积累的进度条做脉冲进度效果，右边新增的进度条加入
一定的粒子动态效果"*。据此把纯挂钟模型升级为**燃料模型（VBX v6）**并重做炉内状态卡。

- **燃料规则（数值默认档，进 `smelting-recipes.json` 顶层 `"fuel"`）**：燃料物品＝`wood`（既有
  材料项，无需新增物品）；每件木材折 **20 秒**燃烧；单炉存料上限 **300 秒**。存料与任务解耦：
  取出矿锭**不清**燃料（下一批直接开炉）；先添料后投矿也可以（`BeginSmelting` 要求存料>0）。
- **进度语义变更**：`FVoxelSmeltingJob{锚格, 配方, ProgressSeconds(已积累), BurnStartTicks(当前
  燃烧段 UTC 起点, 0=停燃)}`。结算式 `burn=min(elapsed, 配方秒数-进度, 存料)`——挂钟照走但**只烧
  存料允许的秒数**，烧完/封顶即停燃；添燃料瞬间续燃。燃料耗尽任务不丢、不退还，等添料。
- **存档**：VBX `Version 5→6`。v6 尾块＝`Smelting`(新结构)+`Fuel`(锚格→秒)；v5 档读入
  `LegacySmelting` 后**迁移**：挂钟已走秒数全额折进 `ProgressSeconds`（封顶配方秒数），燃烧段
  清零、燃料为零（停炉待燃，老档不白送火）；配方下架的 v5 任务丢弃并记日志。读档孤儿判定改为
  "锚格上必须还是高炉记录"，燃料条目同规则（0/负数与孤儿丢弃）。`Tools/Building/read_voxel_save.py`
  同步支持 v5/v6 两段解析（新增 `f64` 读数）。
- **拆除/脱落退料扩展**：炉内**存料按整件折回木材**（`floor(燃料秒/20)`，零头随炉损失）；
  背包放不下仍拒绝拆除（脱落路径尽力退、放不下随炉清并在提示栏点名，与矿料同一口径）。
- **准星提示新增停炉态**：有任务、未完、火已熄 → "冶炼高炉 · 等待燃料"。
- **状态卡重做（双列）**：卡内左右两列各占一半（12px 列距），左＝"冶炼进度"条＋剩余时间，
  右＝"剩余燃料"条＋秒数读数（`%d 秒 · 上限 300 秒`）＋**添加燃料**按钮（36px 统一按钮样式，
  标题 `添加燃料 +20 秒`；无木材或炉满置灰，`CanAddFuel` 预览不改状态）。有炉子上下文时
  双列常显（空炉也显示燃料 0 与添加按钮，先添料后投矿的动线成立）；"取出矿锭"仍整宽。
  页脚改为"炉内有燃料才推进，耗尽即停炉"。状态三态文案：冶炼中（`TextPrimary`＋脉冲）／
  燃料耗尽（`Warning`）／冶炼完成（`Success`）。
- **加粗**：两条进度条 5px→**12px**、圆角半径 2.5→6（`UpdateScale` 与构建期同一常数）；
  轨道色 `Content`、填充圆角刷不变式样，仅加厚。
- **左条脉冲（每帧动画，独立于 0.1s 数据节流）**：燃烧时填充色在四段进度色基础上做
  0.90~1.24 亮度正弦（周期 1.1s），并在填充前沿叠一颗 7×12px 白色圆角"亮头"，透明度
  0.22~0.72 同相位呼吸。动画数据由 `RefreshJob` 写入缓存成员（`AnimSmeltT/bBurning/…`），
  `NativeTick` 每帧只读缓存做表现——数据刷新与动画解耦，节流口径不变。
- **右条粒子（火星）**：`UCanvasPanel` 覆盖在燃料条上，6 颗 2.5~4px 暖色微粒（#F1C13F↔白
  按随机 `Hot` 偏色）沿**填充区宽度**自左向右漂流，上下 ±2.4px 正弦轻摆、独立闪烁相位，
  越靠填充头部越"冷却"（透明度 ×0.45 衰减），漂出 1.0 归零重投并换随机种子。仅当
  存料>0 且填充宽度>2px 时激活（没油不冒火星）。未接 Niagara——纯 Slate 实现零资产依赖。
- **面板挂钟落账**：面板可见期间每 0.1s 调一次 `SettleFurnace`（值真正变化才标脏存档），
  停炉/烧完瞬间写入状态；`AddFuel/Collect/Refund/Begin` 内部也各自先结算，读写不重不漏。
- **构建**：首轮 `build_fuel.log` 报 4 处我方编译错误（UE_LOG 单语句 if/else 需花括号、
  局部名 `Fuel` 遮蔽成员 C4458、`FTimespan::TicksPerSecond`→`ETimespan::`），修复后
  `Saved/SmeltingPanel20260923/build_fuel2.log` **构建成功**、新 DLL 落盘（下次启动编辑器生效）。
  未运行 PIE、未截图，交由用户实机测试。

### 7.2 开合关系定稿＋燃料卡下移＋木材 1 分钟（同日第三轮，用户追加需求后澄清）

用户要求：*"现在打开背包也会出现冶炼界面，这不是设计本意，帮我去除；只跟高炉交互时才打开，
其次帮我拆分冶炼面板上方冶炼部分和燃料部分，燃料部分放到下方，设置木材是燃料，一块木材+1分钟
的燃烧时间"*。

- **开合关系（用户澄清后的定稿）**：高炉 E＝`SetInventoryOpen(true)`＋面板一起开；打开背包
  永远不带出面板（面板只在 `bSmeltingOpen` 时显示，唯一置真入口是 E 交互）。关闭背包时
  `SetInventoryOpen(false)` 一并 `CloseSmelting`（防"下次开背包残留上次面板"）。面板新增
  自己的出口：Esc（`NativeOnKeyDown` 在背包 Esc 分支之前先收面板）与顶栏 ×，可**只收面板
  保留背包**。面板不再跟随抽屉滑入滑出（去掉 `DrawerProgress` 平移），关闭即 Collapsed。
- **布局**：背包开时贴抽屉左侧（中缝 12），背包关时贴视口右缘（12 边距，独立态留作后备）；
  `UpdateInventoryLayout` 用 `SmeltDock` 记录当前贴边距离并参与变化判定（抽屉开合瞬间面板
  跟着挪位）。宽度仍为背包宽一半、<240px 整块收起。
- **上下拆分**：炉况卡（上）＝标题＋冶炼进度通栏条（12px，脉冲＋亮头）＋剩余时间＋取出按钮；
  **燃料卡（新，面板底部、页脚之上）**＝"剩余燃料 · 木材"＋通栏燃料条（火星粒子）＋
  读数行（左：秒数·上限，右：添加燃料按钮）。原双列 `BarColumns` 删除，两条都变通栏
  （`BarColumnPx` 改按整卡内宽）。
- **燃料数值**：`smelting-recipes.json` `fuel.secondsPerUnit` 20→**60**（一件木材＝1 分钟；
  capacity 300 不变＝最多存 5 件），`FColdSteelSmeltingFuel` 默认值同步。界面读数改用
  `ReadableSeconds`（≥60 秒折"X 分 Y 秒"，整分省秒），按钮标题自动成"添加燃料 +1 分钟"。
- 本轮含头文件成员增删（`SmeltDock`、`FuelCard/SmeltSection/FuelSlot`），**Live Coding 不
  支持**，需关编辑器全量构建（21:47 已构建成功落盘）；JSON 数值表在 GameInstance 初始化时
  读一次，**重启 PIE 即生效**。未运行 PIE、未截图，交由用户实机测试。

### 7.3 截图审计与塌高/居中修复（同日第四轮，用户"字体格式、贴图大小位置都错了，自己获取面板看一下"）

用户判定面板字体格式与贴图大小位置有问题，并授权自行抓图核对。新增**冶炼面板视觉审计**管线
（先例＝`run_inventory_visual_acceptance.ps1`）：

- `Source/FPSGAME/UI/ColdSteelSmeltingVisualAudit.cpp`：`UColdSteelHUDWidget::RunSmeltingVisualAudit()`
  仅允许在 `IsAudit()` 隔离档上运行；0.3s/拍相位机＝等世界就绪 → 玩家前/右/远三列探针放高炉
  （`PlacePrefab` 自带支撑校验）→ 配料（目录每种输入 5＋木材 30，摆格走种子同一
  `ColdSteelInventory::Insert`，手拼格子会被 `Validate` 的 Footprint 规则拒绝——首轮实锤）→
  加燃 3 件起**最长配方**（8 秒配方会在加载跳变的世界里两拍之间烧完）→ 开面板 →
  burning / starved（抽干燃料＋进度归零＋燃烧起点拨回现在）/ done（强制满进度）/ idle-rows
  四态各截一屏到 `Saved/SmeltingVisual/` → 收面板拆炉退出。触发：`-SmeltingVisualAudit`
  （PlayerController 12s 定时器），启动脚本 `Tools/UI/run_smelting_visual_acceptance.ps1`。
- 本机实锤的环境约束：standalone 全量 DayNight 世界 1920 直跑会在 PSO/着色器预热时把虚拟内存
  顶到 ~22GB 触发页面文件 OOM（GTX 750 Ti／32GB），审计固定 1280＋`-CpuCount=2`；
  含中文的 `.ps1` 必须带 BOM（harness 的 `pwsh` 实为 5.1，无 BOM 按 ANSI 解析会把脚本体打碎，
  表现为"exit 0 但什么都没发生"）。

**读图定位到的两个真缺陷（都在 `ColdSteelSmeltingWidget.cpp`）**：

1. **进度/燃料条塌成 1px**：`FSlateRoundedBoxBrush` 的 `DesiredSize=0`，填充 `UImage` 在横排里
   没有显式高度就塌成细线——"加粗到 12px"只加在 `BarSize` 轨道上，填充图没吃到。修复＝
   `FillSize/FuelFillSize->SetHeightOverride(12/Scale)`（创建与 `UpdateScale` 两处）。
   像素复核：修复后 y=173..182／592..601，条高 10–12px ✓。
2. **矿石行整体居中、"持有"悬空、名称折行**：`UButtonSlot` 默认 `HAlign_Center/VAlign_Center`
   （引擎 ButtonSlot.cpp），行内容按 desired 收缩居中，Fill 列撑不开。修复＝行槽
   `SetHorizontalAlignment(HAlign_Fill)`。复核：图标贴左缘（x≈224）、"→ 铁锭 ×1 · 8 秒"
   单行不折、"持有 5"贴卡右缘 ✓。

字体档位复核无误（20/16/14/12 四档、数字用 JetBrains Mono，与已验收仓库同源）；
"字体格式错"的观感来自缺陷 2 造成的错误折行与居中。四态截图（burning/starved/done/idle-rows）
＋8/8 审计 checks 全绿。行为修复（第二轮的开合耦合）随本轮构建一并落盘。

### 7.4 双倍速结算 bug＋黑边/通栏整改（次日第五轮，用户"20 秒的金矿几秒钟就完成了；条没贴合框内有黑边；燃料条改成通栏黑色背景条"）

- **时间双倍（`SmeltingSystem.cpp` SettleFurnace）**：落账 `ProgressSeconds += Burn` 后
  `BurnStartTicks` 不推进，而 `LiveProgress` 又在落账值之上加 `Now-BurnStart` → 同一段挂钟计两次，
  显示与 `IsDone` 全双倍速（20 秒配方 10 秒完成）。修复＝整段落账后把段起点推到 `Now`
  （封顶段仍归 0 停燃）。审计实锤：20 秒配方回拨 10 秒后拍得"剩余 8.7 秒"，与真实流逝 1:1。
- **黑边根因（截图像素实锤）**：手拼 `Border+SizeBox+Image` 结构里填充图 10px、轨道 12px，
  上下各露 1px 轨道色。整改＝两条都换成与 HUD 状态条（已验收）同款的 **`UProgressBar`**：
  轨道/填充共用同一几何（`RoundedBrush` 背景＋白填充 `SetFillColorAndOpacity` 染色），
  percent 驱动宽度 → 天然贴合、不溢出、无黑边。
- **UOverlaySlot 默认 `HAlign_Left/VAlign_Top`**（引擎 OverlaySlot.cpp）：ProgressBar desired 只有
  brush ImageSize≈20px，槽不显式 Fill 就缩成小点——四槽（两 bar＋两 ember/head canvas）全部
  显式 Fill。旧手拼结构靠 Border desired 虚撑才没露馅，这类"默认收缩"坑与 UButtonSlot 同源。
- **燃料条定稿（用户口述）**：通栏黑色背景条（与冶炼条同构同宽），存料占比＝填充宽度，
  "添加燃料"即让填充增长；火星粒子保留（画布叠在条上，位置改按缓存几何×percent，恒在条内）。
- 复核：冶炼/燃料条 12px 全高、左右 12px 卡内边距对称（217..518 vs 卡 205..530）；
  四态截图＋8/8 checks 全绿。`SettleFurnace` 属玩法结算，用户实机再验一次出炉时间最稳。

### 7.5 美术升级两批＋燃料区剩余时间（2026-09-24 用户"方向对了，还有优化空间吗"→选定第一批全做→"按你建议优化，同时在下方燃料区显示剩余时间"）

- **A 炉况视觉区**：任务中（冶炼中/停炉/完成）列表区与分区标题收起，同域交给
  "投料图标 → 产物图标＋呼吸光环＋状态小字（出炉待取/冶炼中/停炉待燃）"，补掉面板中部空窗；
  光环色＝完成 Success／燃烧 Warning／停炉灰，α 呼吸 1.8s（完成，栏目脉冲先例）或 1.1s（随条脉冲）。
- **B1 流动高光**：8/20/8 三段白亮带（α .06/.16/.06 假渐变）在填充区内 2.2s 往返，仅燃烧时；
  **B2 完成闪光**：`bDone` 上升沿触发一条 26px 宽带 0.55s 扫满条淡出（技能完成闪光先例）；
  **B3 亮头辉光**：16px 软带垫在 7px 亮头后随脉冲呼吸；**B4 轨道刻度**：25/50/75% 三条 1px α.10 刻线。
  画布不裁剪 → 全部位置数学钳制在 [0, 条宽-带宽]，永不越出条外。
- **C 锚点**：炉况卡标题旁 28px 当前炉料图标（空闲时＝选中配方输入矿）、燃料卡 16px 木材图标、
  "取出矿锭"完成态绿色呼吸描边（Border 包一层，tint α 动画）。
- **燃料区剩余时间**：任务中读数改"存料 X · 还需烧 Y"，`Fuel<Need` 转 Warning 橙（一眼判断要不要添柴）；
  空闲/完成维持"X · 上限 Y"。首轮截图实锤长文本与右侧按钮横向重叠 → 读数与按钮改各占一行，
  按钮通栏＝与"开始冶炼/取出矿锭"同一动作规格。
- 全部动画只驱动装饰绘制（tint/位置/可见性），不改数据与刷新节流。审计新增完成闪光抓拍时点
  （强制完成后 0.3s，落在 0.55s 扫光中段）。两轮 8/8 checks＋截图复核通过；
  本轮含头文件成员新增，须关编辑器全量构建（值守任务在编辑器退出后自动构建成功）。
- **零缝拼接（同日追加，用户"冶炼栏和背包间进行拼接，不要留有间隙"）**：`ColdSteelInventoryTheme.cpp`
  中缝 `Dock=Width+12` 改 `Dock=Width`（背包开＝面板右缘贴抽屉左缘；背包关仍贴视口右缘 12px）。
  截图复核：1280×720（scale=0.666）下面板 190..560 与抽屉 560..1280 边缘相接，无世界背景露出；
  交界处可见的亮带是双方 1px 描边＋抽屉背景模糊的固有边缘光晕（抽屉四边皆有），不是间隙。

### 7.6 批量冶炼＋炉体升级＋升级页签（2026-09-24 用户"是否有批量冶炼功能，如果没有帮我添加。在冶炼栏的左边添加一个类似事件进度栏的扩大箭头小方块，小箭头替换成升级二字，点击后左方弹出针对这个冶炼炉的升级界面"）

- **批量冶炼（VBX v7）**：`FVoxelSmeltingJob.BatchCount`（1..99）；一炉一份任务投 N 份料、
  出 N 份产物，总秒数＝配方秒×N÷等级速度——`JobTotalSeconds()` 单口径供结算/进度/剩余/预览共用。
  面板空闲态新增步进行（−/×N/＋，上限＝持有÷单份投料），开始按钮与预览行同步"×N"；
  领取/退料按 Batch 折算。老档 v6 经 `ReadListV6` 旧布局读入（Batch=1、Level=1，行为不变），
  写侧升 v7；读档过滤保留"零存料但已升级"的燃料记录（等级住在该记录里）。
- **炉体升级**：`FVoxelFurnaceFuel.Level` 1..5，每级 +25% 速度（Lv5=+100%）；
  升至下一级＝铁锭×10×当前等级（10/20/30/40），`UpgradeFurnace` 走 ConsumeItem 全有或全无，
  升级后 SettleFurnace 即时按新倍率缩短在炼任务。只影响这座炉，拆炉连记录清除。
- **升级页签与弹层**：面板根改 CanvasPanel（Shell 满铺），左缘外 34px"升级"小方块
  （事件进度栏扩大钮同思路、文字按要求替换），点击左向弹层：等级/速度/下一级消耗（持有量）/升级按钮/×。
  数字复用 10Hz RefreshJob，不新增定时器。
- **贴屏钳制踩坑（三轮实测）**：本层级 Slate 缓存几何带固定偏移（reported=px+650，widget 的
  AbsX 读数 840 即证），任何从几何反推面板位置的公式都失真；最终由主题层推送真值
  `SetPanelScreenX(Pixels.X-Dock-Smelt)`，弹层放不下时右推盖成浮层、屏幕左缘留 8px。
  1280 审计实拍钳制生效；1920（Scale=1）常态左开不遮页签。
- 审计扩到 9 项：批量 ×3 预览、弹层 Lv.1→点升级→Lv.2（扣 10 铁锭、预览 8×3÷1.25=19.2 秒、
  "furnace upgraded to Lv.2" 落账核验）全绿。

### 7.7 面板滑入动画＋页签点穿修复（2026-09-24 用户"设置冶炼面板跟背包一样以相同的动画从左到右弹出，现在的位置不变；升级放置在冶炼面板左侧的中间，目前按钮点击后关闭了背包和冶炼栏什么都没有弹出"）

- **点穿根因**：页签/弹层挂在 widget 槽边界外的负坐标上——Slate 不裁剪所以看得见，
  但命中测试沿父容器几何递归下降，**出父界的子控件收不到点击**；点击落到世界视口＝左键，
  触发"攻击关 UI"，于是背包和冶炼栏一起被关、什么都没弹出。审计直调 C++ 处理器，绕过了
  命中路径，所以此前 9/9 全绿仍漏掉这个必现 bug。
- **修复＝全宽命中区**：主题层把面板槽位从"面板宽"扩为"屏幕左缘→面板右缘"（右缘仍由
  Offset.Left 贴 Dock），widget 本体改 **HitTestInvisible**（透明区放行世界点击，子控件照常可点），
  Shell/页签/弹层全部用正坐标重排：坐标源＝主题层推送的面板左缘像素真值（`SetPanelScreenX`），
  `ApplyScreenLayout()` 统一换算（Scale 变化/推送时各重排一次），旧的"几何反推＋迭代钳制"全部删除。
- **页签位置**：按用户要求改到**面板左缘垂直居中**（anchors(0,.5)＋Offset.Top=−17/S）；
  弹层同样垂直居中（alignment(0,.5)＋autoSize 自动对中），水平位＝面板左缘−286px、窄屏贴左缘 8px。
- **滑入动画**：HUD Tick 新增 `SmeltMotion`，`FInterpConstantTo(…,4.0f)` 与抽屉 `DrawerProgress`
  完全同速率（0.25s），`SetRenderTranslation(−(1−m)·(视口宽−Dock+24)/Scale,0)`＝自屏幕左缘外
  **从左到右**滑入、落位不变；CloseSmelting 不再瞬时 Collapsed，滑出播完才收起；
  OpenSmelting 的可见性/位移移交 Tick 统一驱动。换炉（SetFurnace）时升级弹层强制收起。

### 7.8 退出改向右收回＋按钮全灭修复（2026-09-24 用户"退出的动画也是向右边收回，重新调整，其次，点击升级按钮，什么都没没有反应"）

- **按钮全灭根因**：上一轮把面板本体设成 `HitTestInvisible`——该枚举**连整个子树一起屏蔽命中**，
  页签与面板所有按钮全部失效（正确语义是 `SelfHitTestInvisible`：本体不挡、子控件照常命中）。
  修复＝widget 本体（Tick）与 RootCanvas（构造）都改 SelfHitTestInvisible。
  教训入档：UMG 三态里"容器放行、子控件可点"永远用 Self 版。
- **退出/弹出动画（三轮定稿＝刚体骑乘）**：第一轮"左来右去"与第二轮"先收面板再收背包的接力"
  均不达标（2026-09-24 用户："我是想把冶炼栏和背包栏视为一个整体，一同收回的"；接力版还叠加
  了关闭瞬间布局把 SmeltWidth 清零导致的"面板被拉伸进背包"错觉）。定稿＝
  **弹出**：E 先开抽屉（原动画 0.25s），`DrawerProgress` 到位后 `SmeltMotion` 起步，
  面板自抽屉左缘背后向左滑出落位（滑距＝面板宽+24，运动中 Z 序 40、落位恢复 42；
  滑距在开着时用 `SmeltSlidePx` 记忆，避开清零问题）；
  **关闭**：CloseSmelting 立即 `SetInventoryOpen(false)` 并置 `bSmeltRiding`，
  抽屉位移公式加长 `SmeltSlidePx`（多出的行程本在屏幕外不可见），面板与抽屉
  **同一条位移曲线**（(1−d)·(背包宽+inset+面板宽+24)）＝一个刚体整体向右缩回，一帧不差。
  审计 burning 抓拍后移一拍（T=9，留 0.6s 接力落位）。

### 7.9 燃料不随时间减少：世界级后台落账（2026-09-24 用户"排查发现一个bug，燃料条不会随着时间而减少燃料也不会减少"）

- **结构性根因**：`SettleFurnace` 的周期调用只活在冶炼面板 `NativeTick`（10Hz）里——面板一关，
  没有任何人落账：燃料与进度全部冻结、存档里也是冻结的，"关闭游戏也计入"的承诺没有兑现处。
  冶炼条显示走 `LiveProgress` 挂钟外推（不需要落账就在走），燃料条读 `FuelAt`（必须落账才动）——
  两条条的"活性"来源不同，正是"进度在走、燃料不减"观感的来源。
- **修复**＝`AVoxelBuildWorld::TickSmelting(Delta)`：世界 Tick 里 10Hz 对 `SmeltingJobs` 全部落账
  （幂等，与面板侧落账交错不双计；只改字段不动数组）。面板关闭、背包收起、甚至没人看炉子时，
  挂钟照常烧料并标脏存档。面板侧 518 行的落账保留（动作瞬间的即时性）。
- **顺带修掉一个真 bug**：`SetFuel(cell,0)` 原来直接 `RemoveAt` 整条记录——零存料升级（
  `SetFurnaceLevel` 建的 0 秒承载记录）会在下一次烧空时**连等级一起删掉**。现在 Level>1 的记录
  只清零不删除（读档过滤本来就保 Level>1，闭环一致）。
- **审计加回归闸门**：T=9 抓拍时记 `Fuel0`，T=10 抽干前判定 `FuelAt<Fuel0−0.15`
  （0.3s 挂钟必须真烧掉 ≥0.15s 存料）。此前审计的"消耗"全部由倒拨 `BurnStartTicks` 的补账驱动，
  实时逐秒消耗从未被单独验证——盲区入档。

### 7.10 燃料行实时倒计时＝锚点外推＋变化门控（2026-09-24 用户"下方剩余时间没有实时更新，帮我做一个性能友好且能实时显示剩余燃料时间的方案"）

- **旧写法的问题**：燃料读数行在 10Hz 的 `RefreshJob` 里每次 `Printf`＋`SetText`——
  每秒 10 次字符串分配＋文本无效化（性能白付），显示粒度却仍是 0.1s 台阶；用户要的是
  "每秒准点跳一格"的倒计时，两头都不占。
- **方案（PaintFuelLine）**：
  1. **锚点**：`RefreshJob`（10Hz）只做校准——`CdFuel/CdNeed/CdStamp=FPlatformTime::Seconds()`
     ＋燃烧标志；`CdNeed` 取 `RemainingSeconds`（内部已含挂钟外推，锚点即真值）。
  2. **外推**：`NativeTick` 每帧调 `PaintFuelLine()`：`显示值＝锚点−(Now−CdStamp)`（仅燃烧中，
     钳 0），与结算频率解耦——就算某帧 RefreshJob 被重帧推迟，倒计时照样逐秒走。
  3. **变化门控**：整数秒（`CeilToInt32`）与文案分支号三者全等就**直接 return**——
     稳态每秒至多 1 次 SetText，其余帧零分配、零无效化；换炉（`SetFurnace`）把门控哨兵打回 −1 强制重绘。
- **锚点窗口误差 ≤0.1s**：添料/停燃/出炉的状态翻转最迟下一拍校准；外推只多减 ≤0.1s，钳 0 兜底。
- 燃料条 percent 维持 10Hz（300 秒烧程对应 1.2px/s，肉眼无台阶感，不值得每帧写）。

### 7.12 升级页四项整改（2026-09-24 用户"竖排字贴缝；弹层大小完全错误；以冶炼栏左边界线为基准弹出收回；燃料倒计时一直显示 10 秒"）

- **页签**：改 36×60 **竖排**（"升\n级"两字由上至下），大小随字收；右缘＝面板左缘零缝
  （alignment(0,.5) 纵向居中，不再手算 −24）。
- **弹层尺寸根因**：上一版画布宽取自 `RootCanvas` 缓存几何——**首帧未测量时回落到创建值
  （全画布宽）**，而且当时函数里引用的 `RootCanvas` 是初始化局部变量（编译期就暴露过一次）。
  定稿＝纯推送值推导：`画布宽＝PanelScreenPx＋LayoutWidth`（主题层保证面板右缘＝画布右缘），
  弹层矩形 `[P−W,P]×全高`，零缓存几何依赖，任何时刻重排都确定。
- **动画改"边界线展开"**：弹层作为独立页面，右缘钉死在冶炼栏左边界线上（RenderTransformPivot
  ＝右中），横向缩放 0→1 向左展开、1→0 收回，同款 4.0/s。放弃"从面板背后滑出"——
  冶炼面板是半透明磨砂玻璃，藏在其后＝穿帮（这就是"动画有问题"的根因）。
- **燃料倒计时 11 项自证闸门**：审计直接读面板读数行文案（`DebugFuelLineText`），
  T=9 记基准、T=10/11 重试、T=12 终判——底层 `FuelAt` 下降＋**文案逐秒变化**双证据，
  卡住即 FAIL 并打印卡住文案。若审计绿而用户端仍见固定值，需按"标题行显示什么"
  （冶炼中/燃料耗尽/冶炼完成）定位停留态：停燃与完成态文案按设计就是冻结的。

### 7.13 空闲燃烧语义（VBX v8，2026-09-24 用户截图定稿"还是没有变化仍然固定10s"）

- 用户截图是**空闲态**文案（"10 秒 · 上限 5 分钟"）：按旧语义"只有冶炼任务才烧料"，
  没矿时存料冻结是"正确"的——但用户要的是**炉内有料就随挂钟持续燃烧（没矿也烧，烧完即熄）**。
  确认为设计变更后全链路落地：
- **数据**：`FVoxelFurnaceFuel` 新增 `FireStartTicks`（火种段起点），存档版本 7→8；
  v7 老档读入火种＝0（读档后首次结算重新起燃，不追溯离线时段），v6 路径同样补默认。
- **结算**：`SettleFurnace` 重构——任务燃烧段照旧（进度与存料 1:1 扣）；任务在烧时火种戳
  只钉到 Now 不重复扣；**无任务/完成/配方下架时火种段独立扣料**，烧尽置 0（熄）。
  原"无任务直接 return"的早退删除。世界 `TickSmelting` 除任务外再遍历有料的炉记录。
- **UI**：`bCdBurning` 从"任务燃烧中"改为"有料即外推"——空闲态"存料 X"逐秒走；
  页脚文案改"存料持续燃烧（没矿也烧）· 有燃料才推进冶炼"。
- **审计**：新增第 12 项闸门——收炉后（无任务）添料 120s，0.6s 后断言 `FuelAt` 下降
  （"fuel burns while idle"）；idle-rows 截图此时应显示"存料 2 分钟"档。

### 7.14 三层滑动统一缓动（2026-09-24 用户"参考背包栏，做高帧率平滑过渡的动画"）

- 进度变量维持 `FInterpConstantTo`（4.0/s＝0.25s 恒定时长，帧率无关，逐帧刷新本就在渲染帧率），
  **在渲染输出处统一过 smoothstep** `T²(3−2T)`（`ColdSteelUI::EaseSmooth`）：起步收尾速度为零、
  中段最快——线性"急起急停"的手感来源就是缺这条缓动。
- 覆盖：抽屉位移＋遮罩/模糊透明度、冶炼面板滑出（SmeltEase）、**骑乘收回共用 DrawerEase**
  （与抽屉同取值＝刚体语义不变）、升级弹层横向缩放（FlyEase）。
- 快捷拖拽（quick-drag）是手势触发开/关、到位用 ZeroVector 直钉，不经缓动，跟手性不受影响。

### 7.15 三轴升级页（VBX v9，2026-09-24 用户"升级栏位参考冶炼栏位…添加最大燃料槽的升级、每次冶炼矿石数升级、右上角的X就没有设计好"）

- **三轴**（同存燃料记录，各自独立、只影响这座炉、同成本曲线 10×当前级 铁锭、封顶 Lv5）：
  ①冶炼速度 +25%/级（v7 旧 Level）；②燃料仓容量 300s+60s×(级-1)（Lv5=10 分钟）；
  ③每次投料上限 5×级（Lv5=25 份；批量步进与 BeginSmelting 都按此夹，兜底 99）。
- **版面照抄面板骨架**：HeaderTint 头部（20px 标题＋**Action("×")** 与面板关闭钮同控件同规格——
  旧版裸文本小方块就是"没设计好"的那个）＋三张 StatusCard 升级卡（名称+Lv.x/5、当前→下一级、
  成本行、整宽升级按钮）＋说明行垫底。UpdateScale 一并重建头部/卡面圆角与按钮高度；
  旧固定 220px 宽残留（会把 ApplyScreenLayout 的动态宽踩掉）作废。
- **容量口径统一**：AddFuel/CanAddFuel 判定、燃料条占比、燃料行"上限 X"全部走
  `FurnaceCapacity(World,Cell)`，不再直接读配置常量。
- **存档 v9**：燃料记录追加 FuelLevel/BatchLevel；v8/v7/v6 读入默认 1（＝旧单轴行为）；
  零存料记录保留条件扩为"任一轴>1"（否则烧空一次会洗掉那条轴的等级）。
- **审计**：夹具铁锭 12→32（三轴各 10 后剩 2 → 按钮"铁锭不足"入镜）；
  升级链 23/24/25 三击 → 26 抓拍 → 27 三轴等级断言（14 项检查）。

### 7.11 升级页签放大贴边＋弹层镜像面板（2026-09-24 用户"放大其所在的小方块，调整位置紧贴冶炼栏左边（参考冶炼栏紧贴背包栏），然后弹出的升级栏大小要跟冶炼栏一样大（直接复制尺寸和打开、收回的动画）"）

- **页签**：34→48px 方块（字号 12→14、圆角/内边距随升），位置＝`PanelX−48` **零缝贴面板左缘**、
  垂直居中；槽 Z 序 1（恒浮在弹层与本体之上，弹层滑过时页签仍可点）。
- **弹层＝面板的左右镜像**：槽改 `anchors(0,0,1,1)` 全画布＋左右留白裁矩形——
  宽＝`LayoutWidth`（与面板同宽）、高＝画布全高（与面板同高）、右缘＝面板左缘零缝；
  窄屏放不下时左缘钳 8px 盖成浮层（1280 审计环境即如此，1920 起为真镜像）。
  内容宽由 `UpgradeFlySize.WidthOverride=P−L−24/S` 随排；说明行 Fill＋Bottom 垫底（页脚语义）。
- **动画＝复制同款**：`FlyMotion` 4.0/s（0.25s），位移 `(1−f)·LayoutWidth/S`——f=0 时弹层矩形
  与面板本体**完全重合**藏其下（槽 Z 序 −1），向左滑出即"从冶炼栏背后弹出"；关闭反向滑回。
  层级链与"抽屉→面板"完全同构：背包→冶炼栏→升级弹层，每层从上一层左缘滑出。
- 可见性统一由 Tick 驱动（RefreshJob 不再直接 SetVisibility）；`SetFurnace` 换炉瞬关弹层
  （FlyMotion=0＋Collapsed＋清零位移，防残影随面板滑入）；`SetLayoutWidth` 宽度推送同步重排弹层。

### 7.16 燃料仓数值调参（2026-09-24 用户"初始 10 分钟…满级 60 分钟"，选项确认＝+10 分钟×5 次升级）

- 配置基线：`smelting-recipes.json` fuel.capacity 300→**600 秒（初始 10 分钟）**，结构默认同步。
- 曲线：`FurnaceCapacity＝capacity×燃料仓等级` → 10/20/30/40/50/**60 分钟**；
  燃料仓轴因此 **6 档封顶**（`VoxelFurnaceAxisMax`：燃料仓 6、速度/批量仍 5）。
- 成本曲线不变（10×当前级）：燃料仓 Lv5→6 花 50 铁锭。
- 卡片"Lv.x / 上限档数"、AddFuel 拒绝文案、燃料行"上限 X"、世界等级夹取与审计全部走
  同一封顶，不再各处写死 5。

### 7.17 冶炼材料建模接入（2026-09-24 用户"金属锭 Blender 建模导入；矿石用强化石的模型做材质替换"）

- **锭**：Blender 程序化铸造块（锥台＋顶面压印＋斜切，68 顶点/70 面）→
  `Tools/Smelting/build_ingot_blender.py` 导出 FBX → UE 无头导入 `/Game/Items/Smelting/Ingot/SM_Ingot`。
- **材质**：`Tools/Smelting/build_ingot_assets_ue.py`（UnrealEditor-Cmd -run=pythonscript）产出
  母质 `M_Ingot`（Tint/Metallic/Roughness 参数）与 `M_Ore_Tinted`（强化石 BaseColor/Normal 贴图采样
  ×Tint），八张实例 `MI_<定义id>`（四锭×金属色＋四矿×矿色）；`pythonscript` 通道在 5.8 的坑：
  `connect_material_property` 是三参数、`TextureObject` 直连 Multiply 会按 texture2D 报错要用
  `TextureSample`、MEL 无 compile_material、改过坏节点无法删只能整包重建。
- **拾取链**（纯 cpp）：`ProductionHarvestAssets::IsMaterial` 纳入四锭；`PickupMesh` 矿石→强化石网格、
  锭→SM_Ingot；新增 `PickupMaterial`＝`MI_<定义id>` 路径；`AColdSteelPickup::InstallProductionMaterial`
  带定义参数并在装网格后覆写槽 0 材质（网格+材质一次批量预载）。石头/木材行为不变。
- **验证**：`verify_ingot_assets.py` 强制加载 11 个资产全部成功、冶炼材质零编译失败
  （仅无关的旧 M_FleshStainV3 失败）。世界矿点岩块外观未动（本次范围＝材料本体）。
- 重跑管线：Blender 脚本→`-run=pythonscript build_ingot_assets_ue.py`（幂等，MI 覆写按名解析）。

### 7.18 存档版本闸门脱钩修复（2026-09-24 用户"建筑存档版本不兼容，这个是你修改导致的吗"）

- **定性：是我的改动导致**。v8/v9 升版本时序列化器加了迁移分支，但 `VoxelBuildWorld.cpp`
  的读取闸门上界仍写死 `Version>7`——v8 存档一存一读就必然弹"版本不兼容，已保留原档"。
- 修复：新增单一版本常量 `GVoxelBuildSaveVersion=9`（VoxelBuildPersistence.h），
  写侧默认值与世界闸门同时引用；报错文案带实际版本号与支持区间，不再只有笼统一句。
  `UVoxelBuildSave::Version` 是 UHT 字面量（=9），注释标明必须与该常量同步。
- **旧档无损**：拒绝加载路径从不写回磁盘，磁盘上仍是完好 v8 档；重编译进游戏后按
  `==8` 迁移分支正常读入（补上 FireStartTicks 缺省与三轴等级=1）。

### 7.19 冶炼系统回头审查（2026-09-24 用户"回头检查一遍冶炼系统，看看是否有bug或者遗漏"）

全链对读（序列化↔迁移↔结算↔世界循环↔UI）发现并修复 **3 个真实缺陷**：

1. **燃料仓 Lv5→6 升级免费**：`UpgradeCostFor` 写死 `VoxelFurnaceMaxLevel(5)` 归零，
   六档轴第 5 次升级被判成"满级成本 0"，UI 同步显示"铁锭 ×0"。改为纯曲线 `10×当前等级`，
   满级判定本来就由各调用点按 `VoxelFurnaceAxisMax(Axis)` 把关（升级/按钮/文案三处核对过）。
2. **拆炉/脱落不清升级记录**：`SetFuel(0)` 的"保等级"分支是为**炉子还在、只是烧空**设计的；
   炉子本体被移除时这条记录变无主残留——**同会话内同格重建新炉会白捡旧等级**（免费升级漏洞），
   只有跨会话才被读档孤儿过滤兜住。修复：手动拆除与脱落两条 `Prefabs.RemoveAll` 路径都补
   `Fuels.RemoveAll(按格)`（退料在其之前已按格完成，顺序核对过）。
3. **TickSmelting 空闲结算迭代器失效（潜在崩溃）**：10Hz 循环用引用式 `for(F:Fuels)` 边遍历
   边调 `SettleFurnace`，而"烧尽且零升级"那拍会 `SetFuel(0)→RemoveAt` 删掉正在迭代的元素——UB。
   任务循环有"只改字段不动数组"注释护身，燃料循环漏了同款约束。改为**先取格快照、再逐格结算**。

顺带：Initialize 里"缺省 300s"过时注释改回 600s；审计追加 2 条回归断言
（"levels erased with the furnace"、"fuel Lv5 upgrade costs 50"），14 项 → **16 项**。

**核对过、无问题的面**：v5-v9 读档迁移链（字段序、缺省、FireStartTicks=0 语义）；写读对称；
任务段/火种段的扣料不重不漏（BurnStartTicks 与 FireTicks 同拍钉桩）；批量与持有量双端夹取；
拆除退料的全有或全无回滚；读档孤儿过滤；容量/速度/批量三轴的封顶与曲线；
`UpgradeFurnace/CanUpgrade` 轴感知满级判定；审计时序断言与拆炉清除顺序兼容（等级检查都在拆前）。

### 7.20 升级页改为「三页签＋下方详情带」（2026-09-24 用户"升级面板下方显示效果与所需材料，字号按冷钢规则规划，别再犯前面的错"）

- **结构**：头部（20px 标题＋同款 × 钮）不变；原三张整卡**压缩成三条可点页签**
  （每行＝轴名 14px＋`Lv.N / Max` 12px，点选切换）；卡列下方新增**详情带**（StatusCard 卡面＋1px 细线分区）：
  显示当前选中轴的完整**升级效果**（`当前 → 下一级`）与**所需材料**（铁锭图标＋名称＋`×需`＋`持有 / 还差`），
  底部一枚标准 36px 升级钮（`已满级 / 升级 / 铁锭不足`）。
- **字号规划（正式规则 §4 四档，杜绝表外字号）**：分区标题 16、正文（轴名/材料名/说明）14、
  数值 16、辅助（标签/Lv/持有）12；纯数值（分钟数、×批量、百分比、成本）用 **JetBrains Mono**，
  中文与混排用 Noto Sans SC——关键信息不再挤在旧卡列的 12px 辅助档（这正是用户点名"前面犯的错误"）。
- **材料口径**：升级到 Lv.N+1 恒需 `10×当前等级` 铁锭；不足时 `×需` 与 `持有/还差` 标 Warning 橙、
  按钮置灰；满级折叠材料行、显示"已满级，无需材料"。成本口径由 §7.19-1 的 `UpgradeCostFor` 单一曲线供给。
- **接线**：页签选择走点击代理 `UColdSteelSmeltingRowProxy::AxisClicked → SelectUpgradeAxis`；
  旧 handler 名保留（`HandleUpgradeClicked` 现升当前选中轴，审计用例不改）；成员换成
  `UpgTabs/UpgTabSurfs/UpgTabNames/UpgTabLv + FlyDetail/FlyDetailName/FlyDetailLv/FlyRuleSize/FlyFx/
  FlyMatRow/FlyMatIconSize/FlyMatIcon/FlyMatValue/FlyMatOwned/FlyNoMat/FlyBtn/FlyBtnText/FlyBtnSize + UpgSel`。
  `UpdateScale` 一并刷这些新尺寸（图标 28²、钮 36px、细线 1px 全随 DPI）。

### 7.21 页签点击失效修复（2026-09-24 用户"升级栏下方子选项不可切换，排查修复"）

- **根因**：v10 页签的点击代理图省事存进了 `RowProxies`——那是配方列表的重建缓存，
  `RefreshRows` 第一句 `RowProxies.Reset()`。开面板（`SetFurnace`）必然触发一次重建：
  页签代理当场失去引用 → 下次 GC 收走 → `AddDynamic` 绑定静默脱钩 → 点击永不落地。
  审计直调 handler 测不到这条链，所以全绿也漏。
- **修复**：新增 `UpgProxies` 专用常驻数组（永不重清），页签代理改存此处。
- **回归**：审计 case 21 展开弹层后先 `CollectGarbage()`（复刻失效环境），再经
  `DebugClickUpgradeTab` 广播**真实 OnClicked 委托链**点三条页签并断言 `UpgSel` 跟变（16→19 项）。
- 顺带：他人并行文件 `ProgressiveInfectionComponent.cpp` 的 C4456（`H` 隐藏声明）阻塞整模块编译，
  做了最小改名 `H→HB` 放行（保留其全部逻辑）。

### 7.22 升级入口方片：居中横排＋贴缝零隙＋跟随弹层推左换"收回"（2026-09-24 用户"升级两字居中放方片、贴紧冶炼栏左边不留间隙；打开后跟随弹层左缘推到最左换成收回，点收回＝关闭升级栏"）

- **文案**：v11 横排试了一轮，用户拍板**竖排从上到下**："升\n级"/"收\n回"14px Medium；
  看着不居中的根因是块内每行默认左对齐——`SetJustification(ETextJustify::Center)` 逐行居中，
  UButton 内容槽整体居中。`UpgradeTabText` 常驻引用，展开态由 `RefreshJob` 换"收回"（`EqualTo` 判等不重设；
  注：FText 无 `operator!=`，v11 首建即栽在此，看守构建失败未被看到，用户测到的是旧二进制——教训：看守构建后必须查结果）。
- **零缝**：观感缝隙来自双方各 1px 描边对贴（非整数 Scale 下再宽 1px）；`LayoutUpgradeTab()` 右缘**压线 2px**，
  方片描边盖到面板描边之上，玻璃对玻璃无缝。
- **跟随**：`NativeTick` 每帧调用，页签位置按 `Lerp(面板缝, 弹层全开左缘, EaseSmooth(FlyMotion))` 与弹层
  `RenderScale` 同曲线同拍左推；1280 宽下弹层左缘仅 8px，页签钳到 x=0 盖在弹层角上（ZOrder 1）仍可点。
- **收回**：页签点击一直是 `HandleUpgradeToggled`（开⇄收互斥翻转），收回态点击天然＝关闭，无需新 handler。
- **v11d（第三轮反馈"没居中"，像素测量定案）**：截图实测方片右缘停在 P 线上、无压线痕迹——那是 **v10e 旧
  二进制**（v11c 构建成功后 17 秒窗口里编辑器被重开，DLL 未换）。教训：交付时要提醒重启时序。
  同时压线 2px→4px（2px 只够贴线，双方 1px 描边的抗锯齿带仍显缝），两字行距 `LineHeightPercentage .88`
  使墨迹块更贴近方片几何中心；实测文字横向本就居中（dx=0，CJK 单字块），纵向小偏差来自行距与描边带。

### 7.23 方片并入主体：去边界保功能（2026-09-24 用户"取消小卡片与冶炼栏、升级栏连接的边界，做成其一部分，保留功能"）

- **做法**：方片**去掉自身描边与卡片底**（`RoundedBrush(Fill,0,Transparent,0)` 直角无描边），
  内钮不再进 `StyledButtons`（共享样式的描边底就是"卡片感"的另一来源），换专用无描边样式：
  Normal/Disabled 全透明，Hover/Pressed 只留轻底色（6px 圆角）。
- **颜色跟随所贴主体**：收起＝冶炼栏 `GlassTint`，展开＝升级栏 `Content`（`bTabVisualOpen` 判变，
  状态翻转才重建画刷）；ZOrder 1 盖在弹层缘上，同色即无缝。压线回落到 1px（只消抗锯齿发丝）。
- 功能不变：点击 toggle、展开换"收回"、跟随弹层左缘动画。`ApplyUpgradeTabVisual()` 统一供给
  构建/UpdateScale/状态切换三处。
- **v12b（2026-09-24 用户"卡片还是圆边角处理"）**：方片改**只圆左两角 8px、右两角直角**——
  右侧是接缝，圆接缝侧会在面板/弹层边线上咬出两个背景缺口（凸舌 tab 的标准做法）。
  新增 `ColdSteelUI::RoundedBrushCorners(Fill,FVector4 半径)`（逐角半径，走 `FSlateRoundedBoxBrush`）；
  hover/pressed 药丸仍 6px 全圆角（轻反馈不涉接缝）。纯函数改动，Live Coding 可热补丁。

### 7.24 发布切片与推送（2026-09-24 用户"废案入 trash、更新 git、沉淀 SKILL、允许推送"）

- **废案核对**：本会话无项目级废案——v10→v12b 全部是同一 `ColdSteelSmeltingWidget.*` 原地迭代；
  各轮候选/看守产物都在 `Saved/`（gitignore，不入仓不归档）。`Tools/Smelting/build_ingot_blender.py`
  经查为在用管线环节（§7.17"重跑管线"），非废案。
- **发布范围**：用户拍板"整套冶炼（后端 v5–v9 + UI 全 19 轮）"，并授权**连带近战会话的
  572d188 一起推**。暂存法：纯文件整加＋`stage_marked_hunks.py`（本次新增的通用逐块过滤工具）
  标记摘块，85 文件 +11777/−29，无二进制、无敏感串、`--check` 干净。
- **顺带披露（用户已裁决"连工作台面板一起发"）**：workbench 面板与冶炼接线**同一 hunk 甚至同一
  行内表达式交织**（抽屉宽度三元 `bSmeltRiding/bWorkbenchRiding` 等），物理不可分；剔除即编译断链。
  故 `ColdSteelWorkbenchWidget.h/.cpp`、`ColdSteelWorkbenchHUD.cpp`、其规划文档与祭坛谓词一并纳入。
- **隔离编译门**：worktree 检出发布提交构建验证。首验（936b61f）暴露 workbench 引用缺口
  （UHT `UColdSteelWorkbenchWidget` 未找到）→ 补齐成 b465f0e。编辑器占用期间 Live Coding 全局
  封锁完整构建，验证＋`git push origin HEAD:main` 交由看守在编辑器关闭后执行：**编译不绿不推送**，
  结果落 `Saved/SmeltingPanel20260923/publish_result.txt`。19 项独立审计仍被启动期环境阻断（第 4 次）。
- **残留本地依赖（不进 git，按第 5 节）**：`/Game/Items/Smelting` 锭网格与 MI、高炉/工作台构件网格
  （`Content/**` gitignore）；复建走 `Tools/Smelting` 管线与两个 SourceAssets 目录。
- **二进制现状**：主树 DLL 已是 v12b（22:07 看守构建，Succeeded）——当前打开的编辑器即圆角凸舌版。

## 8. 剩余工作
- 锭的图标正式渲染图（`ue5-item-asset-workflow`）。
- Niagara 挂点（`NS_CauldronBlacksmith`/`NS_ForgeSparks` → `ChargingMouth/BlastFlange/TapHole`）
  与 `EmberBed` 发光材质实例替换——高炉案例文档已列，属表现侧下一步。
- 放置扣料（构件目前免料，Backlog 第 16 条）。
