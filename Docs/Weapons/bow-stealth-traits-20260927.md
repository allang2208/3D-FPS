# 弓：暴击加成与静默击杀

## 已定位的 AI 警觉入口

- `MonsterAIController` 配置视觉、听觉、伤害感知。默认听觉范围 1800 cm，记忆 8 秒；普通索敌记忆 `MemorySeconds=12`。实际视觉索敌还受怪物各自 AggroRange 和视线限制。
- 枪械 `ReportNoiseEvent(Gunshot)` 使用普通 1800 cm／消音 500 cm；弓组件与箭矢原本没有发送听觉事件。拉弓、放弦的玩家反馈音效独立于 AI 听觉。
- `DungeonSpawnDirector::OnMonsterDamaged` 原本不区分致死与否，收到 `OnTakeAnyDamage` 就把本房设为本次地牢运行内持续警报，并将连续通道连接的相邻房间唤醒 12 秒。它只唤醒，不直接给邻房怪物注入玩家坐标。
- 狼族另有 `bHowlOnEncounter=true`、`PackAlertRadius=1100 cm`、`PackAlertTime=1.2 s` 默认值；嚎叫到时间才通知半径内同类，接收方不连锁嚎叫。死亡状态会退出该分支。类或蓝图可覆盖这些默认值。
- Boss／封门遭遇另有 `EncounterTarget` 主动锁定；静默特性不解除已有战斗锁定，也不屏蔽其他怪物直接看见玩家。

## 接入行为

1. `bows.json` 添加 `critDamageBonus=0.5`，与狙击步枪使用同一字段、同一 `ColdSteelSkills::Snapshot` 和 `ApplySkillWeaponHit`。只在随机暴击或要害暴击时生效，与暴击技能奖励相加后一次结算。例如技能加成 +55% 时，弓暴击倍率为 `1 + 0.55 + 0.50 = 2.05`，不是两次相乘。
2. 以独立 `bow_traits_revision=1` 迁移已有实例的这项特性，保留原伤害、强化、质量、改造件和本次之前的表现调整。弓参数面板与“特殊性质”显示同步更新。
3. 箭矢直接命中进入 `MonsterDamageAlert::FScopedSilentShot`。地牢群体警报在该次伤害调用结束后处理：目标实际死亡则丢弃新增警报；存活则在同一调用内按原规则传播，无下一帧延迟、无额外 Tick。
4. 延后判断是必要的：各怪物在扣血后调用 `Super::TakeDamage`，此时伤害委托已经发出，但 `Die`／死亡状态可能尚未设置。只在伤害委托内读取 `IsDead()` 会把致死箭也错误传播出去。
5. 静默作用域绑定这一箭实际命中的目标；不修改已发出的警报、已有仇恨、狼群默认行为或其他武器的伤害通知。未击杀仍由原 ReceiveHit 记住攻击者；先前受伤但被本箭终结，也不从这一箭新增警报，已有警觉保留。
6. 玩家仍听到已制作的拉弓和放箭音效。弓发射／命中继续不提交 AI 听觉噪声；“无声”是怪物感知规则。

## 完成状态

源码、弓目录、面板文案和旧实例迁移已落盘。用户保存并关闭编辑器后，`FPSGAMEEditor Win64 Development` 后台构建成功，18 个构建任务，21.91 秒；模块 DLL 已更新。构建日志：`Saved/BowStealthTraits20260927/build-editor.log`。

下次游玩时旧弓实例会同步暴击特性。未启动编辑器或游戏，未进行测试或验收；游戏行为由用户测试。

变更备份：`Saved/BowStealthTraits20260927/Before/`。
数据安装脚本与回执：`SourceAssets/BowStealthTraits20260927/`。
