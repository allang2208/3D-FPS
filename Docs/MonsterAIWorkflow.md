# 怪物 AI：Behavior Tree 标准

2026-09-11：护士僵尸与手脑共用 UE Behavior Tree 决策、AI Perception 感知和 NavMesh 寻路。角色保留攻击与受控动作的执行时钟；不再在角色 Tick 中同时选择目标、直线追击或切回 Idle。未接入 StateTree。

## 责任划分

- `AMonsterAIController`：目标记忆、感知、返回出生点、Blackboard 更新及路径请求。
- `BT_Monster`：优先处理执行锁定，再返回、攻击、追击/调查最后位置、待机。条件使用观察中止，受击能停止移动和取消当前攻击。
- `UMonsterCombatComponent`：统一攻击入口、受击累积、控制期限、恢复及专用受击动画。角色自身继续维护接触时间、命中去重、嚎叫伤害窗口和布娃娃。
- 动画只表现执行状态；受击结束进入 Recovery，由行为树根据目标、距离和冷却重新选择行为。

原生入口位于 `Source/FPSGAME/Monsters/MonsterAIController.*`、`MonsterBTNodes.*` 和 `MonsterCombatComponent.*`。新增怪物应扩展此执行适配层及其配置，复用控制器和任务；不要在新角色 Tick 中另建追击决策。当前适配层明确支持护士和手脑，尚不是任意角色无需代码即可接入的通用插件。

## 资源与参数

正式资源位于 `/Game/Monsters/AI/`：`BT_Monster`、`BP_MonsterAIController`、`A_Nurse_Hit`、`A_HandBrain_Hit`。两个现有怪物蓝图以及村庄、测试关卡实例均保存控制器与受击片段引用。

| 参数 | 护士 | 手脑 |
|---|---:|---:|
| 累积伤害触发眩晕 | 60 | 150 |
| 普通硬直 | 0.55 秒，每次命中 | 低于阈值不打断攻击 |
| 眩晕 | 1.2 秒 | 0.9 秒 |
| 未受击后清空累积 | 2 秒 | 2 秒 |
| 导航半径/高度 | 34/184 cm | 62/204 cm |

弱命中不会缩短已有眩晕。受击片段基于各自已接受的 Idle 首姿制作，0.6 秒；长控制保持后仰姿态再恢复。骨骼旋转轴从模型空间转换到对应骨骼空间。

视听感知通过 AI Perception；实际开枪报告枪声，普通/消音最大传播距离分别为 1800/500 cm。伤害通过 ReceiveHit 同步记录攻击者，目标记忆为 12 秒。当前包含追击最后已知位置，尚未实现多点搜索、巡逻路线、掩体、EQS 或飞行寻路。

村庄和 `/Game/Tests/MonsterAI/L_MonsterAI` 均有实体导航范围，运行时动态生成两种体型的 Recast 网格。路径失败会记录日志，不退回穿墙直线移动。视觉感知事件只报告变化；目标清空后需从感知缓存重新获取仍可见的玩家。

## 重建与验收

- 首次安装：`Tools/MonsterAI/install_ai.py`（UE Python）。会保存现有村庄备份、建立资源与专用测试地图，不作为日常回归命令。
- 导航修复：`rebuild_navigation.py`；只返回成功不足以证明范围有效，必须读回非零 Brush bounds，并在游戏中获得有效路径。
- 受击动作重建：`refine_hit_axes.py`。
- 独立绕墙与受击：`Tools/MonsterAI/Run-MonsterAI.ps1 -Audit`，结果 `Saved/MonsterAI/acceptance.json` 和 `play.log`。
- 护士村庄回归：`Tools/MonsterAI/Run-NurseRegression.ps1`，结果 `Saved/MonsterAI/nurse-regression.log`。
- 手脑村庄回归：`Tools/HandBrain/Open-HandBrainVillage.ps1 -Audit`，结果 `Saved/HandBrain/acceptance.json` 与 `play.log`。

三项均使用隔离角色档案。护士测试按实际防御计算预期扣血，复活检查满当前生命上限；不使用旧的固定 100 血假设。各怪物回归隔离其他怪物，保留命中、躲避、打断与尸体等断言。

构建成功与运行验收分别记录；打包、联机复制和大量怪物性能不属于本次验证范围。原工程的 GameFeatureData / Python 工具加载错误需与本次断言分开记录。

## 本次验收记录

2026-09-11，Editor Development 模块 `9112110` 构建成功；随后独立 `-game` 运行：

- 15:49：AI 16/16，通过真实枪击、受击片段、停止移动、累积眩晕、弱命中保持眩晕、恢复追击/攻击和绕墙。实际侧向绕行 456.9 cm。
- 15:51：护士村庄 15/15，近战接触与去重、躲避、打断、枪击、尸体回收和玩家满血复活。
- 15:52：手脑村庄 30/30，包含拍击、六跳嚎叫、恐惧释放、墙体遮挡、死亡取消伤害、布娃娃接地及再次刷新。报告副本在 `Saved/MonsterAI/handbrain-regression/`。

已查看最新版 `Saved/MonsterAI/gun-recoil-peak.png` 受击实拍和 `Saved/HandBrain/village-ragdoll.png` 村庄尸体实拍。以上是自动驱动真实游戏进程的验收，未代替用户手动试玩。正在运行的旧编辑器需要重新启动才能加载新原生模块。
