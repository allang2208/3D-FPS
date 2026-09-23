# SVD ADS 模型闪现排查与修复（2026-09-23）

用户反馈：SVD 进入 ADS 后持续闪动，有模型瞬间出现又消失。本次检查范围为枪械开镜、镜内遮罩和角色身体组件对第一人称网格的可见性写入；没有启动 UE 编辑器、游戏或视觉回归。

## 根因与代码证据

`AFPSGAMECharacter::Tick` 每帧调用 `UpdateScopePresentation()`，在 `GetScopePresentationAlpha() > 0.5` 时，对 `AKMViewmodel` 及其全部子组件设置 `OwnerNoSee=true`。SVD 的枪体、镜筒与 Manny 手臂都属于这一视模。

`UFPSPlayerBodyComponent::BeginPlay` 通过 `AddTickPrerequisiteActor(Character.Get())` 明确让身体组件在角色 Tick 之后执行。其 `TickComponent` 每隔 0.2 秒执行 `UpdateOwnerVisibility()`，遍历第一人称相机的子组件，将 `OwnerNoSee` 写为 `bThirdPerson`。在第一人称模式下，该值为 false，因而在开镜隐藏之后又把同一批网格解除隐藏。下一帧角色 Tick 又把它们隐藏，形成每隔约 0.2 秒持续一帧的模型闪现路径。

第一处错误状态是身体组件覆盖了瞄准镜已应用的隐藏请求。该结论来自实际源码的写入条件及 Tick 前置依赖；没有采集运行录像，不把源码诊断称为实机复测。可见性翻转还会触发渲染状态重建。旧版 `ScopeHiddenParts.Add` 会在每次重新隐藏时重复记录同一组件。

镜内 Widget 只绘制镜框、分划和开火反馈，没有上述模型可见性写入。武器姿态、UV/材质修复和模型资产本轮没有改动。

## 修改

- `Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp`：相机子组件的拥有者隐藏值采用 `bThirdPerson || ScopeHiddenParts.Contains(Primitive)`，保留瞄准镜已经登记的隐藏请求。
- `Source/FPSGAME/Weapons/M4GunsmithVisual.cpp`：用 `AddUnique` 登记；若第三人称已隐藏视模，也登记瞄准镜请求，防止切回第一人称时误显示；退出 ADS 时释放镜内请求，同时保留第三人称隐藏值。仅状态变化时调用 setter。
- SVD 原厂 PSO-1 与 LPVO 共享此逻辑，均覆盖；不修改固定倍率、射线、后坐力或 HUD 画法。

修改前两份源码保存在 `Before/`。仅供本次定位对比，不能整份覆盖并行工作区。

## 构建与交付

常规后台 Editor 构建已完成：`Result: Succeeded`，5 个构建动作、5.84 秒（不含构建锁等待）；两个修改的 `.cpp` 均编译，并完成 `UnrealEditor-FPSGAME.dll` 链接落盘。完整输出为 `build_editor.log`，UBT 日志为 `Saved/BuildEditor/build-20260923-094943.log`。未启动编辑器或游戏，未进行运行视觉复测。

交由用户复测的最小场景：第一人称装备 SVD，待装备动作结束，保持 ADS 数秒，观察镜内是否仍有枪体/手臂闪现；松开 ADS 后应恢复持枪显示。相邻边界为 ADS 中切换第一/第三人称，以及装 LPVO 的枪械相同操作。这些运行场景本次未执行。
