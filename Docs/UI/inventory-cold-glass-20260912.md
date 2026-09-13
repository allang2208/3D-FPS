# 背包与装备栏：冷钢玻璃同步升级

2026-09-12。用户要求按已接入改造台的风格同步优化背包和装备栏，本次直接落实到 `D:/FPS3D/FPSGAME` 的 UE 5.8.2 游戏。

后续已按用户要求降低透明度至 248/255 不透明度，并扩展为左右等大抽屉及仓库空间网格，见 [仓库升级记录](warehouse-spatial-cold-glass-20260912.md)。字体和配色现已成为 [冷钢 UI 正式规则 v2](ui-cold-steel-design-system.md)，状态页同步见 [状态面板记录](status-cold-glass-20260912.md)。以下为首轮背包装备升级的实现与历史验收记录，原 224/255 与状态页未迁移条款已被后续版本替换。

## 画面与交互

- 原偏蓝、贴满屏幕右边的抽屉改为中性黑灰玻璃，四周保留 12px 留白。真实 `UBackgroundBlur` 限定在抽屉内，强度 9、半径 21；炭灰染色 alpha 为 224/255，压低动态场景细节对文字的干扰。
- 抽屉宽度按窗口的 48% 计算，正常范围 720–1040px，并受视口边界约束；打开仓库时为仓库保留空间，两者边界同步定位。
- 随身装备保留 3×5 的 15 个槽位。已装备卡片显示部位、名称、实际物品预览；较高的卡片补充“当前使用／已装备”。空槽显示部位与“未装备”，双手占用继续使用原规则。
- 空间背包保留 18×4 的 72 格、物品占格与真实附件组合图。名称标签、等宽数量、容量进度、整理按钮、选中银边和悬停底色统一。强化、改造、附魔角标及有效／无效放置色继续保留原语义。
- 背包、装备格、快捷物品和右键操作／拆分菜单共用改造台的 Noto Sans SC 与 JetBrains Mono。使用 20／16／14／12 字号角色，字体从工程内容加载。
- 右键菜单增加局部磨砂、视口内高度约束与内部滚动；常规菜单高度收紧为 336px，拆分为 240px，超出视口时进一步限高。拆分输入框改为深灰与等宽数字。Tab、Caps、Esc、取消和外部点击沿用现有焦点／关闭规则。
- 标题、页签与底部快捷键提示固定，中部独立滚动；窗口变化时更新宽度、文字、页签高度与内边距，避免只改变字体后标题栏被挤压。

这次修改保留状态页、白色物品详情卡、战斗 HUD 与仓库内容的既有业务和专用样式。没有重画物品原始图标，没有引入新的装备类型、容量、配方或存档字段。

## 实现边界

沿用 UMG 抽屉承载自绘背包控件的结构。`ColdSteelInventoryPresentation.cpp` 负责显示，`ColdSteelInventoryWidget::Layout/Hit` 同时决定绘制和命中坐标；所有库存写入继续走 `UColdSteelStatusModel` 的提案、事务与保存路径。展示订阅库存及武器图标事件，窗口布局只在尺寸／DPI／仓库状态变化时更新。

`ColdSteelInventoryTheme.cpp` 复用上轮 `GunsmithUIStyle` 的工程字体和中性灰阶。字体资源、固定版本与许可仍见 [改造台接入记录](gunsmith-cold-glass-implementation-20260912.md)，没有再下载一套系统字体。

抽屉内的 BackgroundBlur 使用 `SelfHitTestInvisible`，允许按钮和物品控件继续接收输入。关闭时保留模型事件清理、菜单关闭、拖动取消和游戏焦点恢复；外部拖放仍按真实抽屉边界判断。右键菜单仍是独立 viewport 根，保留共享外部点击入口。

## 验证

本次先保存并查看旧版实机截图，再检查新界面。第一轮自绘颜色参数出现白底，已修正并保留失败画面 `Saved/InventoryColdGlass20260912/v1-overview-1920.png`；V2 新增审计文件曾因共享构建缓存未收录而链接失败，随后重新扫描源文件并完成构建。没有将这些轮次作为最终视觉验收。

最终 Editor 与 Game Development 均编译成功：`Saved/InventoryColdGlass20260912/build-editor-final.log`、`build-game-final2.log`。已打开的编辑器进程需要重新启动才能载入新原生模块。三个验收 PowerShell 脚本语法检查与本次路径的 `git diff --check` 通过。

已通过的交互回归：`Saved/InventoryDrag/20260912190501-1280.log`，**127 项、0 失败**，涵盖实际 Slate 键鼠拖放、交换、堆叠、拆分、装备、快捷栏、保存失败回滚、失焦取消及多物品交换。针对窄窗，测试先将待操作的背包区域滚入视口，再发送真实指针输入；原事务断言保留。

960×540 的完整拖放回归 `Saved/InventoryDrag/20260912192104-960.log` 同样 **127 项、0 失败**。外部拖动目标根据实际抽屉左边界计算，不再假定抽屉固定占屏幕比例。

新增 `InventoryGlassAudit` 在同一游戏进程内检查 1920、1280、960 和 150% Slate 应用缩放，验证全部 15 个装备槽及 72 格命中、抽屉边界、最后提示可达、右下角菜单限位、工程字体命中和数据不变。它不等同于更改 Windows 系统 DPI，也不代表完成发行包测试。

最终视觉运行 `Saved/InventoryVisual/20260912192504-1920.log`：原视觉检查 **8 项、0 失败**，玻璃／布局检查 **20 项、0 失败**。运行确认 `allow=1 fallback=0 strength=9 opacity=1`，并保留模糊关闭／开启的实机对照；开启后面板背后的 HUD 数字与场景文字变模糊，前景物品保持清晰。半径使用显式覆盖，确保设定的 21 生效。最后一轮也覆盖了收紧后的 336px 右键菜单。

窄窗真实输入边界运行 `Saved/DropHitch/20260912191654-960.log`：**25 项、0 失败**，包含真实鼠标丢弃、弹药保持、落地物理、Tab 取消、仓库和拆分菜单外部关闭。初次失败是审计使用旧布局位置：待拖物品尚未滚入可见区域，且“外部”坐标落进了展开后的仓库。审计现在先滚入物品并使用视口留白作为外部点，原 25 个业务断言未删减；没有通过修改游戏关闭逻辑来绕过失败。

验证期间其他任务也在运行 UE 场景，一次视觉进程因 GPU 竞争由本任务停止后单独重跑；`20260912191654-1920.log` 为中止轮次，不计为通过。这里的掉落运行验证行为，不将繁忙环境中的计时作为帧率或性能结论。

复查入口（PowerShell，项目根；使用独立 Audit 存档）：

```powershell
$env:UE_SKIP_UBT_SDK_SETUP='1'
& Tools/UI/run_inventory_visual_acceptance.ps1 -Widths @(1920) -RenderOffscreen -ColdGlass
& Tools/UI/run_inventory_drag_acceptance.ps1 -Widths @(1280) -RenderOffscreen
& Tools/UI/run_drop_hitch_acceptance.ps1 -Width 960 -RenderOffscreen
```

`UE_SKIP_UBT_SDK_SETUP` 仅避免启动时等待共享工程的并行 SDK 探测，`-RenderOffscreen` 仍使用真实 DX12／Slate 渲染与输入。

## 实机截图

![背包与装备栏](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/overview-1920.png)

[1280 窗口](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/overview-1280.png) · [960 窗口上部](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/overview-960.png) · [960 窗口底部](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/bottom-960.png) · [右键菜单](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/item-menu.png) · [拆分菜单](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/split-menu.png) · [150% 应用缩放](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/ui-scale-150.png)。

毛玻璃对照：[关闭](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/blur-control-disabled.png) · [开启](D:/FPS3D/FPSGAME/Saved/InventoryColdGlass20260912/final/blur-control-enabled.png)。

主要改动为 HUD 抽屉构建、独立布局／字体辅助文件、背包自绘层和操作菜单。已有并行修改继续保留；本次没有整理暂存区、覆盖其他任务或公开提交资产。
