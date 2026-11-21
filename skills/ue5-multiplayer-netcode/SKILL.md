---
name: ue5-multiplayer-netcode
description: FPSGAME 联机源码入口、服务器权威、档案传输、动作复制与生命周期约束；按当前实现维护，不以历史测试笔记代替运行合同。
---

# 联机开发规则

**第一条（FPSGAME）　文件位置与引用路径。** 从当前工程的[制作目录与功能索引](../../Docs/Production/README.md)和[存储规则第 4.1 节](../../WORKFLOW.md#41-存储分配与文件操作边界)查找对应功能。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

1. 遵守工程 `AGENTS.md` 与 `WORKFLOW.md` 的后台开发、用户授权测试和禁止跨对话协调规则。为什么：联机历史取证命令不是每次开发都要执行的操作。
2. 联机入口使用 `Plugins/ColdSteelNet/Source/ColdSteelNet/Public/FPSNetGameMode.h` 的 `AFPSNetGameMode`，继承 `AFPSGAMEGameMode`；World 层接入见 `Source/FPSGAME/Multiplayer/ColdSteelNetWorldSubsystem.*`。为什么：当前插件没有旧笔记所写的 `AOnlineGameMode`、`AMultiplayerStart` 或占位玩家类。
3. `UColdSteelNetConnectSubsystem` 是 `-MPConnect`/`-MPConnectDelay` 的延迟连接辅助，按 `Initialize`/`TryConnect` 实现使用；不把它当常驻 GPU 预热服务。为什么：当前代码通过 GameInstance 定时器发一次 `open`，没有旧文的 `OnMapLoad` 预热协议。
4. 冲刺、ADS、滑铲、架枪意图沿用 `FSavedMove_FPSCharacter` 的 `FLAG_Custom_0..3`；打包、恢复及 `CanCombineWith` 同步维护。为什么：移动预测需要按同一份意图重放，拆成无关 RPC 会破坏时序。
5. 闪避位移沿用 `FPSDodgeMovement.cpp` 与 `FPSDodgeRootMotionSource.*`，保留 `PrepareRootMotion` 的区间积分。为什么：当前实现按时间段累计位移，不能凭旧笔记补入不存在的派生类重载或改成逐帧常量位移。
6. 玩家本地档案由 `UColdSteelStatusModel` 维护，服务器远端玩家使用 `AColdSteelPlayerState` 的影子档；数值按 `ColdSteelAuthority::ForPawn` 或 `GetNetShadowProfile` 的实际归属读取。为什么：直接使用本机 GameInstance 会把主机装备数值套给客机或目标。
7. 档案传输沿用 `ServerSubmitProfileChunk` / `ClientReceiveProfileChunk` 与 `ColdSteelProfileTransfer.*`；保留 `MirrorBlob` 的拥有者传输语义及当前块大小、序号、长度限制。为什么：当前实现是有界字节块传输，不存在旧 `UColdSteelSkillModel` 的 4 KB shard 协议。
8. 客机档案先经 `SanitizeGuestProfile` 消毒再合并；目录数值、服务器账本与投影剥离见 [服务端回执与准入](references/server-authority-receipts.md)。为什么：实例快照及客户端上传不能覆盖服务器已经确认的资源与权威数值。
9. 命中走 `ServerReportHit`、服务器校验和 `ClientConfirmHit`；伤害、弹药、攻击语义、骨骼与 LOS 由服务器重建。为什么：本地表现命中和客户端声明不能替代权威结算。
10. 重击、弓拉弦、冲刺、连段、格挡及副手攻击分别使用已有授权轮次与回执，按 [服务端回执与准入](references/server-authority-receipts.md) 和 [副手近战](references/offhand-melee-retiming-and-item-snapshots.md) 维护。为什么：重复包、错实例和跨 Actor 乱序不能产生重复扣费、无蓄力伤害或无限弹反。
11. 施法入口按 `ServerCastSpell` / `ClientCastResult` / `ExecuteCastRequest` 的当前声明接入，并阅读 [持续魔法的联机状态与收尾](../ue5-skill-magic-workflow/references/persistent-magic-network.md)。为什么：旧 `ClientRequestCast → ServerCastBegin → ServerCastRelease` 不是当前 RPC 接口，资源支付与离场收尾必须跟随现有状态机。
12. 本机表现按 `IsLocallyControlled()`，结算按 Authority，专服跳过纯音画；符文剑保留当前客户端初始化与权威请求链。为什么：旧“符文剑在 NM_Client 整体不 Tick、只有主机可用”已不符合 `RuneSwordComponent::BeginPlay`。
13. 身体上行沿用 `ServerBodyTransition` / `ServerBodySnapshot` 和 `AcceptBodyPresentation` 消毒，下行由 `SampleRemoteAuthorityState` 汇合；复制服务器起点与阶段时长。为什么：远端表现要能恢复晚加入状态，不能让客户端表现字段改写玩法事实。
14. 旧 `ServerReportBodyAction` / `ServerRecordAction` 仅列为待清理兼容入口；未完成反射与资产引用确认前保留。为什么：当前定向源码搜索未见发起调用，但文本零调用不足以证明 UE RPC 可以删除。
15. 玩家死亡、相机归还与重生沿用 `FPSCombatHealthComponent` 和 `FPSPlayerBodyReactionCamera`；死亡不重新灌入陈旧档案快照。为什么：相机管理器跨 Pawn 存活，旧实例收尾不能黑屏新实例或撤销已确认死亡。
16. 门族上行使用玩家拥有的 `UFPSDoorPushComponent`，门状态沿用 `FColdSteelDoorNetState`；保留权限、LOS、序号、动作占用和同门重试边界。为什么：客机不拥有门 Actor，直接对门发 Server RPC 无法替代已有权威交互入口。
17. 怪物离散表现沿用当前 State、序号和服务器时钟，循环音频由各端复制态驱动；奖励由权威档案结算。为什么：重放和晚加入需要可恢复状态，客户端音画不能触发重复奖励。
18. 私有钥匙等拥有者数据保留其复制条件；装备、身体与接触事件读取 [全身表现](../ue5-cpp-gameplay/references/player-world-body.md) 和 [复制终态事件](../ue5-save-load-replication/references/replicated-terminal-events.md)。为什么：拥有者可见的数据不能被其他玩家当作公共事实，短事件也不能只依赖一个易被覆盖的瞬时字段。
19. `ColdSteelNet` 的描述符和源码已在 `.gitignore` 设例外；发布仍精确列路径，不默认 `git add -f` 整个插件。为什么：当前忽略规则允许源码发布，而二进制、资源及构建产物仍应按许可和用途单独处理。
20. 构建、档案保存、源码审阅与主客机运行结果分别交付；历史命令只在用户要求相应检查时使用。为什么：已链接或旧取证成功不能证明当前版本的完整联机行为。

当前源码入口：`Source/FPSGAME/Multiplayer/`、`Movement/FPSCharacterMovementComponent.*`、`Movement/FPSDodgeRootMotionSource.*`、`Characters/FPSPlayerBodyNetwork.cpp`、`Plugins/ColdSteelNet/Source/`。 为什么：把查阅范围限定在连接、移动和权威实现，避免从历史类名推断现有架构。
