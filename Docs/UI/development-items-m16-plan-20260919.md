# F6 基本调参：原生成物品下拉增加 M16

2026-09-19，范围依用户后续授权更新：复用 F6 → 基本调参 → 生成物品的现有下拉、数量和生成按钮。M16 已从首阶段模型展示条目变为正式物品 ue_m16a2，显示为 M16A2；不另建页面。

布局沿用已有生成物品卡片、响应式横排／上下重排、冷钢字体与主题。顶部原基本调参、天气环境、怪物生成页签，输入焦点、F6/Esc 开关及 HUD 让位规则保持现有实现。

数据统一来自 ItemCatalog()，M16 与其他武器一样经 AddItem() 入背包并保存。移除手动注入的 dev_model_m16 条目及专用数量上限，沿用原数量框。装备后使用正式持枪资产、5.56 mm 弹药和三连发逻辑。旧模型展示生成函数已确认没有调用方，清理时移入根目录 trash，并从源码移除；当前仅保留正式物品流程。

选择和生成提示归 UDevelopmentPanelWidget；原 FeatureStatus 反馈新增数量／背包不足等结果，不新增状态区或按钮。下拉沿用原选择保持逻辑。

主要文件为 DevelopmentPanelWidget.cpp、DevelopmentPanelTools.cpp 和 Content/ColdSteelData/items.json。武器数值、动作、枪匠与保存接入说明见 [M16A2 三连发](../Weapons/m16a2-gameplay-20260919.md)。没有新增物品存档结构。

资产通过当前编辑器 Python 导入。Live Coding 的补丁应用阶段出现崩溃后，已完成常规 Editor 目标构建并恢复项目编辑器，基础 DLL 已更新。未运行 PIE、截图、回归或视觉验收，由用户测试。
