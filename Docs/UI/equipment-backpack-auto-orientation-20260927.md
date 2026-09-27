# 装备替换回填背包时自动转向

日期：2026-09-27

## 行为

- 背包右键穿戴、拖入装备槽共用 `ColdSteelInventory::Move`。优先沿用原有朝向与回填位置；空间无法容纳时，再搜索旋转 90 度后的空位。
- 换上双手武器时，把替换下的主手、副手作为同一组规划。搜索允许回退前一件的位置和朝向，只安排此次替换下的装备，不移动其他背包物品。
- 右键卸装、反向拖动换装后需要卸下的副手，同样在原朝向无处可放时尝试旋转。
- 拖入装备槽时，高亮框显示旧装备的实际回填位置和占格；需要旋转时显示自动转向提示。
- 手动拖入背包的那件物品继续使用玩家选择的朝向和落点。自动转向用于卸装回填，不覆盖拖动中的 F 键选择。

## 实现

`ColdSteelSwapPlacement.h` 的候选位置可按需包含第二种朝向，并记录各候选的行高和占用位掩码。先搜索全部保持原朝向的布局，再允许旋转；各阶段先考虑新装备腾出的区域，再考虑背包其余空位。每阶段最多访问 20,000 个候选；未找到完整布局时不写入部分结果。

新选项由背包装备替换显式启用，仓库及普通网格交换保留原有调用行为。`ColdSteelInventoryRules.cpp` 的普通 `Insert` 不变，装备自动卸下使用局部的旋转回退。

成功提案同步保存 `bRotated`、`Width`、`Height` 和 `Cell`，继续由现有模型的 `Generation` 与事务保存机制提交。预览和松手继续调用同一业务规则，无新增存档字段或迁移。

## 交付状态

源码已落盘，`FPSGAMEEditor Win64 Development` 后台构建成功，已链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。构建日志：`Saved/EquipmentAutoOrientation20260927/build-editor.log`，结果 `Succeeded`。

最初沿用已运行编辑器执行 Live Coding，编译日志成功后编辑器报 `Window Creation Failed (Error Code 1158)` 并退出，桥接连接断开。随后在进程和模块释放后完成上述后台正式构建，没有启动或重启编辑器。该次记录保留于同目录的 `live-coding-build.log` 和 `editor-compile-disconnect.log`。

按用户规则未运行测试、游戏、截图或验收，由用户自行测试。
