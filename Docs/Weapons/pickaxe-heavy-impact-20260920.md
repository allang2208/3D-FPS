# 矿镐沉重命中反馈 — 2026-09-20

用户要求：参照伐木斧，增加强打击感、屏幕抖动和停帧。镜头沿用此前确认的单次大幅跳动，不使用高频震荡。

## 本轮调整

- 确认击中可采集资源或敌人后，动作停住 0.24 秒。
- 命中后 0.24–0.42 秒，双手与矿镐整体绕握持中心小幅上下撬动，峰值为 +2.4° / -1.6°。保持接触姿势，不单独扭转手腕和肘关节。
- 命中后 0.42–0.51 秒，播放现有动作的快速拔出段；0.51–0.80 秒回到待机。
- 镜头命中后 0.04 秒达到单次下顿峰值：俯仰 -10.5°、垂直位移 -3.4 cm；短暂保持后平滑回正，0.51 秒归零。抽回时不追加第二次大幅震动。
- 挥空保留较轻的蓄势与下砸跟随，不触发命中停顿、撬动或强镜头冲击。
- 动作、命中判定和镜头继续共用工具组件的时间轴。命中时钟从接触点开始，不暂停世界时间。

## 时序与接入

接触仍在攻击开始后 0.60 秒，挥空仍为 1.16 秒；确认命中后的完整动作延长到 1.40 秒。每次攻击仍只结算一次接触，伤害、装备条件、采集距离及背包图标沿用上一版。

保留 `PickaxeSightline20260919` 的现有 Swing / HitRecover 动画资产，本轮只重映射命中回收的播放时间并增加刚体运动，没有重烘焙动画或修改骨骼局部旋转。

实现位置：

- `Source/FPSGAME/Production/ProductionPickaxeImpactMotion.h`：时间参数、回收采样、撬动角度和单次镜头曲线。
- `Source/FPSGAME/Production/ProductionToolMotion.cpp`：动画重映射及矿镐镜头接入。
- `Source/FPSGAME/Production/ProductionToolComponent.cpp`：确认命中后的动作结束时间。
- `Source/FPSGAME/Production/ProductionAxeLocomotion.cpp`：双手与工具整体撬动。

可通过 `fps.Tool.PickaxeCamera` 调整矿镐镜头幅度：默认 `1`，`0` 关闭矿镐镜头运动。

## 交付状态

源码已修改，通过当前编辑器的 MCP Live Coding 编译并热更新，返回 `Result: Success / Live coding succeeded`。编译记录保存在 `SourceAssets/PickaxeImpact20260920/live_coding_result.json`。本轮没有重编正式基础 DLL。

未主动运行 PIE、测试或验收渲染，手感由用户在游戏中测试。

## 用户反馈：攻击怪物没有新增反馈

2026-09-20 用户反馈打怪时没有新增效果。沿命中调用链读取发现：`ResolveContact` 对无资源 ID 的敌人命中调用 `ResolveAxeEnemyContact`，后者在伤害生效或击杀后返回成功；随后同样进入 `bHitConfirmed`、停帧、回收和矿镐镜头曲线。因此源码没有把反馈限制为矿石。

本次定位到运行版本落后：当前编辑器 PID 22476 于本地时间 00:28 启动，进程模块列表仅加载正式 `UnrealEditor-FPSGAME.dll`；该 DLL 修改时间仍为 2026-09-19 23:41:21，早于本轮反馈源码的 2026-09-20 00:06:40 及 Live Coding 成功记录的 00:10:22。新进程未加载上一进程的补丁。

处理：用户保存并关闭编辑器后，于 2026-09-20 07:41 运行 `Tools/Build/Build-Editor.ps1`，常规 Editor 目标构建返回 `Result: Succeeded`（16.31 秒），已链接正式 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。本次版本问题未再改动伤害或动画曲线。

构建日志：`Saved/BuildEditor/build-20260920-074120.log`。下次启动编辑器会加载正式 DLL 中的矿镐反馈；未启动 PIE 或进行实机测试，交由用户测试。
