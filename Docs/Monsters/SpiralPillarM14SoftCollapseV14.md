# 螺柱 M-14：30 米喷吐与连续软体死亡 V14

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

用户要求：攻击距离设为 30 米，重新调整僵硬的死亡动作。按照当前远程攻击迭代，30 米用于喷吐发动距离。

## 玩法调整

- 喷吐最远发动距离：20 → 30 m。
- 弹体最大航程：22 → 33 m，给发射位置和移动提前量留出余量。
- 索敌视距：22 → 33 m；脱战范围：26 → 40 m，避免玩家在新射程内却先触发脱战。
- 保留 CD 3.5 秒、速度 10 m/s、锁定速度快照与发射等待时间的提前量计算、有效伤害命中后叠加一层中毒。
- 毒液拖尾采样间距改为 53 cm，继续限制每颗最多 64 个采样、每帧最多 4 个；完整覆盖新航程。

## 死亡动作调整

旧动作只有三个大幅整体形态，每段单独 smoothstep 会在中间姿态减速停顿。V14 将空间错开的软组织塌落烘焙为九个采样，在相邻采样之间连续插值，不再重复对每段减速。

九个采样时刻：0.18、0.42、0.68、0.94、1.20、1.50、1.85、2.35、3.10 秒。根裙先失去支撑，上下螺旋躯干向不同方向弯折；两侧囊体延后并错时落下，接地后有逐渐消退的回弹和横向摊开。进入死亡的当前姿态过渡延长到 0.42 秒。

铁链和束带沿八个刚性区域拟合运动，材料接缝的重复顶点共享轨迹，继续保留 V13 的组织过渡权重。骨骼保持单位缩放，不重新引入连续组织被多具布娃娃拉开的处理方式。每帧最多启用两个形变目标，不在运行时重算顶点或拟合铁链。

终态沿用 V13 摊平表面和对应 V06 单体复合尸体碰撞。3.10 秒组织停止回弹，3.24 秒交接尸体物理。原 V06 死亡骨骼片段作为 3.6 秒的静止骨架时钟继续使用；实际新动作保存在 V14 网格形变目标及蓝图采样时序中。源 Blender 文件也写入了相同时间曲线。

## 文件

- 源文件：`SourceAssets/SpiralPillarM14Meshy20261004/ProductionV14/Authoring/M14_SoftCollapse_v14.blend`。
- 新网格：`/Game/Monsters/SpiralPillarM14/SK_M14_SoftCollapse_v14`。
- 正式蓝图：`/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14`。
- `Tools/SpiralPillarM14/author_soft_collapse_v14.py` 制作源形变和导入数据。
- `Tools/SpiralPillarM14/import_soft_collapse_v14.py` 保存网格和蓝图参数。
- `SpiralPillarM14DeathAuthoring.cpp` 在原拓扑上导入形变，保留权重、UV、材质及所有原始面。

## 状态

Blender 制作源、新形变网格与正式蓝图均已实际落盘。Editor/Game 原生构建完成。未启动编辑器或游戏，未运行预览、测试或验收渲染；由用户体验最终观感与玩法。

[资产保存回执](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV14/Records/ue_revision.json)，[制作回执](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV14/Records/authoring.json)。
