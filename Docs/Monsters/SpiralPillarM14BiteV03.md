# 螺柱 M-14 — V03 口器前伸

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04。按用户要求，将攻击时下方口器的向前伸出幅度增加 50%。

## 已保存改动

复制原咬击动作，仅将 maw 骨骼的向外平移分量乘以 1.5。制作曲线的向外峰值从 30.11 cm 增至 45.16 cm；这描述的是口器相对原骨骼位置的前伸量，并非从怪物中心计算的总攻击距离。

向内蓄力、口器高度、左右偏移、牙圈开合、主体配合及收势时序保留。动作仍为 1.9 秒，伤害接触时刻仍为 0.86 秒。现有代码在接触时刻采样动画，再从 mouth_socket 取得位置，因此命中位置随前伸动作自然前移；没有额外放大 MouthReach 或 AI 起手距离。

已有的 56 cm/s 移速、两倍移动播放节奏及 V02 死亡动作和尸体物理保留。没有改动网格、蒙皮、材质或 C++，本次无需原生构建。

## 文件与接入

- [可编辑 V03 Blender](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV03/Authoring/M14_Rigged_Animated_v03.blend)
- [新版咬击 FBX](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV03/Exports/A_M14_Bite_v03.fbx)
- [动作制作记录](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV03/Records/authoring.json)
- [UE 保存记录](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV03/Records/ue_revision.json)
- [制作脚本](../../Tools/SpiralPillarM14/extend_bite_v03.py) / [导入脚本](../../Tools/SpiralPillarM14/import_bite_v03.py)

UE 动作为 `/Game/Monsters/SpiralPillarM14/Animations/A_M14_Bite_v03`，现有 `BP_SpiralPillarM14` 已引用该动作并保存，F6 入口仍为“螺柱 M-14”。旧动作保留。

通过已有编辑器的 MCP 互斥桥导入与保存。首次保存被当前试玩模式阻止，结束该次 PIE 后完成保存；未重新启动试玩。未执行测试、截图或验收渲染，实际伸出效果与接触由用户体验。
