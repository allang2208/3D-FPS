# 怪物布娃娃共用物理核心，2026-10-02

用户授权：改进倒地物理，保留现有标准起身动画。首轮覆盖护士、胖子、突变体 3、重建巫婆共用的人形控制组件，以及百目的死亡布娃娃。

## 实现与使用

`Source/FPSGAME/Monsters/MonsterRagdollPhysics.h/.cpp` 提供共用原生函数；`UHumanoidKnockdownComponent` 与 `AHundredEyedSlagMonster` 继续持有阶段和生命周期，分别持有一个 `FMonsterRagdollHandoff`。没有新增常驻 Tick 组件、角色基类或 ALS 插件依赖。

- `ReadBody` 在物理读锁内读取刚体世界变换、线速度及角速度。物理期间的目标位置和接地查询使用真实骨盆刚体；定姿和动画预算回退使用骨骼姿势。
- `ContainerRoot` 从真实参考骨架首骨和根／骨盆约束识别辅助容器根，替代胖子、突变体等名称列表。只有辅助根的连接按交接姿势重新锁定；人体关节沿用现有 Physics Asset 的范围。
- `BeginHandoff` 给连接的身体传递一致的刚体运动。`LimitHandoffSpeed` 在最初八个更新帧限制异常线速度；上限至少 200 cm/s，同时计入初始肢体旋转速度和累计重力，保留正常击飞和下落。
- `CapturePose` 在停止模拟前，从真实模拟骨重建姿势快照。保留快照中的骨架缩放链和未模拟骨，避免直接用刚体单位缩放替换百目的根 x100。
- `RebasePose` 将定姿根转换到恢复后的网格坐标，再通过已有动画播放器混合到标准起身动作。
- `FindGround` 使用真实骨盆位置及模拟骨盆包围盒确定支撑查询范围；`IsSettled` 在物理读锁内判断身体线速度和角速度。

人形流程仍为：`Launch/StartDeath` → 物理 → 接地稳定 → 快照定姿 → 选择仰卧／俯卧动作与可用起身空间 → 根坐标转换 → 混合 → 标准起身动画 → 恢复行动。现有击倒触发入口、控制时钟、动画预算回退、8 只／128 刚体／4 个新尸体的物理预算保持原合同。

百目继续在死亡动画 0.42 秒附近交接到自己的 V17 Physics Asset；复用辅助根连接、一致速度、交接限速和刚体接地读取。五秒后，只有接地且低速持续至少 0.35 秒才保存快照、关闭模拟与网格 Tick。尸体仍按原生命周期销毁，没有给百目强套人形起身动画。

## 来源与适配边界

参考 [ALS-Refactored 的动作与布娃娃源码](https://github.com/Sixze/ALS-Refactored/blob/main/Source/ALS/Private/AlsCharacter_Actions.cpp) 的直接刚体读取和八帧初始限速方法。冻结到本次修订的原文、提交 SHA 与来源记录分别在 `SourceAssets/MonsterRagdollCore20261002/Reference/AlsCharacter_Actions.cpp` 和 `provenance.json`；MIT 原始许可在 `Docs/ThirdParty/ALS-Refactored-LICENSE.md`。

这是现有怪物系统的物理核心适配，未安装整套 ALS 角色系统。保留现有 `HasAuthority` 入口；本轮未移植 ALS 的网络目标复制与客户端拉拽，不代表多人布娃娃复制已完成。

本轮不改变普通攻击的击倒触发条件，不新增坠落、抓取或局部受击玩法。原有标准动作和 Physics Asset 继续使用，没有改写动画、模型、地图或蓝图包。

## 交付状态

- 源码已接入上述运行路径；来源和许可随源码落盘。
- 常规 `FPSGAMEEditor Win64 Development` 构建已成功，基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已落盘。构建结果、时间与产物路径在 `SourceAssets/MonsterRagdollCore20261002/build.json`；正式日志为 `Saved/BuildEditor/build-20261002-133550.log`，结果 `Succeeded`，本次常规构建耗时 13.88 秒。
- 构建在用户保存并关闭主编辑器后进行，并等待已有构建和占用 DLL 的后台 commandlet 释放窗口。第一次构建入口被后台 commandlet 占用保护拦截，未编译；等待释放后的正式构建成功。现有对象文件由先前共享 Editor 构建编译，本轮增量复用并成功完成链接；没有使用 Live Coding 补丁充当基础 DLL。
- 未启动编辑器、游戏、PIE、截图、渲染或自动测试。实际倒地、接地、起身衔接与画面效果交由用户测试。

## 现有范围构建收尾，2026-10-02 15:17

用户确认完成前面约定的现有范围。护士、胖子、突变体 3、重建巫婆的倒地／死亡／定姿／标准起身链路，以及百目 V17 死亡物理接入，已完成源码接入和本次普通原生构建。沿用此前已保存的 Physics Asset 与 12 个起身／倒地动画片段，本次没有重新导入或改写动画资产。

- `FPSGAMEEditor Win64 Development`：`Succeeded`，日志 `Saved/BuildEditor/build-20261002-151646.log`，5.94 秒。通过 `Tools/Build/Build-Editor.ps1` 构建，完整 Editor 依赖图增量编译并链接，基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 于 15:16:51 落盘。
- `FPSGAME Win64 Development`：`Succeeded`，日志 `Saved/BuildGame/ragdoll-complete-20261002-151708.log`，14.89 秒。常规 `Binaries/Win64/FPSGAME.exe` 于 15:17:22 落盘。
- 第一次 Game 构建被练习靶两处编译错误阻断。仅修正 `FPSPracticeTarget.cpp` 的公开伤害开关调用和范围命中点的 `FVector` 显式转换，保留其原有行为，再完成上述构建。
- 本次收据、日志和产物时间在 `SourceAssets/MonsterRagdollCore20261002/Completion20261002/completion.json`；此前首次 Editor 构建收据继续保留在 `build.json`。

本次完成的是上述现有范围，未加入多人布娃娃同步。没有启动编辑器或游戏，没有运行测试；接地、关节表现、尸体定姿和标准起身衔接仍由用户测试。
