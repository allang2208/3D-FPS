# 抽屉贴右边缘与打开时的 HUD 让步（2026-09-16）

## 需求

装备栏（共享抽屉）位置贴近右边屏幕边缘，弹出／收回方式不变；抽屉为弹出式；打开抽屉时隐藏右侧栏目按钮（人物状态／背包／技能入口）、时钟面板与右下角武器详情面板。

## 修改

- **抽屉贴右边缘**：`ColdSteelUI::NavigationDrawerInset` 由「入口宽度 + 间隔 + 12」改为 `0`。该常量只有三个使用者——`UpdateInventoryLayout` 的抽屉右偏移、抽屉滑出距离、以及背包内部内容的右侧留白——所以改一处即等于"抽屉右缘＝视口右缘、内容用满整幅、滑出距离＝抽屉自身宽度"。弹出／收回的 `DrawerProgress` 插值（4.0/s 匀速）与 TAB／Caps／P 键位**未改**。
- **打开抽屉时让步**（条件统一为 `bInventoryOpen || DrawerProgress > KINDA_SMALL_NUMBER`，即收起动画播完才恢复）：
  - `ColdSteelPanelNavigation.cpp`：右侧入口列（人物状态 Caps／背包 Tab／技能 P）改为 `Collapsed`；未打开时保持原行为（显示光标为 `Visible`，否则 `HitTestInvisible`）。
  - `ColdSteelHUDWidget.cpp`（抽屉 Tick）：世界时钟 `WorldClock` 改为 `Collapsed`。
  - `ColdSteelHUDWidget.cpp::RefreshAmmo`：右下角武器详情（`AmmoReadout`）在抽屉出现期间强制 `Collapsed`，覆盖其自身 `HitTestInvisible` 的恢复（该面板原有逻辑只在 `MenuOpen` 为真时收起，角色指针为空时会漏掉，这里一并兜住）。恢复仍由它自己的 `Refresh` 负责。
- 依源码依赖补 `#include "ColdSteelWorldClock.h"`（原来只有前置声明，直接设可见性会编译失败）。

## 保持不变

- 抽屉与仓库的配对规则不变：仓库打开时两者各取 `(视口-24)/2` 宽，中间保持 12px 间隙，仓库仍从左侧滑入。
- 页签切换在抽屉打开时改用键位：Caps 人物状态、P 技能、Tab 关闭（菜单内已无重复横排导航，入口列本次按需求隐藏）。
- 状态页／技能页与背包共用同一抽屉，因此三页在打开时都会让出右侧 HUD。

## 构建与边界

## 追加：删除左缘「Caps 角色状态」入口（2026-09-16）

用户要求删除左边缘的角色详情 CAPS 按钮。该按钮由 `ColdSteelCharacterSheet.cpp::BuildCharacterSummary` 建立（`MakeReferenceText("Caps  角色状态")`，锚点 `FAnchors(0,.5f)`、x=16），即屏幕左缘垂直居中的那一个；本次直接移除该构建代码，`BuildTopVitals` 保留。

- 入口仍在：`Caps` 键继续经 `HandlePanelShortcut` 打开角色状态页；抽屉右缘的「人物状态」入口在抽屉未打开时照旧可用（打开时按上一节隐藏）。
- 抽屉页脚 `Tab 收起 · Caps 状态 · P 技能 · 右键物品操作` 文字提示保留（Caps 仍然有效）。
- 必要构建：`Tools/Build/Build-Editor.ps1`（编辑器已关闭）→ `Result: Succeeded`，日志 `Saved/BuildEditor/build-20260916-214132.log`，编译 `ColdSteelCharacterSheet.cpp` 并链接 `UnrealEditor-FPSGAME.dll`（21:41:49）。

- 必要构建：`FPSGAMEEditor Win64 Development -ModuleWithSuffix=FPSGAME,9162351` → `Result: Succeeded`，产物 `Binaries/Win64/UnrealEditor-FPSGAME-9162351.dll`，日志 `Saved/BuildEditor/drawer-edge-build-2.log`（首次 `9162350` 因缺少 `ColdSteelWorldClock.h` 包含失败，已修复后重编）。
- 构建时用户编辑器正在运行，采用后缀模块；需重启编辑器加载新模块。
- 未启动游戏、未截图、未做视觉验收，实际位置与让让效果由用户测试。
