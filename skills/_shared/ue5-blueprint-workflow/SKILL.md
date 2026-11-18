---
name: ue5-blueprint-workflow
description: UE5.6-UE5.8 Blueprint graph workflow for feature implementation, input events, node wiring, and graph validation. Use when requests involve adding Blueprint logic, keyboard input behavior, function chains, event graph edits, or pin-level connection guidance.
---

# 蓝图编辑工作流

- 只在用户要求蓝图实现、修改或排障时使用本流程；后台制作和必要编译遵守[开发规则](../ue5-auto-assistant/references/editor-open-development.md)，不自动运行检查、PIE 或验收。原因：图编辑授权不包含运行游戏或额外测试。
- 先确定目标资产、图和已有输入方式，再用“事件 → 条件/调用 → 状态与输出”说明本次改动。原因：目标图与输入上下文决定节点应该接在哪条执行链上。
- 沿用项目已有的按键或 Enhanced Input 入口；需要新输入系统时使用项目实际支持的 `UInputAction`、`UInputMappingContext`。原因：重复入口或两套绑定同时生效会让同一次输入触发多次。
- 工具名称、操作和参数以当前已读 schema 为准；工具确实支持专用输入节点及复用参数时使用它们。原因：历史 `blueprint_modify`、`add_input_key_event` 等名称不保证在当前桥中存在，硬编码会阻断合法的编辑路径。
- 复用已有变量、函数和入口，只添加本次行为需要的节点；不规定逻辑节点的最少数量。原因：直接调用一个已有函数也能完成需求，凑节点只会增加图的复杂度。
- 按实际节点签名连接执行引脚和数据引脚；重载、类型转换和潜伏节点按该节点语义处理。原因：相同显示名称的节点可能具有不同引脚和异步时序。
- 需要成功与失败两条路径时分别连接，并保留原有状态写入与副作用的先后次序。原因：统一改成“先写状态再调用”可能改变现有失败回滚或异步行为。
- 保存实际修改的蓝图；必要的蓝图编译属于资产制作，用户未要求时不追加引脚巡检、输入去重检查或运行验证。原因：保存与编译用于产物落盘，运行效果仍需单独证据。
- 交付说明修改资产及最终执行链，并注明未测试；若遇到无关编译错误或资产锁，只报告具体阻塞并继续独立工作。原因：用户需要知道已保存的范围及尚未完成的接入，不能把无关问题扩成整项目改造。

## 按故障读取的 API 线索

以下是定位入口，具体签名以工程使用的引擎和插件为准；不承诺未来 UE 小版本的工具能力。原因：接口存在性和工具暴露范围由实际安装版本决定。

| 场景 | 入口 | 保留原因 |
| --- | --- | --- |
| 普通键盘与函数事件 | `UK2Node_InputKey`、`UK2Node_CallFunction`、`UK2Node_CustomEvent` | 帮助区分输入节点、函数调用与自定义事件的职责。 |
| Enhanced Input | `UK2Node_InputActionEvent`、`UEnhancedInputLocalPlayerSubsystem`、`UEnhancedInputComponent` | 输入资产、上下文注册和组件绑定是不同的触发环节。 |
| 引脚连线失败 | 当前节点类型、真实引脚名称、类型与重载 | 对应关系明确后才能修复连接，不需要猜测节点类。 |
| 用户要求排查输入不触发或重复触发 | 当前输入上下文、焦点、入口及绑定路径 | 这些路径直接决定事件是否分派及分派次数。 |
