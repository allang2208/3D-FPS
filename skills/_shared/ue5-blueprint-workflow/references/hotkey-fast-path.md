# Hotkey Fast Path

## Mandatory Sequence
1. `blueprint_modify(operation=add_input_key_event, key_name=..., reuse_existing=true)`
2. Query or inspect pins only if needed.
3. Connect exec and data pins.
4. Compile and save the edited graph when required for the implementation; report the actual result. Reason: graph compilation produces the usable Blueprint asset; additional validation runs require a user request.

## Key Names
- Use UE key names like `One`, `SpaceBar`, `A`, `LeftMouseButton`. 原因：输入事件解析依赖引擎的键名标识，显示文字或平台别名未必可用。
- Digits like `"1"` are acceptable if tooling normalizes them.

## Anti-Pattern
- Use the node-creation capability exposed by the current bridge instead of guessing unavailable tool or class names. Reason: bridge schemas differ, and historical tool priority is not a current interface contract.
