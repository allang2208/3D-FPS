# 战锤冲刺就绪无进度：排查记录

用户反馈：持战锤按住 Shift 向前跑，冲刺攻击进度不出现或不增长。旋风 V3 已确认保存：`Content/Weapons/SteelWarhammer20261014/WhirlwindV1/A_Warhammer_Whirlwind.uasset`，保存时间 2026-10-14 22:58:59，修订 `LeftReleaseV3_20261014`。

## 当前结论

**用户已确认重新进入游戏后，战锤冲刺进度恢复正常。** 本次排查结束。冲刺蓄势公式、门槛、动作、伤害与范围没有改动；本轮正式编译已落盘。此前失效状态未被捕获，根因未证实，不能将恢复归因于某项尚无证据的计时或判定修复。

已读冲刺累计、HUD、出手入口、角色移动更新、动作互斥、装备异步加载和服务端释放分支。当前 HUD 直接读取 `DashReadyFraction()`，与冲刺持锤切换和左键释放共用进度；没有另设 UI 计时。

## 隔离复现

`WarhammerSprintAudit` 使用独立 GUID 临时档案、无界面临时世界与正式战锤资源。不会改写用户的正式／PIE 存档。只读过最近 PIE 档案的前置字段，其当时已切换为法杖，不能作为战锤故障现场。

最终运行 `formal-assets-diagnosis.log` 退出码 0，得到：

- 正式战锤网格、握姿配置、动作全部加载，`presentation=1`。
- 装备结束后持续冲刺：`seconds=1.0 / ready=1.0`。
- 完整角色 Tick 和工具 Tick 后：`ready=1.0`。
- 旋风结束后：`ready=1.0`。
- 松开 Shift：`ready=0.0`。

前面的 `loaded-assets-current.log` 虽然计时通过，但 `presentation=0`：无引擎主循环的 commandlet 尚未分发延迟加载回调，不能用来证明正式资源链路。最终 fixture 在自身进程中临时关闭一帧回调延迟，加载完恢复；这是诊断工具修正，不是生产逻辑修复。

## 现场记录

控制台 `fps.Tool.SprintTrace 1` 开启，仅本地战锤且按住 Shift 时每 0.4 秒记录一行；`fps.Tool.SprintTrace 0` 关闭。默认关闭，未改配置文件。

记录 `[WarhammerSprint]` 的资格、已累计秒数、实际进度、冲刺／地面／速度、装备／挥击／蓄力／收势／旋风／上挑占用、输入可用性、施法阻塞、体力冲刺资格、瞄准／开火意图、移动锁及前向输入。

用户在正式编译后回复“重新进入后进度恢复正常”。这是用户实机确认的蓄势进度恢复，不延伸为伤害、联机或整套动作验收。本轮收尾关闭临时状态日志，保留默认关闭的诊断入口供明确需要时使用。

## 构建与范围

正式 `FPSGAMEEditor Win64 Development` 构建成功，最新回执及日志在 `SourceAssets/SteelWarhammer20261014/SprintReadinessFixV1/`。加入隔离 commandlet、所需 friend 声明及默认关闭的定点日志。

必要构建曾被 `Monsters/M09NetworkClockTests.cpp` 调用受保护的 `SetRemoteRoleForBackwardsCompat` 阻塞。只将该调用替换为公开的 `SetReplicates(true)`；已读取引擎实现确认它将 RemoteRole 设置为 `ROLE_SimulatedProxy`，保留随后 `SwapRoles()` 的测试意图。没有执行该怪物测试或修改怪物玩法。

未自动启动图形编辑器或游戏；只读取过既有游戏会话，后续诊断均在后台执行。
