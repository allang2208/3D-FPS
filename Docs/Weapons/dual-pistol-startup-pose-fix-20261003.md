# 手枪双持启动姿态修复

## 问题与范围

用户反馈：携带双持 G18 进入游戏，右侧仍是单持双手托握，左侧同时出现副手枪。期望主副手各自使用双持网格与动画实例。

源码定位到共用启动顺序，不是 G18 大弹鼓的换弹姿态配置：

1. UE `APawn::PreInitializeComponents` 可自动调用 `Possess`，早于角色的 `BeginPlay`。
2. `AFPSGAMECharacter::PossessedBy` 原先立即调用 `TryAttachLocalProfile`，恢复装备；`UPistolDualWieldComponent::LoadHand` 为主副手加载双持网格并缓存各自的动画实例。
3. 随后的角色 `BeginPlay` 无条件执行 `InitializeWeaponVisuals`，将主手重建为单持网格和动画实例，再覆盖初始弹药缓存；副手组件仍然存在。
4. 本地档案已标记挂载，不再恢复装备；双持组合也未变化，`MatchesEquipment` 仍匹配。双持主手继续更新旧动画实例，而新主手留在单持待机。

上述初始化和缓存路径适用于当前 `IsDualPistol` 支持的 G18、M1911、Pit Viper 2011、Dan Wesson 715、RSH-12，包括混合双持。这里是源码影响范围，不代表已逐枪运行复现。

## 实现

- `TryAttachLocalProfile` 在角色尚未开始游戏时延后挂载。后续正常 possession/controller replication 保持即时挂载。
- `ApplyColdSteelProfile` 对提前到达的档案同样延后应用；服务器影子档案仍保存在 `NetShadowProfile`。
- `BeginPlay` 在基础视模初始化完成后，统一应用已有影子档案或尝试挂载本地档案。监听服务器的本地主机也使用同一顺序，控制器尚未到达的角色仍由原 possession/replication 入口接续。
- 使用现有生命周期状态，不新增逐帧网格修复、额外装备刷新或 G18 专属补丁。双持动作、弹鼓数值及抓握资产保持原样。

## 排查与交付状态

用户截图与源码调用链为本次问题证据。通过已有编辑器执行只读诊断时，没有正在运行的 PIE 世界，回执为 `Saved/Diagnostics/DualPistolStartup20261003/runtime-before.json`；未为排查启动游戏或改变装备。

源码修改已完成，`FPSGAME Win64 Development` 后台构建成功，产物为 `Binaries/Win64/FPSGAME.exe`，日志为 `Saved/Diagnostics/DualPistolStartup20261003/game-build.log`。

编辑器目标尚未完成本批次落盘：连续等待后，既有 `UnrealEditor-Cmd.exe`（PID 112228）仍在运行资产导入，且随后又有一个原生构建开始。为保留其现场，本批次未覆盖被占用的编辑器 DLL，也未启动、关闭或重启编辑器。占用释放后仍需一次常规 `FPSGAMEEditor Win64 Development` 构建；不可将独立 Game 构建成功视为当前编辑器已应用修复。

未执行游戏回归或逐枪测试，由用户重新进入游戏测试启动姿态。
