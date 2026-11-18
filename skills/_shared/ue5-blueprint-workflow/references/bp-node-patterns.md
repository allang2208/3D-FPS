# Blueprint Node Patterns

## Feature Chain Pattern
- Entry event
- Guard branch (optional)
- Core action node(s)
- Output feedback (`PrintString` or UI update)

## Pin Wiring Pattern
- Connect exec flow first.
- Then connect data pins.
- Set defaults only when data source is absent. 原因：缺省值只用于缺失输入，覆盖已有数据会改变调用者显式选择。

## Validation Pattern
- Inspect node pins for dynamic nodes before final wiring. 原因：动态节点的引脚取决于上下文，最终连线必须使用实际存在的引脚。
- Compile after each logical chunk to isolate faults.
