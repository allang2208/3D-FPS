# 改造面板的默认项目与退出位置（2026-10-15）

复用当前 `UM4GunsmithWidget` 的 Slate 改造栏、选项区、焦点与关闭入口；本轮只调整项目选择状态，不改变布局、图标或物品改造事务。

## 行为

- 首次打开某个武器实例时，按面板目录顺序选中第一个可用改造项目，移除原先写死的“弹匣”默认值。
- 关闭面板时，记录当前停留的项目；再次打开同一实例时恢复该项目，并将对应栏目滚动到可见位置。
- 记录使用稳定项目 ID，以玩家存档槽和物品 `InstanceId` 隔离。同型号不同实例分别记忆，枪械、近战、法杖、弓与工具沿用同一个面板逻辑。
- 记录保存在本机 `GameUserSettings.ini` 的 `FPSGAME.Gunsmith.Navigation.<ProfileSlot>` 节，重进游戏也可恢复。
- 项目已移除或当前武器不再支持时，沿用面板现有规则回退到第一条可用项目。
- 只保存浏览栏目；退出时未应用的配件或强化草稿仍由既有 `GunsmithSystem::Close()` 丢弃。撤销或取消改造不会把浏览位置恢复成旧栏目。

## 生命周期与修改范围

`M4GunsmithController.cpp` 在 `Begin()` 成功后、创建面板显示前读取对应实例的栏目。在关闭入口中，先记录当前栏目，再移除控件并清空改造会话，避免实例 ID 在析构前丢失。

`M4GunsmithWidget.h` 将初始栏目设为空，由现有 `RebuildWidget()` 按实际可用目录选择第一条；`M4GunsmithWidget.cpp` 在构建完成后将选中栏目滚动到可见区域。普通刷新保留当前选择，没有增加 Tick 读写、控件重建或每次点选写盘。

玩家本地的界面偏好独立于物品数据与主客机改造事务。沿用已有 UIOnly/GameOnly、移动视角锁定、键盘焦点和所有关闭按钮/快捷键入口。

已完成 `FPSGAMEEditor Win64 Development` 常规构建，退出码 0，日志返回 `Result: Succeeded` 并链接保存 `UnrealEditor-FPSGAME.dll`。记录位于 `SourceAssets/GunsmithCategoryMemory20261015/build_console.log` 与 `build_receipt.json`。

未运行游戏、UI 测试、截图或验收。
