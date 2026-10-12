# Super90 裸手局部曲面与表面修正（2026-10-12）

本轮按用户要求保留原有手型和绑定，处理腕部环形分界、肘窝与掌根杂乱折线，并执行制作后的检查。只作用于 Super90；共享 M4/V7 材质、其他武器、骨架、动画和换弹时钟未改。

**交付状态：两套正式网格和独立材质已保存。** `published.json`、`publication_checks.json` 已生成；正式保存内容与检查过的候选逐项一致。未启动 PIE 实机操作。

## 变更

- 腕部、肘窝和掌根采用有界局部平滑：4,436 个顶点改变位置。腕部最大 1.60 mm；肘部左/右最大 1.43/1.48 mm；掌根最大 0.55 mm。
- 对在现有压缩动画中接近翻折的局部面保留原形，并以邻接区域渐变衰减修改。未改变蒙皮权重、参考绑定、拓扑或 UV。
- 裸臂平滑法线跨原有分段和重合 UV 边界连续计算；手指及掌面的法线只在局部修改范围内更新。遵循 UE 原生面绕序，导出 Blender 时匹配其坐标与绕序。
- Super90 独立皮肤材质改用原生 PreSkinnedPosition/Normal，避免把经过 FBX 转换的 M4 打包坐标直接用于腕部过渡。前臂到掌内的颜色、粗糙度和解剖法线渐变共用原生腕部坐标。
- 减少颜色细点，增加轻微的大尺度色温与粗糙度差异。保留已有皮肤贴图来源、指甲与浅掌纹。

## 文件与资产

- 制作、检查和回退记录：`SourceAssets/Super90JointSurface20261012/`。
- 独立材质：`/Game/Weapons/Super90/JointSurface20261012/Materials/`。
- 正式目标：`/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7`。
- 正式裸臂目标：`/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7`。
- 可编辑源：`SourceAssets/BenelliM4Super9020261006/Super90_Gameplay_Editable.blend`，以及同目录 Exports 中上述两套 FBX。
- `author_super90.py` 和 `import_super90.py` 已接入本轮独立制作源与材质。当前 Super90 独立裸臂源以本轮读出的原生 UE 表面为起点，保留原绑定，不再依赖旧 Blend 中有少量位置差异的表面。
- 改动前文件保存在本轮 `Before/`。早先被否定的 MPFB 整臂重塑和 Super90 权重重分配分支继续停用。

## 检查范围与边界

- 读取实际保存的 UE 网格、骨架和压缩动画，检查待机、普通装弹、空仓装弹、完整换弹、检视、装备、开火 7 组动作，共 513 个采样帧。局部修改未造成新增反向三角面。
- UE 候选保存后读回：顶点顺序、三角面、所有 UV、材质分区、权重、骨架及参考骨骼一致；位置误差约 0.000027 mm，法线误差低于 0.00002。
- 4,134 个由末端指节主导的顶点位置保持完全不变。
- 可编辑 Blend 检查通过；裸臂 FBX 再导入检查通过，顶点 18,642、三角面 37,158，权重误差为 0，最大位置误差约 0.00013 mm。
- UE 离屏对比使用实际材质与压缩动画，通过临时 PoseableMesh 采样。它不是用户地图中的 PIE 运行；临时隔离照明用于比较接缝和表面，不代表游戏场景曝光。
- 正式保存以本轮 `published.json` 为准，保存后读回以 `publication_checks.json` 为准。没有这些回执时仍属于候选。

最终 UE 对照图为本轮目录中的 `ue_before_idle.png` / `ue_after_idle.png`、`ue_before_reload.png` / `ue_after_reload.png` 与 `ue_before_elbow.png` / `ue_after_elbow.png`。最终截图批次日志为 `capture-09.log`；正式保存日志为 `publish.log`（0 errors）。

用户可在游戏中重点观察持枪时腕部一圈分界、换弹时肘窝与掌根，以及回握时的接触。本轮维持微调尺度，未整体重塑手臂，也未增加新的姿态驱动或更改动画节奏。
