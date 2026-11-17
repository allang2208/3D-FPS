# 本对话工作与联机核查（2026-11-17）

按用户要求核对源码、资产保存回执及构建记录，修复明确遗漏。未打开 UE，未启动游戏、PIE、无界面玩法测试或联机进程。本报告的代码核查不等同于实机验收。

## 完成情况

| 工作 | 当前证据与状态 |
| --- | --- |
| 陨石包覆火焰、尾迹、冲击波、火星、残火 | MeteorAssets.h 仍引用已接入的各阶段资产；本轮检查文件存在，未改美术资产或玩法数值。 |
| 火球命中基底替换陨石爆燃、拉长翻滚 | SourceAssets/MeteorFireballImpact20261115/LongerRoll/assets-saved.json 为 revision 2，记录 NS_MeteorPressureV7 已保存、Niagara 编译完成，火团生命周期为供体的 2.05 倍。旧摘要中“仅分析、尚未替换”已不符合当前文件和保存回执。 |
| 暴风雪 B 版乌云、寒气、冰锥碎裂 | ZoneAssetPaths[0] 为 ChargedV3，近手云保持 RollingV1，寒气与碎裂路径仍在同一清单。ColdShatter、CloudMistRepair 保存回执存在，B 版恢复 Game / Editor 构建成功；当前资产文件存在。 |
| 高地长弓阴影 | UpdateBowVisibility 仍只遍历各槽直接渲染子组件，阴影受零件与渲染件可见性共同约束，隐藏的备用弦圆柱不会重新投影。HighlandBowShadow20261117 双目标构建成功。 |
| 夜间传送门、神像与袭击 | 当前权威生成、复制表现、地形固定加载、完整路线校验与失败换址逻辑均在。之前构建记录已落盘；本轮没有改生成算法和波次。 |
| 丘陵普通、大型与表面怪物导航 | HillsRaidPursuit20261117、HillsLargeSurfaceNavigation20261117 双目标构建均成功；本轮补齐多人替换目标的导航体型校验。 |
| 丘陵不生成悬钟 | F6 列表与 SpawnInFront 使用同一 IsAvailableInWorld 禁止策略；丘陵野生动物和夜袭池原本不含悬钟，地牢入口保留。上一轮中断的构建已于本轮补齐，当前 Game / Editor 产物均包含该限制。 |

陨石、暴风雪及传送门当前直接引用的 33 个 /Game 资产文件均存在，见 Saved/ConversationNetworkAudit20261117/asset-files.json。这是文件存在性与历史保存记录核对，本轮没有启动引擎重新加载或渲染资产，也没有进行 Cook / 打包。

## 本轮修复

1. 陨石远端 NetInit 原先必须先获得 NetCaster；客户端 Tick 也会因施法者未同步或失去相关性而自行结束技能。现在客户端按复制的技能快照、落点和服务器时间初始化，施法者死亡/消失导致的权威结束只由服务器决定。补等 GameState，已过期副本不再请求并启动旧特效。
2. 暴风雪远端同样解除 NetCaster 的初始化门槛。服务端 InitializeZone 仍要求真实施法者；客户端使用已复制的区域和房间数据，施法者后续可用时补回引用。伤害、结束与奖励仍走原权威分支。
3. 陨石残火的地形采样原本也通过施法者取得 World。TraceSurface 的上下文扩大为 Actor，未同步施法者时以陨石副本自身采样，保留原地面、遮挡、角色过滤和残火数值。
4. 陨石资源异步加载完成时，岩体已按服务器时间移到途中，但尾迹初始位置仍是高空起点。现改为岩体当前世界位置，避免资源迟到时产生不连续的初始长段。
5. 丘陵实际 NavigateTo 已拒绝过小体型导航，但多人 FindReplacement 的候选路线探测遗漏了同一限制。现统一体型条件，避免大怪物选择一名看似有路径、实际移动又拒绝的替代玩家。视野、攻击距离、记忆和换目标冷却不变。

本轮共修改 6 个源码文件，修改前副本和 SHA256 清单位于 Saved/ConversationNetworkAudit20261117/Before 与 changed-files.json。既有悬钟限制文件另纳入构建，不改动其已保存逻辑。

## 联机代码核查边界

- 施法：客机通过 ColdSteelPlayerState 的施法请求进入服务端快照/消耗/落点复核；区域 Actor 由权威端生成。Meteor DamageArea、Blizzard DamageTick 和奖励结算保留权威限制，未增加客户端伤害。
- 表现：两种区域技能按服务器开始时间恢复；较晚进入区域不会重新播过期的陨石撞击。晚到的资源恢复残火，不补播旧瞬间爆炸。暴风雪仍采用选定 B 版路径。
- 传送门：HillsNightRaidSubsystem 客户端 Tick 立即返回；Portal 为 AlwaysRelevant，位置以及 OpenedAt/ClosedAt 复制，各端使用服务器时钟计算渐入/渐出。
- 神像：身份、耐久和夜间状态复制；伤害入口只接受权威端且带夜袭标签的合法攻击者。接触点来自实际石台外表面，服务端 AI 和近战共用。
- 玩家范围：玩家避让和替代目标遍历服务器的全部 PlayerController；丘陵地形 ViewCenters 包含远端玩家，碰撞等待也按每个权威玩家处理，不仅跟随主机。
- 追击：共享移动由服务器 AI 决策，神像没有玩家目标时仍可发布路线。护士客机 Tick 只播放动作，不执行 TryMelee；鼓囊攻击时钟、伏窥者表面法线/附着/跳跃时钟、悬钟状态均有复制路径。
- 特殊怪物：沿用上一轮逐类清单与相应原生移动入口；本轮复查的是本对话改动关联的权威与复制分支，未逐个运行 16 类怪物的联机对局。
- F6 刷怪当前是主机权限；客机没有开放刷怪按钮，这是现有权限边界。

以上路径没有再发现本轮可明确确认的重复生成、重复伤害或只追主机的问题；不据此宣称完整联机通过。高延迟、丢包、中途加入、施法者离开相关范围、断线与重新加入等实际表现尚未在本轮运行验证。

## 构建与交付

上一轮 Saved/HillsNoHangingBell20261117/delivery.json 已记录 Game failed、Editor pending；日志止于编译中途，没有成功链接回执。本轮不终止其他进程、不覆盖运行中模块。

2026-11-17 17:17 已完成本轮构建交付，Saved/ConversationNetworkAudit20261117/delivery.json 中 Game / Editor 均为 succeeded。

- Game：共享 Game 构建成功链接后，本轮 run-build.ps1 再次执行 FPSGAME Win64 Development 成功；本轮日志为 FPSGAME.log。
- Editor：复用刚完成的同项目共享 Editor 构建，日志 Result: Succeeded，成功链接 UnrealEditor-FPSGAME.dll。日志副本为 FPSGAMEEditor-shared.log，保留其来源字段，不冒充由本轮队列重新链接。
- 本轮 6 个 .cpp（含悬钟限制）在两个目标中的 12 个对象文件均晚于对应源码及 FireMagicArea.h，最终二进制均晚于对应对象文件；本轮修改清单的源码 SHA256 未发生后续变化。详情见 built-source-receipt.json 与 changed-files.json。
- 本轮等待中的重复 Editor 构建队列已结束；未停止其他编译或资产导入进程。无需等待占用 DLL 的其他导入操作结束后再次链接同一批代码。

未修改玩法数值、美术资产、地图或存档结构。源码修复与构建产物均已落盘；未打开 UE 或运行游戏，本轮联机实机效果由用户后续测试。
