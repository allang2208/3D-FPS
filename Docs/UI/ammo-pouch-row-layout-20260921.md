# 弹药袋卡片格式：右侧数量不换行（2026-09-21）

用户反馈：弹药袋里卡片大小不一，右侧子弹剩余数在换行。要求右边数量向左边延展，不要换行把卡片撑高。

入口：Tab → 装备与背包 → 弹药袋子页（`SetInventoryPage(3)` → `UColdSteelAmmoPouchWidget`）。相关合同见 [动态弹种轮盘与弹药袋](../../skills/ue5-ui-umg-slate/references/ammo-radial-and-pouch.md)。

## 原因

类型行的结构是 `[图标][名称／效果／说明 · 可换行][数量][状态]`，数量与状态都是 `AutoWidth` 槽，且都用同一套 `Label()` 建 `STextBlock`，那个工厂把每个标签都设成 `AutoWrapText(true)`。

`STextBlock` 开了自动换行后，期望宽度会跟着“上一次被分到的宽度”走：抽屉变窄（例如同时打开仓库、窗口变小、DPI 变化）时，左侧说明先被压窄换行，横向箱里各槽的期望宽度随之改变，数量的可用宽度被压到数字以下时，`1234` 就被拆成两行。那一行的期望高度因此变大，同一页里各卡的高度不再一致；下一个布局帧又会因为高度变化再算一遍，观感就是卡片忽高忽低。

## 改法（`Source/FPSGAME/UI/ColdSteelAmmoPouchWidget.cpp`）

1. `Label()` 增加第 5 个参数 `Wrap`，默认仍是 `true`，只有右侧数量与状态传 `false`。不换行的文本块期望宽度就是单行宽度，不会再被上一帧的窄宽度带偏。
2. 右侧两列改成**按本页最长内容量出的定宽列**：构建前用 `FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure()` 量出本页最长数量（`NumberFont(16*.75*U)`）、最长状态与最长分组总数（`TextFont(12*.75*U)`），取最大值作为 `SBox::MinDesiredWidth`；量不到文字（没有 Slate 的自动化上下文）时退回 48/36/48×U 的下限。
3. 数量列 `HAlign_Right`：数字贴着右边，位数变多时**向左边延展**，右边界与卡片高度都不动。状态列 `HAlign_Left`，同一页的状态文字左对齐成一列。
4. 分组标题的「N 发」同样不换行并放进定宽列，展开／收起行的高度也不再受总数位数影响。

因为同一页所有卡片共用同一组列宽，左栏（名称／效果／说明）的可用宽度在每张卡上完全相同；说明文字仍是唯一的可换行内容，卡片高度只由文本本身的行数决定，不再由数量的位数决定。

## 边界

| 项 | 结果 |
| --- | --- |
| 数量取值 | 仍是完整整数（`%lld`），不缩写、不省略；列宽只保证同页对齐 |
| 数量极长（超过本页最长值） | 该行数字继续向左延展，不换行、不裁切；不影响其他行 |
| 文案、颜色、等级底色、点击与禁用逻辑 | 未改 |
| 内容键／重建时机 | 未改：列宽由视图模型算出，视图模型没变就不重建 |
| 存档、数量扣除、换弹事务 | 未涉及 |

## 文件范围与状态

- 源码：`Source/FPSGAME/UI/ColdSteelAmmoPouchWidget.cpp`（`Label()` 多一个默认参数、`BuildPage()` 增加量宽与三个定宽列）。头文件未改。
- 新增资源：无。
- 构建：本文件单文件编译通过（`Saved/BuildEditor/singlefile-ammopouch-20260922-002234.log`）；当前 `UnrealEditor-FPSGAME.dll` 已包含本次改动。整模块常规构建因其他任务的在改文件与编辑器占用未能跑完，见下方实施记录。
- 未测试：卡片是否等高、数字是否始终单行、状态列是否对齐、极长数量是否仍完整显示，均由用户实测；本文件不据源码推断实机观感。

## 实施记录（2026-09-21）

- 按上节改动写入 `ColdSteelAmmoPouchWidget.cpp`；括号／花括号平衡、`Label()` 全部调用点参数个数、`SBox` 的 `MinDesiredWidth`／`HAlign` 与字体测量 API 签名已按引擎头文件（`Slate/Public/Widgets/Layout/SBox.h`、`SlateCore/Public/Fonts/FontMeasure.h`）核对，文件仍是 UTF-8 无 BOM、LF 行尾。
- 该文件当时正被另一路弹药袋闪动修复改过（内容键拆分），本次改动落在其 `BuildPage()` 内，未触碰采集与内容键逻辑。
- 编译与验证：
  - 00:22:34 本文件单独编译通过：`[1/1] Compile [x64] ColdSteelAmmoPouchWidget.cpp`，`Result: Succeeded`，日志 `Saved/BuildEditor/singlefile-ammopouch-20260922-002234.log`。
  - 当天更早一次单文件编译（00:00:19）曾被 UBT 拒绝：`Unable to build while Live Coding is active`（另一路会话 23:59:49 打开的编辑器）。用户关闭编辑器后重跑即通过；未结束他人编辑器、未注入 Live Coding 快捷键。
  - 整模块常规构建 `Tools/Build/Build-Editor.ps1` 三次没跑成，都不是本文件的问题：23:59:39 停在 `Characters/FPSBodyAssetPreloader.cpp`；00:22:00 停在 `Weapons/RuneGoldMaterialCommandlet.cpp`（`FindPropertyByText`、`FPropertyChangedEvent`）与 `Weapons/FrostRuneVisualDiagnosis.cpp`（`Weapon`/`Sword` 未声明、序列化重载）；00:23:47 被脚本自身拒绝——另一路会话已于 00:23:41 重新打开编辑器（`Save your work and close the FPSGAME editor before building.`）。按项目规则未修改、未回退、未替他方报告这些文件，也未强杀他人编辑器。
  - 本文件的目标文件 `Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/ColdSteelAmmoPouchWidget.cpp.obj` 生成于 23:58:51（晚于最后一次源码改动 23:58:36，说明当次已被另一路的构建编过且未报错）；`Binaries/Win64/UnrealEditor-FPSGAME.dll` 其后两次重新链接（00:03:54 来自 00:03:31 的成功构建，00:23:27 来自用户关闭编辑器窗口期内的另一次链接），都晚于该目标文件，因此**当前二进制已包含本次改动**。等编辑器关闭、上述武器文件也编过后，仍建议补跑一次常规构建以保证源码与二进制完全一致。
- 结果：代码、文档与单文件编译已完成；未运行 PIE、未截图、未做游戏内验收。卡片是否等高、数字是否始终单行、状态列是否对齐、极长数量是否完整显示，均由用户实测。