# Natural Language Triggers

## Example User Prompts
- How do I add a keyboard hotkey in Blueprint?
- Why is my inventory data empty after loading save data?
- How do I write a reusable UE5 C++ component?
- Tooltip goes off-screen in UMG. How should I fix it?
- How do I generate deterministic modular buildings with PCG and Shape Grammar?
- What should I check before packaging?

## Expected Routing

示例用于识别实际任务；出现关键词不自动执行制作、检查或测试。原因：路由只选择相关资料，具体操作范围仍由用户请求决定。

| 请求主题 | 领域入口 | 原因 |
| --- | --- | --- |
| Blueprint behavior | `ue5-blueprint-workflow` | 节点、引脚和事件图由蓝图流程处理，避免把图编辑问题误归为 C++ 实现。 |
| C++ / class design | `ue5-cpp-gameplay` | 类生命周期、反射与组件实现需要对应 C++ 合同。 |
| UI / UMG / Slate | `ue5-ui-umg-slate` | 界面布局、输入和控件生命周期属于 UI 流程。 |
| save/load / replication | `ue5-save-load-replication` | 持久化与网络权威需要共同处理数据身份和恢复顺序。 |
| world interaction / pickup | `ue5-world-interaction` | 交互资格、目标和拾取事务需要沿用实际世界入口。 |
| PCG / procedural building / Shape Grammar | `ue5-pcg-building` | 程序化生成需要场景结构、种子与模块接口约束。 |
| performance / packaging | `ue5-performance-packaging` | 性能与打包问题需要对应预算、构建目标和用户要求的诊断范围。 |
| debugging / validation | `ue5-debug-validation` | 用户明确请求诊断时，需要把现象、日志与证据对应起来。 |
| module boundary / architecture | `ue5-architecture` | 模块依赖与职责划分属于架构边界问题。 |

- 用户给出引擎模块名且需要定位时，按需读取 [模块映射参考](../../ue5-module-router/ROUTING.md)；已有明确领域时直接进入该领域。原因：映射表辅助定位，不应成为每个任务的强制前置步骤，也不再作为独立技能触发。
