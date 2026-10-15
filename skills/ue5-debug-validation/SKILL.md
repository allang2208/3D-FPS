---
name: ue5-debug-validation
description: UE5.6-UE5.8 debugging and validation workflow for logs, asset checks, and regression triage. Use when requests involve troubleshooting why gameplay does not work, validating expected output, narrowing minimal repro, and producing concrete fix steps.
---

# 本机维护源入口

本机共用流程统一读取[ue5-debug-validation](C:/Users/allan/.codex/skills/ue5-debug-validation/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

- 预览世界释放、EndPIE 或 DynamicWind 渲染线程异常：读取 [预览场景生命周期](references/preview-scene-lifecycle.md)。

用户要求多进程主客机或渲染检查时，读 [运行负载与构建证据](references/multi-process-runtime-evidence.md)：独立 DLL 宿主仍共享硬件负载，源/对象校验、成功链接和运行结果分别记录。用户叫停后，整理与发布不恢复测试授权。

地图文件存在但联机载入失败，或无界面地牢卡在渲染预热时，读 [地图预加载与无界面诊断](references/map-preload-and-headless-dungeon.md)。
