# 强化／附魔工作台：加工状态可视化规划（2026-09-30）

按 [面板／栏目规划模板](panel-column-plan-template.md) 填写，针对 `UColdSteelEnhancementWidget`（`ColdSteelEnhancementLayout.cpp`/`ColdSteelEnhancementWidget.cpp`）。依据：[冷钢 UI 正式规则](ui-cold-steel-design-system.md) §7、[面板与栏目工作流](../../UI-WORKFLOW.md)、[强化／附魔 UI 同步升级](enhancement-cold-glass-20260913.md) 后的现状。

## 目标与范围

- **解决**：面板内容层过平——强化进度只有文字「强化 +N / +M」、附魔占用藏在右侧滚动摘要里、确认成功只有页脚一行字、卷轴粉尘价要悬停才见。玩家难以一眼读出"当前段位 / 词缀是否被占 / 这次附魔要花多少尘 / 刚才那次成了没有"。
- **范围**：只加工件舞台（中央预览头部）与卷轴卡片两处信息密度；不改左目录、右汇总结构、报价／扣除／保存与任何业务合同。沿用现有 `ColdSteelUI` 主题值与字号档，不新增色板。
- **保留**：三栏响应布局、真实预览与视图按钮、强化／附魔页签、264×142 卡片规格、四列对比表、消耗汇总"需要 / 持有"、卷轴仅背包口径、Esc/Tab/K 关闭与控制器输入合同。

## 信息结构

| 元素 | 内容与优先级 | 位置 | 字体／字号 | 显示条件 |
| --- | --- | --- | --- | --- |
| 等级徽章+段位条 | 右侧大号 `+N`（JetBrains Mono 28px，`Enhanced`）+ `/ M` 尾注；其下 `MaxLevel` 个 6px 高分段：已达成=`Enhanced`、下一段=`Accent` 亮银、未满=暗灰 | 舞台头部右上块（标题行右侧，垂直居中） | 28/12px | 选中装备；未选时整组空 |
| 词缀占用行 | 「前缀 <名> · 后缀 <名>」，槽名 `TextTertiary` 12px，词缀名 `Enchanted` 12px，空位显示 — | 舞台头部 `ItemLevel` 行下方 | 12px | 选中装备；未选时清空 |
| 资源芯片 | 顶栏右侧三枚：金/强化石/魔法粉尘，图标 18px + `CountMaterial` 实时数（图标未就绪走字牌回退+限时泵） | 页头标题与 Esc 按钮之间 | 12px Mono | 常显 |
| 成功辉光 | 舞台整面银白薄边+微填充，0.9s 内透明度 1→0，结束 `Collapsed` | `Stage` 最上层 overlay | 不适用 | `Confirm()` 返回成功后一次性播放 |
| 卷轴粉尘价 | 卡片底行「尘 N」（JetBrains Mono 12px），持有 < 需要时 `Warning` | 卷轴卡底行「背包 N」左侧 | 12px | 附魔页签、卡片常显 |
| 确认键文案 | 有效强化报价显示「强化至 +N」（结果等级），否则「确认强化」；附魔页签恒为「确认附魔」 | 底部固定操作区主按钮 | 14px | 随 `Preview.Valid` 切换 |

## 视觉角色

- 段位条复用 `ColdSteelUI::Enhanced`（与背包右上强化角标同一语义色）、`Accent`、`Gray(70)`；单元 16×6px、圆角 2px、间距 3px，15 段约 285px 宽，舞台头部可容纳。
- 辉光刷 `RoundedBrush(Gray(255,34),10,Accent,1.5)`，动画只改 `SBorder` 的 `ColorAndOpacity` alpha；归零即 `Collapsed`，遵守设计系统"RenderOpacity 淡出陷阱"条款不留 1px 描边。
- 词缀名用 `Enchanted`（附魔角标同语义）；不挪用稀有度色。
- 粉尘价沿用 `Warning` 红表达不足，与消耗汇总同一判据 `P->CountMaterial("magic_dust") < Option.Dust`。

## 数据合同

- 段位：`ColdSteelInventory::Number(I,"enhanceLevel")` 与 `UColdSteelEnhancementSystem::MaxLevel`（武器 15／防具 10）；等级徽章与确认键「强化至 +N」取 `Preview.After.enhanceLevel`，与报价同源。
- 资源芯片：`UColdSteelStatusModel::CountMaterial("gold"/"enhancement_stone"/"magic_dust")`，与 `Quote` 中同名材料的 Have 同源（背包＋仓库口径不变）；`OnChanged` 驱动刷新。
- 词缀：`UColdSteelEnhancementSystem::Affix(I,"prefix"/"suffix")`，与右侧「当前前缀／后缀」摘要同源。
- 粉尘：`UColdSteelStatusModel::CountMaterial("magic_dust")`，与 `Quote` 中 `magic_dust` 成本的 Have 同源（背包＋仓库合计口径不变）。
- 辉光：仅消费 `Confirm()` 的返回与 `FPlatformTime::Seconds()`，不写任何状态；`NativeTick` 只做 alpha 衰减与一次可见性切换。

## 状态与输入

- 未选装备：段位条与词缀行清空，不显示占位线；舞台其余不变。
- 已达上限：全部段位为 `Enhanced` 态，无"下一段"高亮；词缀行照常显示。
- 附魔页签下段位条仍显示（附魔装备的强化等级仍是身份状态，与 `ItemLevel` 同义）。
- 辉光期间再次成功重新计时；面板关闭/切换装备不打断（覆盖层在舞台内部，随主体销毁）。
- 不新增输入、快捷键、焦点或滚动变更；关闭合同不变。

## 文件范围

- `Source/FPSGAME/UI/ColdSteelEnhancementWidget.h`：新增 `LevelTrack`、`AffixRow`、`FlashOverlay`、`FlashUntil` 与四支画刷成员。
- `Source/FPSGAME/UI/ColdSteelEnhancementLayout.cpp`：画刷初始化；舞台头部接入段位条＋词缀行；`Stage` 末尾叠加 `FlashOverlay`。
- `Source/FPSGAME/UI/ColdSteelEnhancementWidget.cpp`：`Refresh()` 重建段位条与词缀行；`Confirm()` 成功置 `FlashUntil`；`NativeTick` 衰减辉光；卷轴卡底行追加粉尘价。
- **需要构建**：头文件成员新增，须 `FPSGAMEEditor Win64 Development` 冷编译（`Tools/Build/Build-Editor.ps1`），Live Coding 不适用。
- **预览／测试**：未要求；构建成功仅表示编译通过，画面与交互由用户测试。
