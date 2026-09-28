# 工作台制造栏复制升级：对齐打铁栏/枪械装配栏规格 · 2026-09-28

用户要求：核对打铁栏（锻造 · 铸造台）与枪械装配栏（制作 · 枪械工作台）当前的布局、规格与栏目大小，
对工作台制造栏做同规格"复制升级"。

## 升级前现状

- 打铁栏/枪械装配栏：**全宽抽屉**（与背包等宽 720–1040px、零缝拼接、上下 12px），卡式版面——
  页头 20px 标题＋36px 方钮关闭；Scroll→StatusCard 卡列（12px 内沿、8px 卡距）：配方卡
  （ComboBox＋**材料三列表**：材料｜持有/需要｜状态，数字 JetBrains Mono 右对齐、不足标红报差额）、
  状态卡（阶段 16 Medium＋读数 16 Mono＋图例 12＋3px 细进度条）、成品预览双列（成品图｜参数卡两列表，
  高度随视口夹取 200–420px）、操作说明卡（14/12/12 三档）；页脚 HeaderTint 带＝状态行＋36px 整宽主操作。
- 工作台制造栏（升级前）：**半宽窄列**（抽屉的 50%，≈360–520px），复刻冶炼栏格式——
  行卡列表选配方＋状态卡图标锚＋页脚散排。另含已被装配面板接管的枪械分支死代码。

## 本轮改动

**版面（ColdSteelWorkbenchWidget.{h,cpp} 重建，逐参数取自 ColdSteelForgingWidget）：**
- 中段改 Scroll→Body→卡列：配方卡（caption 12→标题 16 Medium→**ComboBox 下拉**（36px、列表 240、
  ItemStyle 同打铁）→所需材料 14→来源 12→材料三列表）→状态卡（阶段 16/读数 16 Mono/图例 12；
  制作即时结算，**无进度条——无对应机制不造字段**）→成品预览双列（左产物图标 ScaleToFit 等比居中、
  右参数卡：PreviewName 16＋两列参数表，数据走 `BuildColdSteelItemTooltip` 摘要＝与物品浮窗同口径）→操作说明卡。
- 页脚 HeaderTint 带：状态行（14，错误标 Warning）＋居中批量步进行（保留工作台特有批量）＋整宽 36px「开始制作」。
- 行卡列表→ComboBox：换配方清批量；换台重置选择与批量（默认选第一项，"选中即可点"手感同打铁）。
- 材料需求＝单份×批量，"所需材料"标题随批量注明；状态列 充足/缺 N（Success/Danger）。
- 字体全走 GunsmithUI 像素入口、所有 padding/尺寸 ÷Scale，`UpdateScale` 缓存数组重排（Cards/Buttons/
  ButtonSizes/RowSpacings/MaterialCellSlots/PreviewCellSlots），滚动条 6px，页头/页脚 padding (18,12)/12。

**宽度（ColdSteelWorkbenchHUD.cpp ＋ ColdSteelInventoryTheme.cpp）：**
- 挂载基准 360→720（BuildWorkbench，同 ForgingSlot/GunAssemblySlot 参数）。
- `UpdateInventoryLayout`：非枪械工作台打开时 `WB=min(Width,Leftover)`（原 `Width*.5f`），
  并把非枪械工作台并入抽屉对半夹取（`bWBOut`），保证 面板＋左缘升级弹层＝2×宽 仍在视口内；
  仓库同开的 Leftover 钳制与 <240 收起守卫保留。

**死代码清除：**
- 工作台的枪械分支整路删除（`ColdSteelGunWorkbench.cpp` 文件、`RefreshGunWorkbench/HandleGunCraft/
  bGunWorkbench/GunMaterialLabels/GunPartLabels/GunActionMessage/SelectRecipe/行卡代理 Clicked/Recipe`
  与 SetWorkbench 的 `bGunStation` 参数）——枪械工作台自 09-27/09-28 起由 `UColdSteelGunAssemblyWidget`
  接管，HUD 只以 `SetWorkbench(World,Cell)` 两参调用。
- 升级页签＋弹层（冶炼 v10-v12b 结构）原样保留，未动。

## 交付

`FPSGAME Win64 Development` 构建 Succeeded（2026-09-28，本轮编译 4 次收敛：bGunWorkbench 残引、
Content 遮蔽 C4456、RefreshRows 残引逐一修复）。未启动编辑器/PIE/截图；实际版面由用户热编译后验收。
冶炼栏仍为半宽（本轮只升级工作台制造栏，冶炼如需同款另开一轮）。
