# 缚群 V13：修正 V12 胶囊碰撞尺寸单位

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户反馈 V12 衣物被拉成大片与尖刺。本次针对这一回归修正，保留 V12 的肉体、衣物几何、UV、蒙皮、末端分叉骨架、攻击时序和死亡资产。

## 定位

已保存 V12 资产中的骨骼参考缩放为 100。`BuildGarmentSimulation` 新建胶囊时，中心已经通过 `InverseTransformPosition` 转为骨骼局部坐标，但半径、柱体长度仍使用肉体顶点的网格厘米值，漏除了骨骼缩放。

Chaos 在 `ChaosClothingSimulationCollider.cpp` 中把根骨缩放乘入碰撞几何的尺寸，因此胶囊线性尺寸错误放大 100 倍。例如左侧袖料的上臂胶囊，错误存储半径 14.504326、柱长 69.655823，而正确的骨骼局部尺寸约为 0.145043、0.696558。该错误属于本次 authoring 实现，不是用户的模型或材质造成。

实际资产只读数据保存在 `SourceAssets/BoundCongregateMeshy20261006/GarmentRepairV13/garment-data-before.txt`。四块衣物骨骼索引无不匹配，渲染分区引用的布料 GUID 均正确，映射索引有效，静止位置重建误差最大约 0.02 厘米。因此本次不重新拆分衣物、不再次删面或更换骨架。

## 修正

- `BoundCongregateAuthoring.cpp` 将胶囊半径和柱长一起除以参考骨骼缩放，与中心坐标保持相同单位。后续重建同样使用修正后的逻辑。
- `save_garment_scale_v13.py` 只重建并保存当前活体网格的四块布料资产，继续关闭 CCD，保留原背挡、活动距离与材质。几何和配套软体死亡数据不变。
- 原网格包备份在 `GarmentRepairV13/before/`。完整落盘以 `GarmentRepairV13/delivery.json` 的 `saved=true` 为准。

本次只读取目标资产数据用于定位，未启动游戏、布料运行探针、PIE 或视觉验收。游戏表现交由用户确认。
