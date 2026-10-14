# 雷暴、暴风雪与专注书本联机补完 · 2026-10-14

范围为上一轮核查列出的联机遗漏。原有龙息联机修复继续保留；本轮不改变技能伤害、范围成长、持续时间、墙板遮挡规则或现用火焰/乌云资产。只进行开发与必要构建，不自动运行主客机、PIE、截图或视觉/性能验收。

## 雷暴领域

- 原先独立的 `bNetDomain` 与 `NetDomainCast` 改为同一个 `FStormDomainState`，包含施法编号、施法快照、服务器开始/结束时间及有效状态。结束会写回 inactive；每次新施法有新编号，重复释放不再依赖一个永远为 true 的布尔值。
- 客机的 Prepare、Release、Cancel 共用 PlayerState 可靠通道并携带相同 CastId。回执按 Pawn 与 CastId 路由，较晚的其他魔法不会吞掉本次雷暴结果；旧取消不能取消新预留。
- 客机先预测云层，但保留本次法力预留直到权威确认。拒绝会清掉对应预测、退还对应预留；不拿走后来雷枪/其他法术的动作付款。权威复制也可确认本次释放，重复回执幂等处理。
- 各端按服务器起始时间计算年龄，晚进入相关范围不会从头播放完整持续时间；已结束状态不会重建旧云。原有 0.6 秒淡出仍然保留。
- 初始化固定长度素材槽。权威雷暴可先推进伤害，云层或音效未加载时延后表现；异步加载完成回调与活动期更新会补建仍有效的云层。雷枪的非专用服入口在素材未就绪时先拒绝，不再越界访问空数组。
- 开始时保留施法者的权威档案。落雷伤害与自然结束修炼均使用该档案，避免客机奖励落入 GameInstance 的房主档案。
- 起手音由预测/复制状态按 CastId 去重；超过 1.25 秒的旧起手不补播。落雷命中音由服务器发送一次 Unreliable Multicast，丢失只影响短声音，不影响伤害；专用服不播放声音。

实现入口：`Skills/FPSStormDomainNetwork.cpp`、`FPSElectricMagicComponent.*`、`ElectricMagicTypes.h`；请求路由为 `Multiplayer/ColdSteelPlayerState.*`。

## 修炼与保存顺序

- 雷暴与暴风雪加入 `PrepareForDisconnect` 和 `SaveTeamTravelParticipant`：先结束活动技能并结算已经确认的命中，再保存/缓存该玩家档案。
- 暴风雪区域在创建时缓存对应权威档案，伤害和完成结算共用它，不在控制器解绑后回退到房主模型。
- 组件/区域 EndPlay 提供收尾补充。结算前置结束标记并清空奖励/模型引用，重复保存和销毁不会重复发放同一批奖励。
- 保留原有施法者死亡时丢弃未完成批次修炼的策略。断线和主动换图与死亡分开；未实际激活的暴风雪区域不发放批次奖励。

实现入口：`Skills/FPSBlizzardComponent.*`、`FPSBlizzardZone.*`、`Multiplayer/ColdSteelCampfireRequests.cpp`、`ColdSteelTeamTravel.cpp`。

## 远端书本金光

- 原本的金色环带/光粒几何抽到 `Weapons/Spellbook/SpellbookGoldGeometry.h`，第一人称与第三人称复用，材质沿用现用 `M_Spellbook_GoldOrbit`。
- 在已有书本骨骼快照里附带淡出强度、效果时钟、翻页活跃度（三个 float，仅书本浮空时发送），不新增逐帧 RPC。
- 远端/第三人称书本创建一次金光组件和动态材质，异步加载素材后消费最新快照。收书、受击收尾和隐藏同步淡出，第一人称/第三人称通过拥有者可见性避免同屏叠加。
- 角色移除时取消本任务的书本/金光加载句柄，并销毁相关表现组件。金光没有碰撞、导航、独立 Tick 或阴影，不参与伤害/扣蓝。

实现入口：`Characters/FPSBodyMotionSample.*`、`FPSPlayerBodyMotion.cpp`、`FPSPlayerBodySpellbook.cpp`、`FPSPlayerBodyComponent.*`、`Weapons/Spellbook/SpellbookComponent.h`、`SpellbookFocusGold.cpp`。

## 交付边界

本轮修改了复制结构、RPC 和自定义身体快照序列化，**主机、客机必须同时使用本轮构建**。不能以旧客机连接新主机来验收。

源码已落盘；无需修改 UE 资产。Game/Editor 构建日志保存在 `Saved/MagicNetworkCompletion20261014`，最终结果以该目录的交付回执为准。代码接入与构建不代表实际主客机、延迟/丢包、重连或画面验收通过。

## 本轮构建结果

2026-10-14 发布前续修：将缓存档案读取落实到雷暴 `Strike`；共用 `Overload` 仅在奖励参数为雷暴批次时读取该缓存，雷枪仍按其自身施法者取权威模型，避免未开雷暴时雷枪过载失效。最终 Editor 构建 `Saved/MagicCloseout20261014/editor-build.log` 成功（54.60 秒），Game 构建 `game-build.log` 成功且目标最新（5.25 秒）。整理、SKILL 和公开依赖边界见 `Docs/Publication/Magic20261014/README.md`；以下为此前构建历史。

最新状态：用户继续构建后，缺失的 M66 头文件已存在，编辑器占用已解除；正式 Editor 构建成功，日志为 `editor-build-final.log`，退出码 0，`Result: Succeeded`，10.89 秒，已完成 `UnrealEditor-FPSGAME.dll` 链接。Game 构建成功记录仍为下述 17:47 快照；本次没有重新运行 Game 构建或主客机测试。

- Game：`game-build-final.log`，2026-10-14 17:47 完成，退出码 0，`Result: Succeeded`，19.03 秒。已链接 `Binaries/Win64/FPSGAME.exe`。这对应当时源码快照，不代表此后并行改动也已经构建。
- 首次 Game 构建遇到 `RootCrownRoots.cpp:13` 的 C4458 局部变量遮蔽错误，仅把局部 `Health` 改名为 `VictimHealth` 解除编译阻塞，没有调整怪物玩法。
- Editor：`editor-build.log`，2026-10-14 17:51 结束，退出码 6，`Result: Failed (OtherCompilationError)`。`MonsterCombatComponent.cpp:3` 和 `MonsterSurfaceGroundingNode.cpp:4` 引用了缺失的 `M66IncineratorMonster.h`；两文件于 17:50 更新，不属于本轮魔法修复。保留现状，不删除引用、不补造怪物类。
- 17:52 读取进程时，发现项目编辑器进程于 17:51:24 启动；本轮没有启动或关闭编辑器。继续正式 Editor 构建需先补齐上述缺失文件，并释放编辑器占用。
- 恢复构建首次尝试为 `editor-build-resume.log`：缺失头文件的错误已消失，但 `RootCrownHitComponent.cpp:20` 使用 `const auto*` 遍历 `TObjectPtr<USkeletalBodySetup>` 数组，导致 C3535/C2440 及后续连带错误。仅将循环变量改成 `const auto&`，保留受击逻辑，随后正式 Editor 构建成功。
- Editor DLL 已落盘；未进行游戏运行、主客机测试、PIE、截图或视觉验收。主客机应同时使用更新后的相同版本。
