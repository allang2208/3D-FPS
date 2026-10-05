# 螺柱 M-14 — V06 软组织摊地死亡

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04。用户反馈 V02 死亡僵硬，要求软体组织全部摊到地上。V02 的整体基底旋转与站立形状复合碰撞已不适合作为该死亡效果的制作方向。

## 制作设计

- 采用原表面的连续变形目标，三个阶段依次下沉、折叠、铺开。底部先失去支撑，上部组织和囊体延迟落下；根裙向外放松，膜面随连接处落下，口器转向上方并保留厚度。
- 同一空间变形作用于所有原表面及重复接缝点，避免不同部件被独立骨骼拉开形成尖刺。保持骨骼单位缩放，不让体节缩放逐层相乘。
- 口器和束带附近使用连续保护区域保留局部厚度；囊体保留低矮组织体积。原网格面、UV、权重和生前动作保留，不减面、不重绑。
- 完整死亡时长 3.6 秒，关键阶段为 0.75、1.60、2.70 秒；2.70 秒达到摊开姿态，3.24 秒接入共享尸体物理。只对 M14 延后交接，防止原 60% 交接提前中断软组织变形。
- 尸体碰撞按同一个终态表面制作 27 个低矮凸包，共用一个整体承重体，维持连续外皮。软组织形变由动画目标驱动，接地与静止由共享尸体组件承担；不是实时软体求解器。
- 终态变形权重保留在网格组件上，尸体快照和动画实例切换后仍保持摊开状态。生前继续使用原查询碰撞；原咬击、喷吐、横扫、移速和尸体寿命沿用。
- UE 交付网格从原 `SK_M14` 复制，在 MeshDescription 中写入与 Blender 母版相同的连续变形场，保留原分区、材质槽和绑定；法线由 UE 按各阶段表面生成。完整 FBX 仍保留为交换源，实际交付绕过其长时间未完成的高面数场景读取。

## 制作源

- [Blender 母版](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV06/Authoring/M14_Rigged_SoftDeath_v06.blend)
- [软体死亡制作脚本](../../Tools/SpiralPillarM14/author_soft_death_v06.py)
- [UE 导入与保存脚本](../../Tools/SpiralPillarM14/import_soft_death_v06.py)
- [变形与碰撞导出记录](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV06/Records/authoring.json)

## 状态

新版 `SK_M14_SoftDeath_v06`、三个变形目标、`A_M14_Death_v06`、`PA_M14_SoftCorpse_v06` 及原怪物蓝图已实际制作并保存；四组原 M14 材质已启用变形目标用途。继续从 F6「螺柱 M-14」生成。

Editor/Game 常规后台构建完成。保留原始约 194 万三角面与绑定，新增加三个全表面变形目标；未制作减面或 LOD，也未测量新增资源开销。

没有打开 UE 图形编辑器、游戏或 PIE，没有运行渲染、截图或测试。接地观感、地形适应和形变由用户在游戏中体验；源码与资源保存不代表视觉验收通过。

落盘回执：[UE 资源](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV06/Records/ue_revision.json)、[Editor 构建](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV06/Records/build_FPSGAMEEditor.json)、[Game 构建](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV06/Records/build_FPSGAME.json)。
