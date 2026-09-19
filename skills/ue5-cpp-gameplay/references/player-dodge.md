# FPSGAME 玩家方向闪避（2026-09-13）

- 左 Shift 与 Sprint 共用现有输入，短按不超过 0.2 秒后松开闪避，按住仍奔跑；动作中的新点按不排队。默认时长 0.3 秒、距离 300 cm，在玩家默认值 `FPS Movement | Dodge` 调节。
- 使用原生 CharacterMovement 的 Root Motion Source Override，锁定触发时的水平输入方向；无输入用镜头水平朝向，归一化斜向。解析积分 `p(t)=2t-t²`，以区间差得到每帧位移；保留重力和原 40 cm 台阶，不用无 Sweep 的位置赋值。
- 无敌状态属于移动组件，在 Actor TakeDamage 事件前拦截伤害，健康组件提供 IsInvulnerable 给中毒／恐惧的施加入口复用；不删除已有状态。完成、取消、传送、销毁均清理本次 Root Motion Source。
- 这是单机接入，没有复制第三方完整移动组件或实现网络输入预测。GitHub 经验和具体文件见工程 `Docs/player-dodge-20260913.md`。
- 按用户规则，未主动运行测试或验收；开发所需构建与运行测试分开报告。

## 体力与技能接入

- 后续体力由 `UColdSteelStatusModel` 拥有；`Content/ColdSteelData/stamina.json` 调节初值，`FPSStaminaModel.cpp` 处理按秒消耗、延迟恢复与旧档迁移。实时体力更新仅广播 `OnStaminaChanged`，不逐帧保存或重新装备武器。
- 300 cm 是基础距离；实际距离叠加闪避等级 × 10 cm，消耗为基础体力 × (1 − 等级 × 0.015)，初始 Lv.1、满级 20。成功开始动作才扣体力/获得使用经验，等级变化不改变已启动动作的距离。
- `EnemyAttackDamage.h` 区分敌方近战/远程直击；无敌拦截位置判定成功闪避，并排除持续毒伤、环境来源。每次动作每类奖励一次；技能经验走原有保存事务。新增技能升级通知须依据该通知的 Icon 加载图标，不能复用固定的步枪图标。
- 具体配置、UI、存档与未测试说明见 `Docs/UI/stamina-dodge-plan-20260913.md`。
