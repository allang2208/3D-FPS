---
name: ue5-world-interaction
description: UE5.6-UE5.8 world interaction systems for pickups, spawners, overlap/trace checks, and visual feedback. Use when requests involve interactive world actors, spawn logic, pickup behavior, interaction radius checks, success/failure feedback, and actor lifecycle control.
---

# 世界交互

遵守[后台开发与接入规则](../ue5-auto-assistant/references/editor-open-development.md)，不主动测试或跨对话协调。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

- 沿实际 overlap、瞄准 trace 或使用键入口修改；拾取资格、库存提交和 Actor 消耗构成一次成功事务，失败不得丢物品。 原因：物品转移涉及来源与目标两侧状态，部分成功不能造成物品丢失或重复生成。
- 成功后立即更新可交互状态；退出模式、卸载与 EndPlay 都清理预览和委托，保留现有碰撞通道与权威路径。
- 挖掘、采集和近战不共用未经区分的射线距离；高度差保持一次符号约定。具体案例及分屏下的村民交互轮廓、店内亮部选择见[交互问题记录](references/interaction-pitfalls.md)。
- 连续环境声使用持续音频组件、淡入淡出与并发预算；字段及来源记录见同一参考的喷泉章节。

## 项目资料

- 设施搜索柜、掉落概率、共享取物或旧档迁移，读取 [搜索容器合同](references/facility-search-containers.md)。区分首次生成、取空状态、客户端视图与真实共享库存。

- 地牢进房封门、完整编成清除、档案至 Boss 推进锁，读取 [主题路线与房间闸门](../ue5-pcg-building/references/themed-routes-and-room-gates.md)，以实际节点和 alive/pending 状态定位。
- FPSGAME 场景栏杆、楼梯与家具翻越，读取 [场景开发标准：统一翻越制作合同](../ue5-pcg-building/references/scene-development-standard.md)。复用现有判定；专用栏杆需连续碰撞及 `Traversal.GuardrailDrop`，样板和生成模块保持一致。
- For FPSGAME GPU grass interaction (currently paused after failed visual feedback; mf-v14 remains partially integrated), read [grass GPU deform RT window](references/grass-gpu-deform-rt-window.md).
- For harvested trees, original stumps, cut-plane hinges, or Nanite tree crowns, read [tree cutting and falling](references/tree-harvest-cut-and-fall.md).
- For FPSGAME dropped weapon models, gravity, camera-aimed E interactions, or drop hitches, read [physical pickups and preview reuse](references/fpsgame-physical-pickups.md).
- For FPSGAME 20 cm voxel building (grid snapping, ghost preview, instanced gold outline, snap vs free placement), read [voxel placement interaction](references/fpsgame-voxel-placement.md).
- For FPSGAME heightfield terrain destruction (explosion craters, shovel dig/refill, 20 cm grid quantization, sink/rise caps, per-cell rebuild and edit bucketing), read [terrain destruction](references/fpsgame-terrain-destruction.md).

- 涉及矿脉岩块变体：矿种唯一真源、空间加权与重建路径（2026-09-30/10-02/03）时，读取[矿脉岩块变体：矿种唯一真源、空间加权与重建路径（2026-09-30/10-02/03）](references/ore-vein-rock-variants.md)。

- FPSGAME 炼药台的器具命中、金色悬停提示、捕获搅拌、旋钮、温度计和装瓶液体，读取 [炼药台交互](references/alchemy-tabletop-interaction.md)。

- [生活区收集品与排水工具箱](references/staff-living-collectibles.md)：2026-10-18 本轮实现经验与恢复边界，按问题读取；不授权自动测试。

- 椅子、沙发、床铺的占位、范围内上床与 SAN 恢复，读取 [家具坐卧交互](references/furniture-rest.md)。
