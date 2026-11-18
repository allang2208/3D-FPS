---
name: ue5-performance-packaging
description: UE5.6-UE5.8 performance budgeting, regression diagnosis, and packaging readiness. Use for FPSGAME hot-path, HUD, asset or streaming performance constraints, frame-time analysis, PIE performance work, and packaging readiness.
---

# 共用规则入口

共用流程读取仓库发布快照：[ue5-performance-packaging](../_shared/ue5-performance-packaging/SKILL.md)，不要叠加旧镜像流程。 为什么：共用流程只维护一个来源，避免工程镜像与个人版本给出相互冲突的步骤。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。 为什么：当前用户授权决定操作范围，历史测试与协调记录不能自动成为新任务授权。

本入口随仓库提供共用规则快照；日常修订仍回到个人维护源，发布时更新快照。 为什么：相对链接支持换机阅读，单一维护源避免两套规则分叉。

## 怪群 GPU 与区域提前准备

PIE、原工程与独立包性能对照，或资源不全/无怪但帧率更高时，先读 [正式战斗负载与性能基线](references/runtime-baseline-equivalence.md)。构建成功和局部资源覆盖不证明场景等价。 为什么：重复读取、同步加载和无预算工作会直接进入游戏帧，复用现有调度可控制成本。

同量蒙皮计算突然变慢、玩家装备随怪群变慢或 F6 驻留采集，读 [共享输出缓冲归因](references/shared-skinning-buffer-diagnosis.md)。提前分摊区域刷怪初始化、控制准备池内存和主客机生命周期，读 [区域提前准备](references/area-spawn-preparation.md)。 为什么：「共享输出缓冲归因」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 骨骼装备多个 LOD 仍保持全精度时，读取[连续长靴与渲染 LOD](../asset-model-workflow/references/continuous-boots-and-render-lods.md)：检查独立策略、最终渲染数据和重导入口，不能从减面比例推算帧率。 为什么：不同几何与变形需求需要不同制作路线，统一套用面数或生成参数会损失有效细节。

城市街区的实例、碰撞代理、连续道路及距离剔除优化，读取 [几何成本与城市实例口径](references/scene-geometry-cost-and-lod.md) 和 [城市分区制作](../ue5-pcg-building/references/city-district-production.md)。 为什么：「几何成本与城市实例口径」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

调整温带丘陵的快速／完整入场、延迟加入或后台植被批次时，读取[进入场景前的资源准备](references/entry-resource-preparation.md)。 为什么：「进入场景前的资源准备」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。
