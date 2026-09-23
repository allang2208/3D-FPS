# 发布记录：脚架部署改版 + 怪物六维/奖励迁移（2026-09-23）

## 发布方式
本条线改动与三个并行会话共用一棵脏工作树（他人未提交的韧性子系统、
近战公式、SVD 配饰等大量混入同一批共享文件）。为不夹带他人未完成工作、
不破坏他人暂存区，采用外科式发布：临时 `GIT_INDEX_FILE` + `commit-tree`，
以 HEAD blob 为基底逐 hunk 叠加本线改动（脚本：`Tools/Monsters/surgical_publish_20260923.py`，
每处锚点断言唯一命中）。真实索引与工作树全程未动。

## 内容
- 脚架：视域窗 ±30°/±12°、窗内转视角不再取消架枪（软降级）、架枪期移动/跳/蹲/冲刺锁定、
  两腿冻结默认下垂（允许穿模）、支撑探测放宽、两段弹链机械音 + 落位衰减抖动。
- 怪物六维：`MonsterCoreStats` 注册表统一供数（伤害/防御/暴击抵抗 + 等级/品阶驱动的
  经验衰减与金币掉落），全局 `HealthMultiplier()=2` 在 BeginPlay 生效。
- 手脑怪：+25% 移速（步频同步）、仅 Howl 期间口部为要害。
- 数据：SVD 狙击重平衡（伤害 85、智力/感知公式、暴击加成 0.5、有效射程 300 m）。
- 文档 / skill 沉淀 / 离线校验器 `Tools/Monsters/check_monster_core_stats.py`（PASS）。

## 有意缓发（依附他人未提交依赖，随后自然带出）
- `Mutant3.cpp` 的 `Level=9; Rank=Elite` 三行（在他会话工作区内；其 69f9e57 提交未含，
  待其下次提交；运行时暂以 NurseZombie 默认 Level=3 计算突变体3奖励，偏保守）。
- `WeaponStatEvaluation.cpp` / 两个 Tooltip 文件的可读性改动（混入他人近战公式与 Gunsmith 依赖）。
- `items.json` 夹带了他会话的冶炼锭条目（纯数据、运行时容忍）。

## 验证
- 工作树整树编译绿：build-20260923-234824.log（含本线全部改动 + 他人代码）。
- 本提交为其保守子集：每个手术文件 = HEAD + 本线 hunk，锚点全部唯一命中。
- `git diff --check` 干净；推送后以 `git ls-remote origin main` 回读 SHA 为准。
