# 人形原地眩晕摇晃

工程制作记录：`Docs/Monsters/humanoid-stun-20260926.md`。四种适配循环已导入保存，首版 Editor 构建成功；后续硬直/眩晕分离修订以 `Docs/Monsters/stagger-stun-separation-20260926.md` 为准。效果尚待用户测试，未做自动预览或性能采样。

- 本地 Mesh2Motion `human-addon-animations.glb` 中存在 CC0 `Dizzy`，源时长 2.375 秒。可作为四种现有人形的共用源，仍需骨架、体型、循环和脚部接地适配，不称为已经适配合格的模板。
- `UMonsterCombatComponent` 使用现有控制时钟衔接受击、原地摇晃和恢复；脚本在 `Tools/HumanoidStun`，源与收据在 `SourceAssets/HumanoidStun20260926`，目标资产在 `/Game/Monsters/HumanoidStun`。
- `DizzyClip` / `DizzyPlayRate` 是各怪物的可配置属性；只有明确的技能/弹反眩晕进入摇晃，破韧硬直永远不凭时长升级为眩晕。短眩晕不强塞完整摇晃周期，追加眩晕保留原循环进度。招架保留原前段，结束混合到动态 Idle。
- 破韧硬直复用受击片段的快速冲击、持续卸力和恢复，跳过已知静态保持段；用 `MonsterReactionTiming::StaggerSample` 调度，不反复重播受击。硬直结束恢复动态 Idle。眩晕单独保存世界时间到期点，叠加硬直只延长整体封锁，不延长眩晕。
- 冻结、石化、击飞与死亡有独立表现优先级。不能把所有 `InterruptAttack` 都视为喝醉摇晃，也不能让普通枪械和 DOT 绕过原免硬直闸门。
- 纯动画眩晕不使用布娃娃，不额外占刚体预算；复用原战斗组件更新。快照切换只发生在进入、恢复和打断边界，不在每帧重复构建动画实例。
- 生产状态以导入收据、正式模块构建和用户实际反馈分别记录。PIE 中原生动画重定向可能被引擎拒绝，先结束已获授权的试玩，再在现有编辑器按桥批次互斥导入；不为此关闭或重新启动编辑器。
