# 工作台制造栏整改＋制造系统规划（2026-09-25）

> 按 [面板与栏目工作流](../../UI-WORKFLOW.md) 与 [冷钢 UI 正式规则](ui-cold-steel-design-system.md) 编写。
> 需求原话：**冶炼面板下方的加减号没有位于卡片中央；按照最新的冶炼栏规则，重新检查并调整工作台的制造栏；
> 新添加制造系统，接入调整 UI 后的工作台制作系统：木材+石头=伐木斧；木材+2石头=十字镐。**

## 1. 目的与范围

三件事，一次交付：

1. **冶炼面板批量步进行居中修复**：截图像素实测（`−` 钮 x73–100、`＋` 钮 x529–556，卡/动作行 x72–557）
   实锤 −/＋ 被 `Fill` 文本列顶到**行两端**＝贴卡边，不在卡片中央。整改＝步进群
   `[−][批量 ×N（最多 M）][＋]` 作为整体**水平居中**于卡宽（文本不再 Fill 撑满，改 Auto＋两侧 8px 间隔，
   行槽 `HAlign_Center`）。文本中心仍落在卡中线上（两钮等宽等间隔，对称）。
2. **工作台制造栏按最新冶炼栏规则复查整改**：
   - 升级入口方片同步冶炼 **v12/v12b**（§7.23）：去自身描边与卡片底、颜色跟随所贴主体
     （收起＝`GlassTint`、展开＝`Content`）、只圆左两角 8px、hover/pressed 6px 药丸、压线 1px；
     旧实现仍是 v11 前的描边方片＋`StyledButtons` 共享样式（`+2px` 压线），与冶炼现版不一致。
   - 制造列结构对齐冶炼最新定稿：状态卡（图标锚＋标题＋明细）→ 分区标题＋滚动行卡 →
     **居中批量步进行**（与修复后的冶炼同款）→ 整宽主操作 → 状态行 → 页脚。
   - 补上冶炼同款数据节拍：`Model` 订阅（`NativeConstruct/NativeDestruct`）、0.1s 节流
     `RefreshRows/RefreshJob`、签名不变不重建行（保选择与滚动位）。
3. **新增制造系统并接入**：`UColdSteelCraftingSystem`（GameInstance 子系统）＋
   `Content/ColdSteelData/crafting-recipes.json`，首批两条配方：
   **木材×1＋石头×1 → 伐木斧（`tool_axe`）**、**木材×1＋石头×2 → 十字镐（`tool_pickaxe`，工程现名"矿镐"）**。
   即时结算（无计时、无炉内状态、**不改存档版本**）：一次事务内全有或全无扣料＋发产物。

**不在本次范围**：工作台升级轴数值（弹层三页签仍占位可切换）、工具改名（"矿镐"→"十字镐"不改，
配方产物即该工具）、新图标/新模型（复用 `ue_icon` 与现有工具资产）、数值平衡。

## 2. 信息结构（与冶炼栏逐层对齐）

| 层 | 冶炼栏（最新定稿） | 工作台制造栏（本次） |
| --- | --- | --- |
| 头部 | 「冶炼」20px Medium＋× | 「制作」20px Medium＋×（不变） |
| 状态卡 | 炉况卡：28px 炉料图标＋标题 16＋明细 12 | 工作台卡：28px **产物图标**（选中配方的输出，C 锚点同款）＋标题 16（空闲/已选 X）＋明细 12（材料→产物·即时） |
| 列表区 | 「可冶炼矿石」＋行卡（只列持有）＋空态 | 「可制作项目」＋行卡（**全目录常列**，见 §4 显示规则）＋空态「暂无制作配方」 |
| 步进行 | `[−][批量 ×N（最多 M）][＋]` **居中**（本次修复） | 同款同构建同居中；上限 M＝可制作份数 |
| 主操作 | 整宽「开始冶炼 ×N」 | 整宽「开始制作 ×N」（选中才可用） |
| 状态行/页脚 | 12px 反馈行／语义页脚 | 同款；页脚改「Esc 或 × 关闭 · 制作即时结算：扣材料、产物进背包」 |
| 升级页签/弹层 | v12b 无描边凸舌＋同尺寸弹层 | **同步 v12b**；弹层内容仍占位（升级轴后续设计） |

行卡结构（冶炼行卡同款）：`StatusCard` 8px 圆角＋1px 细边、内衬 12/10、整行可点按钮
（`UButtonSlot` 显式 `HAlign_Fill`——2026-09-23 的坑）；行内＝产物图标 28²｜名称 14＋材料行 12（Fill 撑开）｜
右侧「可作 N」12 NumberFont（不足 1 份转 Warning 橙并写「缺 料名」）。选中＝`ButtonHover` 底＋2px `Accent` 细边。

## 3. 布局与尺寸

- 步进行居中：行槽 `HAlign_Center`；钮 30×30（`UpdateScale` 随 Scale）；文本 Auto 宽＋左右 8px 间隔；
  行垂直留白 4/6 不变。两钮与文本同一 `VAlign_Center`。
- 其余留白/滚动条/字号档位全部沿用现值（16px 边缘留白、6px 滚动条、20/16/14/12 四档），不新增断点。
- 升级方片：`LayoutUpgradeTab` 压线 `+2/Scale`→`+1/Scale`、`Padding 0`、外观走 `ApplyUpgradeTabVisual()`
  （构建/UpdateScale/状态翻转三处同一入口，`bTabVisualOpen` 判变才重建画刷）。

## 4. 数据合同（制造系统）

- 目录：`Content/ColdSteelData/crafting-recipes.json`，进程启动读一次（与 items/smelting 同口径，无热重载）；
  坏行逐条跳过并点名，重复 id 只留第一条。
- 行结构：`{id, inputs:[{item,count}], output:{item,count}}`；id 为稳定配方名（`craft_axe`/`craft_pickaxe`），
  item 为 items/production_tools 合并目录的定义 id（`wood`、`stone`、`tool_axe`、`tool_pickaxe`）。
- 持有量口径＝`UColdSteelStatusModel::CountMaterial`（背包＋主仓库，储物箱不参与——与冶炼扣料同域）。
- 可制作份数 `MaxCraftable`＝min(各输入 `floor(持有/单份需)`)，兜底封顶 99；批量 Batch 夹 [1, max(1,M)]。
- 提交 `Craft(Recipe,Batch,Reason)`：`SyncRuntime→Snapshot` 后**本地**逐输入 Deduct、再 Grant 产物，
  全部成功才 `CommitState` 一次＝单事务全有或全无；背包放不下在提交前失败（不扣任何东西），
  原因文案「背包放不下，先整理背包」；材料不足文案「缺少 N 块（背包+仓库共 M）」（冶炼同句式）。
- 显示/隐藏/禁用（新业务自定，UI-WORKFLOW §4）：行**常列全目录**（目录仅两条，隐藏即不可发现）；
  材料不足＝行可选、主操作点击后状态行报原因（与冶炼"选中即可点、失败给原因"同手感）；
  目录空＝空态行；无工作台上下文＝整面板不显示（既有开合不变）。
- 不新增存档字段、不改 VBX 版本；产物即既有工具定义（`stack_max=1`，`Insert` 自动多格拆分）。

## 5. 状态与输入

- 打开/关闭/互斥/骑乘动画：全部沿用既有工作台接线（`OpenWorkbench/CloseWorkbench`、冶炼互斥瞬收），不动。
- 行点击＝选中（代理 UObject 携带配方 id，`UColdSteelWorkbenchRowProxy` 增 `Recipe`＋`Clicked()`；
  代理数组与升级页签代理**分家**常驻——冶炼 v10c 教训）。
- 库存变化（`Model->OnChanged`）→ 下一拍 0.1s 节流刷新签名→重建行/刷读数；选择在同签名下保留。
- 制作成功：状态行「已制作 伐木斧 ×1 · 消耗 木材 ×1 石头 ×1」；失败：Warning 色原因行。
- 批量 −/＋：`HandleBatchMinus/Plus`（UFUNCTION，审计可直调）；越界钮置灰（`Batch>1`/`Batch<MaxBatch`）。

## 6. 文件与资源范围

- 新增：`Source/FPSGAME/Building/CraftingSystem.h/.cpp`、`Content/ColdSteelData/crafting-recipes.json`、本文。
- 修改：`Source/FPSGAME/UI/ColdSteelSmeltingWidget.cpp`（步进行居中：构建＋`UpdateScale` 两处）、
  `Source/FPSGAME/UI/ColdSteelWorkbenchWidget.h/.cpp`（制造列＋v12b 方片＋数据节拍）。
- 复用：`ColdSteelUIStyle`（含 `RoundedBrushCorners`）、`ColdSteelStatusModel` 事务、行卡/代理先例、
  工具 `ue_icon`（`ProductionTools/axe.png`、`pickaxe_upright.png`）。
- 退役：无。Content 资产无改动（JSON 为文本数据表，随源码工作区交付）。

## 7. 交付

- 必要构建：`FPSGAMEEditor Win64 Development` 后台全量（新增 UCLASS，需 UHT）；编辑器若在跑不重启，
  构建结果如实说明（DLL 锁定时交由编辑器关闭后的看守构建）。
- 不运行 PIE、不截图、不验收（用户规则）；实机 E 交互工作台验证交由用户。

## 8. 实现记录（2026-09-25，用户授权"你来负责做面板调整…帮我设置"后按本文推进）

- **冶炼步进行居中**：`ColdSteelSmeltingWidget.cpp` 构建期＋`UpdateScale` 两处——行槽 `HAlign_Center`、
  读数列去 `Fill` 改 Auto＋8px 间隔；新增常驻槽引用 `BatchRowSlot`。截图像素实测的"贴卡两端"即旧 Fill 布局。
- **工作台制造列**：`ColdSteelWorkbenchWidget.h/.cpp` 全量重写内容层——状态卡读数/图标锚、行卡（全目录＋
  可作份数/缺口点名）、居中步进行、整宽主操作、状态行、页脚、`Model->OnChanged` 订阅与 0.1s 节流刷新、
  行/页签代理分家常驻；升级方片同步冶炼 v12/v12b（`ApplyUpgradeTabVisual`、压线 1px、只圆左两角）。
- **制造系统**：`Building/CraftingSystem.h/.cpp`（`UColdSteelCraftingSystem`）＋`crafting-recipes.json`
  （`craft_axe`：wood×1+stone×1→tool_axe；`craft_pickaxe`：wood×1+stone×2→tool_pickaxe）。单事务即时结算，
  无存档版本变化。"十字镐"对应工程既有定义 `tool_pickaxe`（现名"矿镐"），未改名。
- **顺带披露**：并行任务文件 `Production/ProductionToolEnhance.cpp:54` 在 UE 5.8 下 C2665
  （JSON SharedString 键直插 `TMap<FString,FString>`）阻塞整模块编译，做最小显式转换 `FString(Pair.Key)`
  放行（保留其全部逻辑，先例＝冶炼 §7.21）。同轮 `Monsters/InfectedDogMonster.cpp:26` C2672
  （`TObjectPtr` 实参推不出模板裸指针参数），最小改 `Combat.Get()` 放行（语义不变）。
- **构建**：首轮报我方 C4458（`InputsText` 参数名遮蔽成员 `Batch`，改名 `InBatch`）＋上述 C2665；
  次轮报上述 C2672（我方文件该轮编译零报错）。用户关闭编辑器后续建：又遇并行图鉴任务新增类成员
  `bActive` 引发 C4458（我做局部改名放行；随后并行会话自行把成员改名 `bCodexVisible` 并覆写该 cpp，
  01:23 一轮失败实为并行写入的撕裂读）。**终局 `Saved/BuildEditor/build-20260925-012859.log`
  Result: Succeeded（01:30:16 链接 `UnrealEditor-FPSGAME.dll`，含 CraftingSystem／Workbench／Smelting
  全部 obj；复核 run `build-20260925-012705.log` 同 Succeeded、target up-to-date）**。
  未运行 PIE、未截图、未验收（用户规则）；实机 E 交互工作台与冶炼栏居中效果交由用户测试。
- **修复（用户实机反馈 2026-09-25）**：制作面板"点任何按钮都直接关闭"＝`HandleInventoryOutsideClick`
  （`ColdSteelWarehouseHUD.cpp`，左键预览拦截）的屏外判定只排除背包/仓库/冶炼/详情/浮贴，
  未排除工作台面板 → 点在面板上＝"屏外点击"→ `SetInventoryOpen(false)` 连带 `CloseWorkbench()`，
  且预览层返回 Handled 把点击吞掉（按钮本身毫无响应）。按冶炼先例补 `InWorkbench` 排除项
  （`bWorkbenchOpen&&WorkbenchWidget` 几何命中），面板内点击不再触发连带关闭。
  该 cpp 需补 `#include "ColdSteelWorkbenchWidget.h"`（完整类型才能取几何）。
  修复后构建 `build-20260925-015000.log` Result: Succeeded（DLL 已链接）。
