# 法杖攀爬／翻越持握手隐藏（2026-09-30）

用户反馈攀爬或翻越时，持杖右手仍留在画面中。源码原因是 `SetWeaponHiddenForTraversal` 只收集 `AKMViewmodel` 子树，而 `StaffAssembly` 与 `StaffV7Arms` 是相机下的独立组件，未进入临时隐藏列表。

## 修改

- `FPSTraversalExecution.cpp` 将法杖装配、V7 持杖手臂及各自子组件纳入现有 `HiddenInGame` 保存／恢复逻辑。锁子甲和手套是手臂的跟随子组件，随源手臂同步隐藏。
- 复用攀爬手臂原有的显示窗口：源时间 `0.06 s` 开始接管，至 `Release + 0.12 s` 收手完毕。正常结束或取消沿用原来的恢复入口，恢复每个组件原先的隐藏状态；不强制修改装备的可见状态。
- `StaffWeaponComponent` 提供只读 C++ 手臂入口 `ArmsMesh()`，不新增反射字段或网络状态。
- 法杖装备期间添加 `PreloadModularOutfit`，临时隐藏时保留已准备的衣袖／手套，卸下法杖时移除。跟随外观仍由源手臂的可见与隐藏状态控制。
- `bHiddenInGame` 时跳过持杖手臂的手动骨骼求值；恢复显示的当帧按当前动作时钟更新姿态。

此次仅调整表现组件的隐藏与资源保留；没有修改右肘姿态表、蒙皮或衣袖资产。

## 交付状态

源码与工作流记录已落盘；`FPSGAMEEditor Win64 Development` 后台构建成功，基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已链接保存。日志：`Saved/BuildEditor/staff-traversal-visibility-20260930.log`（`Result: Succeeded`）。未启动编辑器、游戏、PIE 或渲染，未进行运行测试，实机效果由用户测试。
