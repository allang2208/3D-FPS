---
name: ue5-debug-validation
description: UE5.6-UE5.8 debugging and validation workflow for logs, asset checks, and regression triage. Use when requests involve troubleshooting why gameplay does not work, validating expected output, narrowing minimal repro, and producing concrete fix steps.
---

# 共用规则入口

共用流程读取仓库发布快照：[ue5-debug-validation](../_shared/ue5-debug-validation/SKILL.md)，不要叠加旧镜像流程。 为什么：共用流程只维护一个来源，避免工程镜像与个人版本给出相互冲突的步骤。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。 为什么：当前用户授权决定操作范围，历史测试与协调记录不能自动成为新任务授权。

本入口随仓库提供共用规则快照；日常修订仍回到个人维护源，发布时更新快照。 为什么：相对链接支持换机阅读，单一维护源避免两套规则分叉。

- 预览世界释放、EndPIE 或 DynamicWind 渲染线程异常：读取 [预览场景生命周期](references/preview-scene-lifecycle.md)。 为什么：「预览场景生命周期」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

用户要求多进程主客机或渲染检查时，读 [运行负载与构建证据](references/multi-process-runtime-evidence.md)：独立 DLL 宿主仍共享硬件负载，源/对象校验、成功链接和运行结果分别记录。用户叫停后，整理与发布不恢复测试授权。 为什么：「运行负载与构建证据」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

地图文件存在但联机载入失败，或无界面地牢卡在渲染预热时，读 [地图预加载与无界面诊断](references/map-preload-and-headless-dungeon.md)。 为什么：「地图预加载与无界面诊断」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 隔离权威命中夹具、真实 RPC 分派与覆盖边界：读取 [authority-hit-fixture](references/authority-hit-fixture.md)。 为什么：「authority-hit-fixture」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 无界面 `-game` 加载动画触发编辑器事务崩溃：读取[骨架曲线迁移](references/uncooked-animation-curve-migration.md)，按真实调用链处理骨架元数据，不能只重存动画或删重定向引用。 为什么：「骨架曲线迁移」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

温带丘陵出现入场长时间等待、地面模糊或联机出生时缺碰撞时，读取[动态地形材质与出生区流送](references/dynamic-terrain-material-loading.md)。 为什么：「动态地形材质与出生区流送」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 丘陵生产地图联机检查

共享拾取、同档重连、真实队伍换图、NullRHI 准备与室内视图证据，读取 [丘陵联机生命周期检查](references/hills-network-lifecycle.md)。仅在用户明确要求相应检查时运行。 为什么：「丘陵联机生命周期检查」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 静止时植被整模型闪灭

树与草已生成却原地周期性消失时，读 [PCG 属性通知导致的重建](references/pcg-property-change-flicker.md)，先区分组件销毁与漏绘。 为什么：「PCG 属性通知导致的重建」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

地图系统的多进程联机证据、无渲染边界与临时宿主归档，读取 [地图联机证据与归档](references/map-marker-network-evidence.md)。

丘陵截图宿主、材质包装引脚与落盘回执，读取 [丘陵截图宿主、材质包装引脚与落盘回执](references/hills-capture-and-material-receipts.md)。

用户要求村庄主客机联测时，读取 [村庄对话与防御联机边界](../ue5-save-load-replication/references/village-dialogue-and-defenses.md)，区分真实拒绝、随机施工占位与测试环境问题。
