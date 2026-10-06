# 手枪第一人称与身体的深度关系

用户已认可身前 V2 相机位置。新反馈为持手枪低头时出现粉色锯齿／衣服破碎，而第三人称没有；用户确认任何上衣都会出现。本轮保留已认可的相机距离、模型、蒙皮、握姿与动作。

截图的缺口位于近景手臂和裤腿交叠处；原管线将相机手臂和世界身体都用普通深度渲染，因此本轮按两者相交的方向修复。读取已有编辑器时，用户已切换至第三人称 ASH12、七分裤、钢甲手套，没有可见上衣组件；这次读取不构成对截图姿态的复现，也没有自动切枪、开始游戏或截图。

## 接入

- `FPSPlayerBodyComponent.cpp`：在既有本机可见性刷新内，把手枪状态下相机附属的手枪、手臂、裸臂皮肤、手套、衣袖和附件统一标为 `EFirstPersonPrimitiveType::FirstPerson`。复用原有组件遍历，只有值变化才更新渲染状态。双持仍沿同一相机子树。
- `FPSPlayerBodyCamera.cpp`：仅本机第一人称手枪设置 `FMinimalViewInfo.FirstPersonScale=0.25`；第一人称 FOV 与当前 View FOV 相同。这是绕眼位的渲染深度缩放，投影视角和大小不变，避免单独改变袖子与手指／枪械的遮挡顺序。
- 切换武器家族时在 `CalcCamera` 应用对应标记，其他武器恢复普通类型；第三人称继续使用原世界身体与装备，不启用该视图缩放。
- 世界身体、裤子、鞋靴保持原世界深度；不更改组件世界变换、枪口／手部 socket 或命中计算。

依据本机 UE 5.8 `CameraComponent.h` 的 `FirstPersonScale` 注释，该接口用于将第一人称物体向相机缩放以减少场景相交；`CameraComponent.cpp` 与 `PrimitiveComponent.h` 提供对应视图字段及类型定义。没有通过移除衣物三角面处理问题。

## 交付状态

源码已落盘，修改前副本及必要构建日志在 `SourceAssets/PistolClothingRepair20261006`。`FPSGAMEEditor Win64 Development -NoLink` 返回 `Result: Succeeded`，6 个对象编译动作，用时 23.94 秒。随后编辑器已关闭，通过 `Tools/FirstPersonLegs/build_pistol_clothing.ps1` 串行等待已有构建，再执行常规 Editor 构建，返回 `Result: Succeeded / Target is up to date`；基础 DLL 已于 2026-10-06 10:52:14 更新。没有主动关闭／打开编辑器、启动游戏、运行测试或验收渲染；实际遮挡效果由用户测试。
