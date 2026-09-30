# ArmHinge55 — PKM / 201 左上臂解剖铰链

说明与结果：Docs/Weapons/pkm-201-arm-hinge-20260930.md。

- collect.py（UE）：读取 PKM 60 条、201 100 条现用动作的左臂 8 根骨骼（RAW 源键）及两把枪的绑定姿势，输出 Inputs/、inputs.json。
- uthor.py（离线）：上臂辅助骨对齐解剖肘铰链，前臂旋前按 0、1/3、2/3、1 分配（上限 110°），肘部在肩—腕圆上最多移动约 6 cm，剩余部分留在上臂并同时作用于肘两侧。输出 Tracks/、uthoring.json。
- check.py（离线）：保持姿势中上臂偏离铰链的前后对比、瞬态、肘位移动、片段首尾与待机的一致性，输出 check.json。
- install.py（UE）：只改写 7 根左臂骨的局部轨道。有 PIE、未保存修改，或包在读取后被改过时停止。备份在 Before/，回执为 delivery.json。
- 过程补丁：patch_branch.py、patch_deterministic.py、patch_pin.py、patch_hinge_continuity.py，已并入 uthor.py，只作记录。

保存：commandlet-20260930-174907.log，160/160，写入前后的散列均已变化。未运行游戏或 PIE。

以后重新导出任何 PKM / 201 左臂动作，都要在最新资产上重跑 collect → author → install。
