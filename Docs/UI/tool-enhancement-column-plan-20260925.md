# 采集工具「强化」栏目规划（2026-09-25）

按 [面板／栏目规划模板](panel-column-plan-template.md) 填写。设计总纲见 [采集工具强化系统设计](../Weapons/tool-enhancement-design-20260925.md)；本次只交付规划，不制作、不接入。

## 目标与交付阶段

- **名称、入口、解决的操作需求**：改造工作台第五栏「强化」。玩家在同一个工具工作台里既装改造件、又选强化档位，不用跑到武器强化台（工具本来就不被 `UColdSteelEnhancementSystem::Supports` 接受）。需求＝把 1～5 级金属材质档位可视化选择、预览、应用并持久化。
- **范围与用户已确定的内容**（2026-09-25）：出厂即 1 级石头；独立字段 `tool_enhance_level`；金属／木质分离走 Blender 重导出拆材质槽；覆盖第一人称视模与背包／图鉴图标等级角标；**不含**铁铲、不含 5 级发光特效、**不设消耗、不设强化后数值**。
- **阶段**：方案（本文）→ 待用户确认后进入"代码骨架＋资产拆槽"两条并行实现。预览与测试：未要求，由用户测试。
- **对照的现有面板、实际源码与规范版本**：`M4GunsmithLayout.cpp`（左目录 Rail／中央预览 Stage／底部横向选项卡 OptionScroll／右侧总览表＋详情）、`M4ToolGunsmith.cpp`（工具总览与独立预览）、`M4GunsmithOverview.cpp`（栏目分派）、`M4GunsmithSelectedDetails.cpp`（右侧详情行）、`SMeleePartIcon.h`（程序化矢量栏目图标）、`ColdSteelInventoryPresentation.cpp`（卡片角标）。规范：[冷钢 UI 正式规则](ui-cold-steel-design-system.md)、[面板与栏目工作流](../../UI-WORKFLOW.md)。

## 信息结构与布局

面板 → 无页签（工作台单页） → 左侧栏目（握把／握柄／改件／主部件／**强化**） → 中央预览 ＋ 底部横向档位卡 → 右侧总览与详情 → 底部固定操作区。

| 栏目 | 内容与优先级 | 宽屏位置 | 窄窗／矮窗位置 | 固定或滚动 | 显示条件 |
| --- | --- | --- | --- | --- | --- |
| 左目录「强化」项 | 主：栏目图标（程序化矢量，砧／层叠档位图形）＋名称「强化」16px＋副行「金属材质档位」12px；次：当前等级 `Lv.N` | 左 Rail 第 5 项，排在「主部件」之后 | 同序，Rail 整体纵向滚动 | Rail 内滚动（沿用 `CategoryScroll`） | 仅工具工作台（`IsToolWorkbench()`）；枪械与剑类不出现 |
| 底部档位卡（5 张） | 主：等级序号 ＋ 材质名（石头刃／青铜／钢铁／不锈钢强化反射／紫色强化石）；次：一句外观说明；角标：当前等级「已装备」、当前+1「可强化」、更高档「需先强化到 Lv.N」（禁用） | 中央预览下方横向滚动条（沿用 `OptionScroll`，高 158） | 同位置，横向滚动不变 | 横向滚动 | 选中「强化」栏目时 |
| 中央真实预览 | 工具模型随**草稿等级**即时换金属材质；木柄不变 | 中央区，填满剩余高度 | 同 | 固定（可拖动旋转／滚轮缩放／双击复位） | 工具模型可用时；不可用显示「工具模型暂不可用」 |
| 右侧总览「强化」段 | 行：强化等级（当前 → 草稿）、金属材质（名称 → 名称），末尾一行说明「强化不影响数值」。**既有「采集」「自卫」两段的数值行保持原样**，不因选中强化栏而抹成「—」——那些行反映改造件收益，抹掉会让玩家看不到改造本身的效果（2026-09-25 修正，与设计总纲及实现一致） | 右列总览表内，排在「采集」「自卫」两段之后 | 同列，表体滚动 | 表头固定、表体滚动（沿用现有） | 工具工作台 |
| 右侧详情（选中档位） | 档位名、外观说明、材质资产归属（如实写明"外观改造，无数值"）、消耗与数值两行显示「待定」 | 右列详情区 | 同 | 滚动 | 选中某档位卡时 |
| 底部操作区 | 「应用」「撤销」沿用现有按钮与可用性判断 | 底部固定 | 底部固定，不被内容挤出 | 固定 | 常显 |

- 实际内容区断点、左右边界与中缝：沿用工作台现有响应布局与 `SScaleBox` 舞台，不新增断点，不整体缩小固定画布。
- 标题／页签／确认／页脚固定方式：标题区保持现状两行——「装备改造」20px ＋ 副行「伐木斧   /   采集工具」12px，右上「Esc  返回」按钮、底部操作区不变；「强化」只是左 Rail 多一项。
- **底部选项区标题需要显式来源**：现有实现按 `Model()->Slots(Definition).IndexOfByKey(SelectedCategory)` 反查栏目名，取不到就退回「配件 / 可选配件」。「强化」不是改造槽、不在 `Slots()` 里，因此该栏选中时必须给一个显式标题（「强化 / 材质档位」）与计数（「5 项 · 滚轮浏览」），不能依赖现有反查。
- 长名称、多项目、空列表、溢出：材质名最长「不锈钢强化反射」7 字，档位卡沿用现有卡宽与 `Ellipsis` 截断规则；等级固定 5 项不产生空列表；若目录缺失或等级为 0 项，Rail 该项隐藏并在详情区给「强化工具目录不可用」。

## 主题与资源

| 元素 | 复用主题／组件 | 字体角色与字号档 | 资源来源及加载位置 |
| --- | --- | --- | --- |
| 外壳／分区卡片 | 工作台现有 `GlassPanel`／`PanelBrush`，枪械库背景 `T_WorkshopBackground` 保留 | 不适用 | 现有，`M4GunsmithLayout.cpp` 构造时加载 |
| 标题／正文／数值 | `ColdSteelUI::Text`／`Secondary`／`Muted`；语义色只用现有收益绿、代价红、不变灰 | 标题 20、栏目名 16、正文 14、辅助 12（px 档） | 工程字体：中文 Noto Sans SC，数字 JetBrains Mono（`ColdSteelUI::TextFont/NumberFont`、`GunsmithUI` 像素入口各自保持调用合同） |
| 同级按钮／主要操作 | `NormalButton`／`PrimaryButton`，等宽等高、`MinDesiredWidth(84)`、文字整体居中 | 14 | 现有 |
| 栏目图标 | `SMeleePartIcon` 新增 `enhance` 分支（程序化矢量，与握把／握柄／改件／主部件同风格，不新增位图） | 不适用 | 代码绘制，48×48 |
| 档位卡图标 | 程序化矢量：刃部轮廓 ＋ 等级刻痕（1～5 道），沿用 `SMeleePartIcon` 的银灰面／石墨凹槽风格 | 不适用 | 代码绘制；不使用烘焙 PNG |
| 真实预览 | 现有独立预览静态网格组件（`SetStandaloneToolItem`），按草稿等级替换 `Metal` 槽材质实例 | 不适用 | 材质实例来自 `tool-enhance.json`；等待／失败回退＝保持当前材质并显示「工具模型暂不可用」 |

不新增主题常量、不新建调色板、不挪用稀有度色：稀有度是 6 档语义色（common／uncommon／rare／epic／mythic／legendary），与 5 档材质并非一一对应（epic 紫恰合 5 级紫石，mythic 金不合 4 级不锈钢）。背包角标光晕统一用现有 `ColdSteelUI::Enhanced`，档位信息交给 `Lv.N` 文本；若用户要按档位分色，需先在 [冷钢 UI 正式规则](ui-cold-steel-design-system.md) 新增条款。

## 数据与动作

| 字段或操作 | 模型／业务入口 | 来源范围与过滤 | 单位／排序／公式 | 更新触发 | 确认、扣除与保存 |
| --- | --- | --- | --- | --- | --- |
| 当前强化等级 | 物品 Data `tool_enhance_level`（缺省 1） | 当前工作台实例（背包或已装备，`Place<=1`） | 整数 1～`MaxLevel`；缺字段＝1 | 打开面板、应用后、profile 发布 | 只读 |
| 等级阶梯目录 | `Content/ColdSteelData/tool-enhance.json` → `ColdSteelToolEnhance` | 全目录，按 `level` 升序 | 无公式；`cost`／`stats` 本次恒空 | 目录读盘一次（子系统初始化） | 只读 |
| 草稿等级 | 工作台 widget 自有草稿状态（**不写进 `gunsmith_parts`**） | 同上 | **只允许当前等级 +1**（逐级、不可降级、不可跳级，用户 2026-09-25 确认） | 点击可强化档位卡 | 关闭／撤销丢弃 |
| 金属材质路径 | `ColdSteelToolEnhance::MetalMaterialPath(Item)`，按草稿等级取 | 目录 `materials[definition]` | 资产路径；找不到＝保持现状 | 草稿变化、应用后 | 只读 |
| 应用 | 与改造同一次提交：`Model()->Apply()` 内一并写 `tool_enhance_level` → `CommitState` | 当前实例 | 无 | 点击「应用」 | **本次无消耗、无扣除**；保存走现有 profile 事务；提交后 `ApplyColdSteelProfile` → `RefreshHeldTool` 立即换手上材质 |
| 撤销 | `Model()->Undo()` 同时回退草稿等级 | 当前实例 | 无 | 点击「撤销」／Esc 关闭 | 无写入 |
| 图标角标 | `ColdSteelInventoryPresentation`：右上加工光晕（等级 ≥2 时点亮，色 `ColdSteelUI::Enhanced`）＋ 左下 `Lv.N` 文本芯片 | 背包／仓库中所有斧、镐实例 | `Lv.N`，N＝等级；芯片字号档 12，JetBrains Mono | 物品 Data 变化、卡片重绘 | 只读 |
| 浮窗／图鉴 | 浮窗元信息追加「强化 Lv.N · 材质名」；图鉴「采集工具数值」段附 1～5 级阶梯表 | 浮窗＝该实例；图鉴＝目录（出厂 Probe 无实例等级） | 无 | 打开浮窗／图鉴 | 只读 |

列表、默认选择、显示数量、预览和实际提交使用同一范围（当前工作台实例 ＋ 全目录等级）。不改变物品容量、占格、可用改造件数量、战斗公式；**新增一个持久化字段** `tool_enhance_level`，迁移规则：旧存档无字段按 1 级读取，不写回、不批量迁移；`NormalizeProductionState` 的定义刷新列表不得包含该键。

## 状态与输入

| 状态／触发 | 显示、隐藏或禁用 | 原因文案／反馈 | 选择、焦点、滚动与确认行为 |
| --- | --- | --- | --- |
| 目录缺失／0 个等级 | 左 Rail 隐藏「强化」项 | 详情区「强化工具目录不可用」 | 焦点回到第一个可用栏目 |
| 未选择档位（进入栏目） | 当前档标「已装备」，当前+1 档可选，更高档禁用 | 详情区显示当前等级与材质名 | 默认选中「当前+1」档（已满级则选中当前档）；横向滚动定位到该卡 |
| 已选可强化档（当前+1） | 该卡标「已选 · 待应用」，中央预览换材质 | 详情区列出材质变化、「数值：本次不影响」、「消耗：待定」 | 单击选中；单击当前档或禁用档不改变草稿；滚轮横向浏览 |
| 高于当前+1 的档位 | 禁用，不可点击 | 卡片角标「需先强化到 Lv.N」，详情区说明逐级强化、不可跳级 | 焦点跳过，不进入草稿 |
| 已达最高等级（Lv.5） | 无可强化档，其余全部禁用 | 详情区「已达最高强化档位」 | 「应用」在无改造改动时禁用（沿用 `CanApply` 判断） |
| 材质资产未到位（阶段 1 先于阶段 2） | 预览保持现状材质 | 详情区如实写「外观资产尚未接入」 | 不报错、不弹窗、不阻断改造栏使用 |
| 消耗／数值未接入 | 详情区两行显示「待定」 | 「强化消耗与数值尚未开放」 | 不显示假数字，不显示 0 |
| 应用成功 | 卡片角标与浮窗等级同步刷新 | 沿用现有确认音（`S_Gunsmith_Confirm`） | 面板保持打开，草稿转为已安装 |
| 打开／关闭／失焦／拖放取消 | 沿用工作台现有 `OpenGunsmith`／`CloseGunsmith`：UIOnly、锁定移动与视角、关闭恢复 GameOnly | 关闭时丢弃草稿等级 | 关闭输入不得穿透成世界攻击 |

- 键鼠入口、快捷键、Tooltip 限位、返回游戏与阻止关闭穿透：完全沿用工作台现有入口（背包「改造武器」按钮、J 键、`Esc 返回`），不新增快捷键。
- Construct／Destruct 绑定与释放：草稿等级与材质预览引用在 Destruct 释放；预览材质切换只改组件材质槽，不新建动态材质实例、不留常驻引用。

## 文件范围与交付

- **本次修改文件**：无（本文与总纲设计为唯一交付物）。
- **实现阶段将触及**（供评估，不在本次执行）：`Content/ColdSteelData/tool-enhance.json`（新）、`Source/FPSGAME/Production/ProductionToolEnhance.{h,cpp}`（新）、`ProductionToolAppearance.{h,cpp}`（新）、`ProductionToolComponent.cpp`（含"同实例只改数据"捷径分支必须补一次外观应用）、`UI/M4ToolGunsmith.cpp`、`M4GunsmithLayout.cpp`、`M4GunsmithOverview.cpp`、`M4GunsmithSelectedDetails.cpp`、`SMeleePartIcon.h`、`ColdSteelInventoryPresentation.cpp`、`ColdSteelItemTooltipData.cpp`、`ColdSteelCodexPage.cpp`、`Tools/Production/check_tool_modification_consistency.py`（扩展为同时校验强化目录）。
- **复用资源**：工作台外壳与背景、`ColdSteelUIStyle`／`GunsmithUI` 样式、稀有度色、`SMeleePartIcon` 绘制框架、独立预览组件与取景。
- **新增资源及来源／许可**：`Content/Items/ProductionTools/Enhance20260925/` 下 1 个母材质 ＋ 5 个金属材质实例 ＋（按需）新增 PBR 贴图；优先复用工程内 `Items/ProductionTools/Materials/T_Production_*` 与 `SourceAssets/ProductionToolMaterials20260913/T_MetalRust_00A`、`T_WoodSurface_00A`。用户 Meshy 源与其派生 uasset 保持本机、不公开提交（`AssetSetup.md`「双手伐木斧与矿镐」既有边界）；新增生成贴图的来源与许可记入本轮 `README.md` 与 `AssetSetup.md`。
- **确认退役的文件**：本次无。重导出后若旧 `SM_*`／`M_*` 被替换，按 `trash/<topic>-YYYYMMDD/` 归档并记原路径、字节数、SHA-256、原因与替代物。
- **需要的必要构建**：实现阶段 `FPSGAMEEditor Win64 Development`（`Tools/Build/Build-Editor.ps1`，需在无编辑器进程时执行）；图标重烘需要一次编辑器批次，走 `Tools/AssetPipeline/mcp_call_codex.ps1` 的批次互斥。
- **用户明确要求的预览／检查／测试及交付文件**：未要求，由用户测试。
