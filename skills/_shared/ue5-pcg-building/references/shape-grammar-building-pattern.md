# Shape Grammar Building Pattern

## Use Cases
- Rule-driven facade variation with deterministic output.
- District style switching without rebuilding full graphs.
- Fast iteration on floor and facade composition rules.

## Rule Design Checklist
- Define atomic modules first: base, mid, corner, top, roof. 原因：原子模块明确连接与边界，语法才能组合出结构完整的建筑序列。
- Keep grammar symbols readable and style-scoped. 原因：可读且按风格区分的符号可避免不同建筑语法互相混用。
- Isolate random choices behind explicit seeded selectors.
- Add hard constraints for min/max height and facade continuity. 原因：高度与立面连续性属于结构合法条件，纯随机序列无法保证可拼接建筑。

## Integration Pattern
- Generate candidate points/transforms in PCG graph.
- Apply shape grammar stage for module sequence decisions. 原因：序列决策属于语法层，分离后可以保持模块几何与排列规则各自清晰。
- Emit final symbol-resolved meshes to output spawner.
- Record style/seed metadata tags for debug and replay. 原因：风格与种子是重放生成方案的必要输入，只保存最终外观无法复现选择过程。

## Common Pitfalls
- Mixing unit scales across module sets.
- Unstable rule order causing non-deterministic variation.
- Overly deep grammar chains causing heavy runtime cost.
