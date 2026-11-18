# 类玩家怪物的伤害与角色生命周期

用于未知等复用玩家装备／技能的敌人，以及客机受击、死亡重生、晚加入、重连或换 World 后的异常。源码位置按 FPSGAME 工程根解析；用户未要求检查时不自动运行夹具。 原因：该参考用于已发生异常的定向排错，读取和维护文档不应自动启动额外夹具。

## 权威与真正接受的伤害

- 防御、暴击抵抗、免伤和受击后的资源变化从实际受击 Pawn 的 `ColdSteelAuthority::ForPawn` 取得。监听服务器的 GameInstance 只属于房主，远端影子档案尚未绑定时不得回落到房主；加入窗口可拒绝受击，不能借默认档案结算。 原因：客户端表现与服务器结算可能重复经过入口，权威路径必须保持一次有效事务。
- `Super::TakeDamage` 的原始返回值不一定等于生命组件实际接受的伤害。月影等免伤可能在 OnTakeAnyDamage 内拒绝；过量伤害也只接受剩余生命。用本次调用的局部回执与 RAII 保护嵌套指针，避免免伤后仍附加寒冷／控制，也避免共享“最后伤害值”被重入覆盖。
- 最后一击后及时 `SyncRuntime` 到同一 Pawn 的权威档案。断线可能早于 PlayerState 下一次采样；只靠周期采样会在重连时恢复成旧血量。这里不增加逐击磁盘存档。
- 客户端 Actor 的初始复制可能早于 BeginPlay；BeginPlay 中把 Health 无条件重设为 MaxHealth 会覆盖晚加入时已收到的受伤／死亡状态。初始生命重置限权威端。

## 每条生命与 World 的身份

- 死亡、UnPossess、销毁、RemovedFromWorld 和重生是不同阶段。弱引用仍有效不表示 Actor 仍在玩法中；流送 EndPlay 到 GC 之间，UObject 可以继续存在。
- 敌人迟到命中校验施法者和受击者仍已 BeginPlay、同一 World、目标仍是控制器当前持有的 Pawn，并检查双方各自的死亡表示。保留 `IsCaster` 的类型分类语义，不通过把退场 NPC 分类为玩家来阻止伤害。
- 仇恨、黑板 Target、战斗面向和待发攻击共同放弃旧 Pawn。失效目标对应的连发、近战待接触、拉弓和引导需要取消；重生目标重新经正常感知取得，不能把旧攻击回执转给控制器的新 Pawn。 原因：弓的准备、持续和释放阶段有不同费用与动作身份，合并阶段会改变取消和消耗行为。
- 附着于旧 Pawn 的灼烧不应复制到新生命。另一方面，一个受害者死亡不意味着应清除整个世界中仍合法存在的敌方区域法术。

## 持续魔法与晚到表现

- 复用玩家组件时核对死亡适配：未知使用自己的 Health/Motion，并没有玩家生命组件。仅检查 `UFPSCombatHealthComponent` 的区域法术会漏掉未知死亡。未知死亡应显式收尾其暴风雪等持续效果；组件 EndPlay 再做幂等兜底。
- 保留技能既有死亡奖励策略。正常结束、死亡、断线、换图收尾可以共用一次性结算，但不能借清理改写奖励或把缓存奖励模型回落到房主。 原因：动作未正常结束也会离开当前状态，资源占用、费用和待结算结果必须有明确收尾。
- `DOREPLIFETIME` 只能登记带复制标记的 UPROPERTY。若已有 `NetHealth` 和调参快照承担状态，不要额外登记本地 Health/MaxHealth；错误可能直到首位客户端打开 Actor 通道才断言崩溃。 原因：复制登记要求对应反射标记，本地字段额外登记会破坏 Actor 通道建立。
- 阶段快照同时传递服务器时间锚点。客户端按当前服务器时钟算年龄，不能从收到快照时重新计时；晚加入恢复剩余墙体／区域，不重播过期落地、碎裂、短促音效。 原因：本地 Authority 标记和共享世界的服务器身份并不总是等价，需要保留现有网络分工。

## 对应实现与证据边界

入口：`Monsters/UnknownSpellCombat.cpp`、`MonsterAwareness.cpp`、`UnknownHumanoidTactics.cpp`、`FPSCombatHealthComponent.cpp`、`Movement/FPSPlayerDodge.cpp`、`Skills/FPSIceWall.cpp`。

2026-11-16 的 JoinAudit 使用真实 AFPSGAMECharacter、普通档案上传和三个新客户端进程检查重连；LifeAudit 走正式两秒重生和真实 seamless ServerTravel。死亡重生用例直接刺激生产处理器、控制器和黑板，不代表真实输入、复杂地图寻路或动画画面通过。参见工程 `Docs/Monsters/unknown-join-damage-review-20261116.md`、`unknown-life-travel-review-20261116.md` 及对应发布包；历史通过记录不自动变成后续版本验收。
