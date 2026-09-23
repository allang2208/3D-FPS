# 手脑怪：移速 +25% 与吼叫口部弱点（2026-09-23）

按用户口径调整村庄首领手脑怪（`AHandBrainMonster`）：移动提速且动画同步；弱点只在
释放吼叫攻击时的口部，其余时间无固定要害，但随机暴击照常。

## 移动速度 +25%，动画自动同步

- 新增 `MoveSpeedMultiplier`（默认 **1.25**）：`BeginPlay` 写
  `MaxWalkSpeed = WalkSpeed × Multiplier`（100→125）。`WalkSpeed=100` 保留为**作者基准**，
  因为 `BP_HandBrain` 未覆盖任何属性，CDO 即生效；恐惧组件按当时的
  `MaxWalkSpeed` 存/取快照，与倍率兼容。
- 移动动画零改动即同步：Chase/Returning 的 Tick 本来就把 `MoveClip` 播放率归一为
  `实际速度/WalkSpeed`——全速追逐 125/100 = **1.25×**，步伐自动加快（上限 1.5 未触顶）。
- 优化点：脚步声计时从固定 0.5 s 改为按同一比值缩放（`StepClock+=Dt*Ratio`），
  高速时约 0.4 s/步，节奏跟上动画；Slam/Howl/Dying 都用 `SetPosition` 绝对驱动，
  不受播放率影响。

## 弱点：仅 Howl 期间、仅口部

- 全局要害判定 `ColdSteelSkills::IsCriticalHit` 原本纯按骨名（`head`/`cranium`），
  现先查受害者：`Cast<AHandBrainMonster>(Hit.GetActor())` 命中则改走
  `Brain->IsWeakpointHit(Hit)`——**只有 `State==Howl`（3 秒吟唱）且命中骨骼匹配
  `WeakpointBones` 才算要害**；Idle/Chase/Slam/Recovery/Dying 全部无要害。
  与 `CombatFormulaRuntime` 对狼怪抗暴的 `Cast<AWolfMonster>` 特判同一路数。
- `WeakpointBones`（UPROPERTY，可调）默认 `jaw/mouth/oral/teeth`（大小写不敏感包含）。
  骨骼名已从 `SK_HandBrain_Skeleton` 实测：口部可动骨是 **`jaw`**（含
  `mouth_jaw_*` 合成链），`Oral_mucosa/Aged_teeth` 只是材质槽；`cranium` 仍在骨架上，
  平时爆头不再触发必暴。
- **随机暴击不受影响**：要害只决定"命中即暴"；随机暴击走
  `Snapshot` 的 `Shot.CriticalChance`（角色暴击率+词条）减怪物抗暴后 roll，
  近战与枪械对无要害状态的手脑照样可随机暴击（其 `CritRes` 默认 0）。
  用户要求的"近战可按随机概率暴击"由此天然成立。
- 该改动同时收敛了旧问题：手脑 `cranium` 之前是全局唯一要害，爆头必暴+步枪精通要害
  倍率都算它一份；现在只有吼叫张口窗口是靶心，鼓励在它施法时集火口部。

## 状态

- **未编译**：`Build-Editor.ps1` 检测到编辑器在运行而拒绝构建（按规则不强关进程）；改动为
  `HandBrainMonster.h/.cpp` 与 `ColdSteelSkillRules.cpp` 三个文件，构建窗口到了即可过。
- `HandBrainAudit` 的 `lord_stats/five_clips/chase_displaces` 等断言与新数值兼容
  （追逐位移阈值 50 cm 只会更容易达成）；按规则未主动跑审计，交用户实测：
  ① 追击手感提速约四分之一且步伐不滑；② 吼叫 3 秒内打 jaw 骨必暴、平时爆头不暴；
  ③ 近战随机暴击仍出现。
