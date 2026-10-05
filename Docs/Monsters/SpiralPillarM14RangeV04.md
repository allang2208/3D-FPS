# 螺柱 M-14 — V04 咬击范围与起手距离

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04。按用户要求，将攻击判定和发动攻击距离与 V03 口器前伸同步调整。

| 配置 | 之前 | 当前 | 基准 |
| --- | --- | --- | --- |
| MouthReach | 70 cm | 105 cm | 实时口器位置到目标胶囊表面的水平距离 |
| BiteTriggerRange | 185 cm | 235 cm | 怪物与目标的中心水平距离 |
| 追击停距 | 170 cm | 220 cm | 现有规则 BiteTriggerRange - 15 |

命中范围增加 50%，新增 35 cm；V03 口器自身的前伸又增加约 15 cm，因此从角色中心计算的起手距离合计增加 50 cm。起手距离使用 235 cm，以保留原有的起手与命中余量关系。命中仍以 0.86 秒实际采样得到的 mouth_socket 为起点，保留原来的面向角、高度限制、遮挡和单次结算。

现有共享 AI 直接读取这些蓝图参数，停距自动同步到 220 cm，近距离转向启动范围自动为 270 cm；冰墙拦截与攻击也读取同一个 BiteTriggerRange，使用 235 cm。没有增加平行的距离常量，也没有修改其他怪物。

已更新并保存 `/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14`。游戏通过现有 F6 蓝图入口采用这组设置；原生类的未配置模板默认值未改。V03 动作、攻击时长和冷却、当前移速及 V02 死亡效果继续使用。

- [UE 保存记录](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV04/Records/ue_revision.json)
- [配置保存脚本](../../Tools/SpiralPillarM14/adjust_bite_range_v04.py)
- [V03 口器动作](SpiralPillarM14BiteV03.md)

本次是既有蓝图参数调整，无需 C++ 构建。未运行游戏、截图或追加验收，由用户自行测试。
