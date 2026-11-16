# 未知：死亡重生与换图的联机收尾

范围：客户端玩家死亡、两秒后的正式重生、未知对新 Pawn 的目标与伤害归属、持续魔法的死亡／World 退出收尾。沿用服务器权威伤害，不改玩家或怪物数值。

## 修复

- `UnknownSpell::IsTarget` 同时检查施法者和目标仍已 BeginPlay、位于同一 World，以及目标仍是控制器当前持有的 Pawn。流送关卡的 `RouteEndPlay(RemovedFromWorld)` 会先结束 Actor 生命周期，UObject 可能仍然有效；仅检查弱引用和死亡标志不足以拒绝这段窗口的迟到命中。弓与法术共享此入口，枪械和近战接触也接入同一判断。
- `AMonsterAIController::LivingPlayer` 排除已经 EndPlay 或不再由控制器持有的旧角色。未知在目标失效时清空待发挥砍／连发、停止持续引导并清掉旧攻击引用；正常换目标、发现新角色继续由既有感知与战术更新处理。
- 未知死亡立即调用 `FinishZonesForRemoval` 收尾暴风雪。原来未知只有自己的 `Health/Motion`，没有玩家生命组件，而暴风雪的自主死亡检测只读取玩家生命组件，导致云、冰雹等可能延续到十二秒尸体销毁。原有陨石／火甲／龙息、电域、冰甲和疾行收尾保留。
- 未知 EndPlay 清除待命中状态及攻击、战术目标引用；原有组件 EndPlay 负责取消异步资源回调、释放持续法术 Actor 和效果组件。

## 已阅读的相关边界

| 边界 | 实际入口与处理 |
| --- | --- |
| 客机死亡与重生 | `UFPSCombatHealthComponent::OnDamage/Respawn`：死亡拒绝后续伤害；UnPossess、Destroy 旧 Pawn，再 RestartPlayer。 |
| 仇恨与面向 | `MonsterAwareness/MonsterAIController` 的 LivingPlayer、UpdateKnowledge、黑板 Target；未知 UpdateTactics 与 UpdateCombatFocus。 |
| 枪、近战、箭与法术 | `HitWithRound`、`ReleaseAttack`、`HitWithArrow`、`UnknownSpell::Hit`；伤害回执仍由服务器生命组件确认。 |
| 持续状态 | 灼烧属于受击 Pawn 的 `UCombatStatusFormula`，不随 PlayerState 复制到新生命。敌人的正常场景区域不会因为某一个受害者死亡而全局消失。 |
| 持续魔法退场 | FireMagic、ElectricMagic、Blizzard、IceArmor、LightningHaste、IceWall 的组件收尾；暴风雪、陨石和冰刺 Actor 的 EndPlay。 |
| 整队换图 | `SaveTeamTravelParticipant` 先取消／结算玩家技能并保存，再启用 seamless ServerTravel；`CopyProperties` 搬运权威影子档案。 |
| 个人返程 | `UDungeonRoomSubsystem::ReturnPlayer` 是同 World 的传送；与实际 ServerTravel 分开记录，不能互相替代验收。 |

## 复现与验证入口

新增 `Development/UnknownLifeAudit.*`，仅在非 Shipping 且携带 `-UnknownLifeAudit` 时执行。真实 AFPSGAMECharacter、ColdSteelPlayerState、普通档案上传和正式死亡重生计时器；AI 使用真实控制器和黑板，以隔离刺激检查目标切换，不代替玩家输入、导航或动画视觉验收。

`Tools/UnknownLifeAudit/build.ps1` 等待已有编译和 DLL 占用，串行构建 Editor/Game。

`Tools/UnknownLifeAudit/run.ps1` 使用隔离项目宿主、独立档案和 UserDir，监听服务器与客户端两个 NullRHI 进程；UDP 20827，双方请求 60 ms 延迟、2% 丢包。通过项目既有批次互斥运行，不打开交互编辑器，只清理本次记录的进程。

实际覆盖：四类未知失去死亡目标／拒绝迟到命中；正式重生后旧 Pawn 失效、旧灼烧不转移、新生命每次命中只结算一次；流送 EndPlay 到 GC 之间的施法者拒绝伤害；未知死亡后的暴风雪及附身效果清理；带着持续魔法执行真实 seamless ServerTravel，新 World 再取得目标并攻击一次。测试使用 `/Engine/Maps/Entry` 到同一最小地图的新 World，走实际网络旅行协议；不是主神空间／地牢资源内容或个人返程玩法验收。

## 2026-11-16 结果

- `Saved/Logs/UnknownLifeTravel20261116-r3-FPSGAMEEditor.console.log`：Editor 编译、链接成功，31.15 秒。
- `Saved/Logs/UnknownLifeTravel20261116-r3-FPSGAME.console.log`：Game 编译、链接成功，210.64 秒。
- `Saved/UnknownLifeTravel20261116/Wire-20261116-life-r1/summary.json`：通过。服务器 15 条记录（含 8 条远端确认），客户端 8 条观察，全部通过；不是 23 个互不重复的场景。
- 一次真实 UDP 连接，一次正式死亡重生，一次保持客户端进程的 seamless World 切换。双方最终实测网络模拟配置均为延迟 60 ms、丢包 2%。
- 客机死亡 0 HP；重生后四种命中结束为 745 HP，客户端一致；切换 World 后保持 745 HP，重新取得新角色并完成四种命中后为 699 HP，客户端一致。测试场景固定刺激，不表示正常 AI 的伤害平衡数据。
- 活动暴风雪在客户端观察到 1 个，未知死亡后变为 0；重新施法后为 1，World 切换后为 0。火甲、电域等收尾状态同步；图像未渲染。
- 两端日志没有 `Fatal error`、`Assertion failed`、`Unhandled Exception`。保留既有 Experimental Python Toolsets 启动报错，未将它作为本次玩法失败或擅自修改插件。
- 运行 DLL 与项目最终 DLL 的 SHA256 一致：`484BD64D1E1D7CA4923755AC2AF930F725899A0D3569BC120732C0A0623CC445`。测试 PID 1876／27640 均已退出。

构建中另修复两处现存的技能树 C++ 编译阻塞：`ColdSteelSkillTreeScreen.cpp` 将 `TObjectPtr` 数组遍历改为引用；`ColdSteelSkillTreeDetail.cpp` 将遮蔽成员的局部 `Selected` 改名 `SelectedSlot`。不改变界面行为。修改前快照位于 `Saved/SourceSnapshots/UnknownLifeTravel20261116`。

等待构建期间遇到目录扫描占用与低优先级编译长期不推进；仅结束过本次 r1 的已核实进程，r2 对本次编译器临时使用普通优先级，辅助轮询已退出。未结束其他任务或交互编辑器。

未覆盖跨机器、打包版本、个人返程实际操作及有画面的动作／特效观感。上述相关源码已检查，不能把无界面网络状态结果当作视觉验收。
