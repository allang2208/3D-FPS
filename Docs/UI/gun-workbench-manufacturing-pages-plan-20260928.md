# 枪械工作台：双制造入口

用户要求制作栏上方左右并列两个可点击卡片，分别进入弹药制造和枪械制造。

- **结构**：既有工作台外壳 → 固定标题 → 左侧“弹药制造”／右侧“枪械制造”卡片 → 单一活动制造页 → 对应固定底部操作。使用 UMG WidgetSwitcher 同步切换正文与操作区。
- **布局与样式**：保留现有面板尺寸与玻璃背景；入口等宽，最小高 72px、间距 8px，文字在窄窗可换行；正文独立滚动，顶部入口与底部按钮固定。复用 ColdSteelUIStyle 的银白选中边框、灰底、Noto Sans SC 字体与 20/16/14/12px 档位。
- **页面**：默认枪械页，在本控件生命周期记住最后选择。弹药页包含弹种选择、袋内存量、每次产量及材料表；枪械页保留配方、工件进度、成品参数及小游戏操作说明。切页只改变展示，保留两边选择及当前枪械工件。
- **数据与提交**：弹药复用 CraftingSystem::AmmoCatalog / Craft 及 StatusModel::PouchCount；枪械复用 GunAssemblySystem 和 HUD 的原开始、继续、领取入口。材料仍按背包＋主仓库统计，成品弹药进入弹药袋，枪械沿原领取事务。
- **状态与输入**：当前入口高亮，缺材料及配方为空沿原提示；收展期间禁用入口。切换时滚动回顶部并聚焦对应入口，关闭与面板命中区域继续由原 HUD 管理。只刷新活动页面，库存事件保留隐藏页的脏标记；原 Construct/Destruct 绑定与解绑不变。
- **范围**：ColdSteelGunAssemblyWidget.h/.cpp、ColdSteelGunAmmoCraft.cpp、新增 ColdSteelGunManufacturing.cpp。无需新美术资产或存档迁移。必要后台编译后交付，不主动启动游戏或进行测试。

## 制作结果

双入口、正文切页和固定操作区切页已落盘。用户关闭编辑器后，后台构建 `FPSGAMEEditor Win64 Development` 完成，包含新模块 DLL 链接；日志 `Saved/GunWorkbenchPages20260928/build-console.log` 记录 `Result: Succeeded`，耗时 29.06 秒。未启动编辑器、游戏或执行测试，实际交互由用户测试。
