---
name: ue5-architecture
description: UE5.6-UE5.8 architecture planning and module boundary design for Unreal projects. Use when requests involve module layout, Build.cs dependencies, reflection exposure strategy, Public/Private API boundaries, naming conventions, and preventing circular dependencies.
---

# UE 模块边界

仅在模块划分、Build.cs 依赖或跨模块 API 确有变化时使用；普通类修改直接用 C++ 技能。 原因：模块架构工作涉及依赖边界，普通类修改不需要重走完整模块设计。

- 读取实际依赖与资产引用，再确定 Runtime、Editor、UI 等边界；不要因类归属不明默认塞入 Runtime 后留 TODO。 原因：模块边界决定依赖方向和打包可用性，随意归入 Runtime 会把不适用的依赖带入运行目标。
- Public 依赖由公开头文件实际需要决定，其他依赖留在 Private；保持现有反射和 Blueprint 调用兼容。
- 移动或重命名反射类型时处理资产类路径与重定向，不能只搬源文件；跨模块变更完成必要构建。 原因：源码、磁盘资产、二进制和运行效果属于不同交付阶段，需要各自的完成依据。
- 模块索引生成工具保留在 `scripts/generate_module_index_v2.py`；仅需要更新索引时执行。
- 遵守[后台开发与接入规则](../ue5-auto-assistant/references/editor-open-development.md)。不强制输出图表，不追加测试。 原因：制作步骤与检查步骤需要分别获得对应授权，历史验收流程不能自动扩展当前任务。

- 行为保持的去重、长文件拆分与反射/生成数据保留，读取 [模块边界与清理](references/module-layout.md)。原因：拆分应保持职责、状态和作者链，不能只按行数搬运。
